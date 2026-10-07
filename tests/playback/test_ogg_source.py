import io
import struct
import time
import urllib.error

import pytest

from playback import ogg_source
from playback.ogg_source import BackgroundDownload, OggOpusSource


def ogg_page(packets: list[bytes], pagenum: int, continued: bool = False) -> bytes:
    """One Ogg page holding `packets` (lacing per RFC 3533; no CRC check,
    which discord.py's parser doesn't verify either)."""
    segments = bytearray()
    for packet in packets:
        size = len(packet)
        segments.extend([255] * (size // 255))
        segments.append(size % 255)
    header = struct.pack(
        "<4sBBQIIIB",
        b"OggS",
        0,
        1 if continued else 0,
        0,
        1,
        pagenum,
        0,
        len(segments),
    )
    return header + bytes(segments) + b"".join(packets)


AUDIO = [bytes([i]) * (10 + i) for i in range(1, 6)]
# a packet longer than 255 bytes exercises multi-segment lacing
LONG = b"x" * 600


def ogg_file() -> bytes:
    return (
        ogg_page([b"OpusHead" + b"\x01" * 11], 0)
        + ogg_page([b"OpusTags" + b"\x00" * 8], 1)
        + ogg_page(AUDIO[:3], 2)
        + ogg_page([LONG] + AUDIO[3:], 3)
    )


class FakeResponse:
    """Serves `data` from `offset`, optionally failing after `fail_after` bytes
    to simulate a dropped connection."""

    def __init__(self, data: bytes, offset: int, fail_after=None, chunk=10):
        self._body = io.BytesIO(data[offset:])
        self._fail_after = fail_after
        self._sent = 0
        self._chunk = chunk
        self.closed = False

    def read(self, size: int) -> bytes:
        if self._fail_after is not None and self._sent >= self._fail_after:
            raise ConnectionResetError("connection dropped")
        data = self._body.read(min(size, self._chunk))
        self._sent += len(data)
        return data

    def close(self) -> None:
        self.closed = True


class FakeOpener:
    def __init__(self, data: bytes, failures: list = ()):  # type: ignore[assignment]
        self.data = data
        self.failures = list(failures)  # fail_after for each successive open
        self.offsets: list[int] = []

    def __call__(self, url: str, offset: int) -> FakeResponse:
        self.offsets.append(offset)
        fail_after = self.failures.pop(0) if self.failures else None
        return FakeResponse(self.data, offset, fail_after)


def drain(source: OggOpusSource) -> list[bytes]:
    packets = []
    while packet := source.read():
        packets.append(packet)
    return packets


@pytest.fixture(autouse=True)
def no_retry_sleep(monkeypatch):
    monkeypatch.setattr(ogg_source.time, "sleep", lambda seconds: None)


def test_yields_audio_packets_and_skips_headers():
    source = OggOpusSource("https://s3/x.opus", opener=FakeOpener(ogg_file()))

    assert drain(source) == AUDIO[:3] + [LONG] + AUDIO[3:]
    assert source.is_opus()
    assert source.read() == b""  # stays finished


def test_resumes_after_dropped_connection_from_last_byte():
    data = ogg_file()
    opener = FakeOpener(data, failures=[40, 100])  # drops twice mid-file

    packets = drain(OggOpusSource("u", opener=opener))

    assert packets == AUDIO[:3] + [LONG] + AUDIO[3:]
    assert opener.offsets == [0, 40, 140]  # each retry resumes where it stopped


def test_gives_up_after_max_retries_and_ends_song():
    data = ogg_file()
    opener = FakeOpener(data, failures=[30] + [0] * ogg_source.MAX_RETRIES)

    source = OggOpusSource("u", opener=opener)
    drain(source)  # must not hang or raise

    assert source._download.error is not None


def test_garbage_data_ends_song_instead_of_raising():
    source = OggOpusSource("u", opener=FakeOpener(b"not an ogg file at all"))

    assert source.read() == b""


def test_background_download_reads_block_until_data_arrives():
    class SlowResponse(FakeResponse):
        def read(self, size):
            time.sleep(0.01)
            return super().read(size)

    download = BackgroundDownload(
        "u", opener=lambda url, offset: SlowResponse(b"abcdefghij" * 10, offset)
    )

    assert download.read(25) == (b"abcdefghij" * 10)[:25]
    assert download.read(1000) == (b"abcdefghij" * 10)[25:]  # short read at EOF
    assert download.read(10) == b""


def test_cleanup_stops_the_download():
    class EndlessResponse:
        def read(self, size):
            time.sleep(0.005)
            return b"\x00" * size

        def close(self):
            pass

    source = OggOpusSource("u", opener=lambda url, offset: EndlessResponse())
    source.cleanup()
    source._download._thread.join(timeout=2)

    assert not source._download._thread.is_alive()


def test_open_url_sends_range_only_when_resuming(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return "response"

    monkeypatch.setattr(ogg_source.urllib.request, "urlopen", fake_urlopen)

    ogg_source.open_url("https://s3/x", 0)
    ogg_source.open_url("https://s3/x", 1234)

    assert requests[0].get_header("Range") is None
    assert requests[1].get_header("Range") == "bytes=1234-"


def http_error(url: str, code: int, reason: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, reason, {}, None)  # type: ignore[arg-type]


def test_http_client_errors_are_not_retried():
    opened = []

    def forbidden(url, offset):
        opened.append(offset)
        raise http_error(url, 403, "Forbidden")

    source = OggOpusSource("u", opener=forbidden)

    assert source.read() == b""
    assert opened == [0]  # gave up at once instead of retrying


def test_server_errors_are_retried():
    data = ogg_file()
    calls = []

    def flaky(url, offset):
        calls.append(offset)
        if len(calls) == 1:
            raise http_error(url, 503, "Slow Down")
        return FakeResponse(data, offset)

    assert drain(OggOpusSource("u", opener=flaky)) == AUDIO[:3] + [LONG] + AUDIO[3:]
    assert calls == [0, 0]
