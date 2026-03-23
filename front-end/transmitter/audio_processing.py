from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pydub import AudioSegment, effects, silence


class AudioPreprocessError(RuntimeError):
    """Raised when audio preprocessing fails."""


@dataclass
class AudioMetadata:
    original_duration_sec: float
    processed_duration_sec: float
    sample_rate_hz: int
    channels: int
    peak_dbfs: float
    rms_dbfs: float

    def as_dict(self) -> dict:
        return {
            "original_duration_sec": round(self.original_duration_sec, 3),
            "processed_duration_sec": round(self.processed_duration_sec, 3),
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "peak_dbfs": round(self.peak_dbfs, 3),
            "rms_dbfs": round(self.rms_dbfs, 3),
        }


def preprocess_audio(raw_audio: bytes, target_sample_rate_hz: int = 16_000) -> tuple[bytes, AudioMetadata]:
    """
    Normalize and trim an audio sample for STT and semantic transmission.
    """
    if not raw_audio:
        raise AudioPreprocessError("No audio bytes were provided.")

    try:
        segment = AudioSegment.from_file(BytesIO(raw_audio))
    except Exception as exc:  
        raise AudioPreprocessError(f"Unable to read audio payload: {exc}") from exc

    original_duration_sec = len(segment) / 1000.0
    if original_duration_sec <= 0:
        raise AudioPreprocessError("The recording is empty.")

    working = segment.set_channels(1).set_frame_rate(target_sample_rate_hz)

    if working.rms > 0:
        working = effects.normalize(working, headroom=1.0)

    nonsilent_chunks = silence.detect_nonsilent(
        working,
        min_silence_len=220,
        silence_thresh=-42,
        seek_step=1,
    )
    if nonsilent_chunks:
        start_ms = max(0, nonsilent_chunks[0][0] - 80)
        end_ms = min(len(working), nonsilent_chunks[-1][1] + 100)
        working = working[start_ms:end_ms]

    processed_duration_sec = len(working) / 1000.0
    if processed_duration_sec <= 0:
        raise AudioPreprocessError("Silence trimming removed the full sample.")

    peak_dbfs = working.max_dBFS if working.max_dBFS != float("-inf") else -96.0
    rms_dbfs = working.dBFS if working.dBFS != float("-inf") else -96.0

    out = BytesIO()
    working.export(out, format="wav")

    meta = AudioMetadata(
        original_duration_sec=original_duration_sec,
        processed_duration_sec=processed_duration_sec,
        sample_rate_hz=target_sample_rate_hz,
        channels=working.channels,
        peak_dbfs=peak_dbfs,
        rms_dbfs=rms_dbfs,
    )
    return out.getvalue(), meta

