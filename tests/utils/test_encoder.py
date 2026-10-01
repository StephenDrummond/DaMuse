import os
from unittest.mock import MagicMock, patch

import pytest

from config import AudioSettings
from utils import encoder
from utils.encoder import Encoder, PermanentEncodeError

MAX_DURATION_SECONDS = 600
ENCODER = Encoder("ffmpeg", max_duration_seconds=MAX_DURATION_SECONDS)


def test_ffmpeg_command_copies_opus():
    command = ENCODER.ffmpeg_command("in.webm", "out.opus", copy=True)

    assert command[command.index("-c:a") + 1] == "copy"
    assert "libopus" not in command
    assert command[-3:] == ["-f", "ogg", "out.opus"]


def test_from_settings():
    configured = Encoder.from_settings(
        AudioSettings(max_duration_seconds=42, opus_bitrate="96k"), "/bin/ffmpeg"
    )

    command = configured.ffmpeg_command("a", "b", copy=False)
    assert command[0] == "/bin/ffmpeg"
    assert command[command.index("-b:a") + 1] == "96k"
    with pytest.raises(PermanentEncodeError):
        configured.check_cacheable({"duration": 43})


def test_ffmpeg_command_encodes_other_codecs():
    command = ENCODER.ffmpeg_command("in.m4a", "out.opus", copy=False)

    assert command[command.index("-c:a") + 1] == "libopus"
    assert command[command.index("-ar") + 1] == "48000"
    assert command[command.index("-ac") + 1] == "2"


@pytest.mark.parametrize(
    "info",
    [{"is_live": True}, {"duration": MAX_DURATION_SECONDS + 1}],
)
def test_check_cacheable_rejects(info):
    with pytest.raises(PermanentEncodeError):
        ENCODER.check_cacheable(info)


@pytest.mark.parametrize("info", [{"duration": 200}, {}])
def test_check_cacheable_accepts(info):
    ENCODER.check_cacheable(info)


def fake_ydl(workdir, raw, processed):
    """A YoutubeDL stand-in whose download writes source.webm to workdir."""
    ydl = MagicMock()
    ydl.__enter__.return_value = ydl
    ydl.extract_info.return_value = raw

    def download(result, download):
        open(os.path.join(workdir, "source.webm"), "wb").close()
        return processed

    ydl.process_ie_result.side_effect = download
    return ydl


def test_fetch_and_encode(tmp_path):
    workdir = str(tmp_path)
    processed = {
        "title": "Pink Floyd - Money (Official Video)",
        "acodec": "opus",
        "webpage_url": "page",
        "duration": 382,
    }
    ydl = fake_ydl(workdir, {"duration": 382}, processed)
    with (
        patch.object(encoder.yt_dlp, "YoutubeDL", return_value=ydl),
        patch.object(encoder.subprocess, "run") as run,
    ):
        run.return_value.returncode = 0
        encoded = ENCODER.fetch_and_encode("url", workdir)

    command = run.call_args.args[0]
    assert command[command.index("-i") + 1] == os.path.join(workdir, "source.webm")
    assert command[command.index("-c:a") + 1] == "copy"  # source already Opus
    assert encoded.path == os.path.join(workdir, "audio.opus")
    assert encoded.metadata == {
        "title": "Pink Floyd - Money (Official Video)",
        "hint-title": "Money",
        "hint-artist": "Pink Floyd",
        "source-url": "page",
        "duration": 382,
    }


def test_fetch_and_encode_rejects_before_download(tmp_path):
    ydl = fake_ydl(str(tmp_path), {"duration": MAX_DURATION_SECONDS + 1}, {})
    with patch.object(encoder.yt_dlp, "YoutubeDL", return_value=ydl):
        with pytest.raises(PermanentEncodeError):
            ENCODER.fetch_and_encode("url", str(tmp_path))

    ydl.process_ie_result.assert_not_called()


def test_fetch_and_encode_ffmpeg_failure(tmp_path):
    ydl = fake_ydl(str(tmp_path), {}, {"title": "t", "acodec": "mp4a"})
    with (
        patch.object(encoder.yt_dlp, "YoutubeDL", return_value=ydl),
        patch.object(encoder.subprocess, "run") as run,
    ):
        run.return_value.returncode = 1
        run.return_value.stderr = "bad input"
        with pytest.raises(RuntimeError, match="bad input"):
            ENCODER.fetch_and_encode("url", str(tmp_path))
