"""Play cached Ogg Opus files from S3 without ffmpeg.

The S3 cache holds Ogg Opus, which is already Discord's voice format, so the
packets can go straight to Discord. ffmpeg would only have copied them.
"""

import logging
import threading
import time
import urllib.error
import urllib.request
from typing import IO, Any, Callable, Iterator, Optional, cast

import discord
from discord.oggparse import OggStream

logger = logging.getLogger(__name__)

Opener = Callable[[str, int], Any]  # (url, byte offset) -> readable response

CHUNK_SIZE = 64 * 1024
MAX_RETRIES = 3
OPEN_TIMEOUT_SECONDS = 30
# Ogg Opus header packets (RFC 7845): metadata, not audio
HEADER_PACKETS = (b"OpusHead", b"OpusTags")


def open_url(url: str, offset: int) -> Any:
    """GET `url` from byte `offset` on. Presigned S3 URLs accept a Range
    header: the signature doesn't cover it."""
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=OPEN_TIMEOUT_SECONDS)


class BackgroundDownload:
    """A file-like reader over an HTTP download that runs on its own thread.

    Downloading far outpaces playback, so the audio thread's reads almost never
    wait on the network. A dropped connection resumes from the last byte
    received (up to MAX_RETRIES times). The file is kept in memory; Opus at
    128 kbps is about 1 MB per minute.
    """

    def __init__(self, url: str, opener: Opener = open_url) -> None:
        self._url = url
        self._open = opener
        self._buffer = bytearray()
        self._position = 0  # next byte read() returns
        self._done = False
        self._closed = False
        self._condition = threading.Condition()
        self.error: Optional[BaseException] = None
        self._thread = threading.Thread(target=self._download, daemon=True)
        self._thread.start()

    def _download(self) -> None:
        response = None
        failures = 0
        try:
            while not self._closed:
                try:
                    if response is None:
                        response = self._open(self._url, len(self._buffer))
                    data = response.read(CHUNK_SIZE)
                except Exception as error:
                    failures += 1
                    _close_quietly(response)
                    response = None
                    if failures > MAX_RETRIES or _is_permanent(error):
                        logger.error("Gave up downloading %s: %s", self._url, error)
                        self.error = error
                        return
                    logger.warning("Download interrupted (%s); resuming", error)
                    time.sleep(0.5 * failures)
                    continue
                if not data:
                    return  # end of file
                with self._condition:
                    self._buffer.extend(data)
                    self._condition.notify_all()
        finally:
            _close_quietly(response)
            with self._condition:
                self._done = True
                self._condition.notify_all()

    def read(self, size: int) -> bytes:
        """Up to `size` bytes, blocking until they've arrived; fewer only at
        the end of the file (or if the download failed)."""
        with self._condition:
            self._condition.wait_for(
                lambda: len(self._buffer) - self._position >= size
                or self._done
                or self._closed
            )
            data = bytes(self._buffer[self._position : self._position + size])
            self._position += len(data)
            return data

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()


def _is_permanent(error: Exception) -> bool:
    """HTTP 4xx (a bad or expired URL, missing permission) won't fix itself
    on retry; timeouts and 5xx might."""
    return (
        isinstance(error, urllib.error.HTTPError)
        and 400 <= error.code < 500
        and error.code not in (408, 429)
    )


def _close_quietly(response: Any) -> None:
    if response is not None:
        try:
            response.close()
        except Exception:
            pass


class OggOpusSource(discord.AudioSource):
    """An AudioSource that hands an Ogg Opus file's packets straight to
    Discord: no ffmpeg process, no decoding or encoding."""

    def __init__(self, url: str, opener: Opener = open_url) -> None:
        self._download = BackgroundDownload(url, opener)
        stream = OggStream(cast(IO[bytes], self._download))
        self._packets: Iterator[bytes] = stream.iter_packets()

    def read(self) -> bytes:
        """The next 20 ms Opus packet, or b"" when the song is over."""
        try:
            for packet in self._packets:
                if not packet.startswith(HEADER_PACKETS):
                    return packet
        except Exception:
            logger.exception("Bad Ogg data; ending the song early")
        return b""

    def is_opus(self) -> bool:
        return True

    def cleanup(self) -> None:
        self._download.close()
