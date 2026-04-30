from __future__ import annotations

from dataclasses import dataclass
from ai_sound.audio_processing import AudioMetadata, preprocess_audio
from ai_sound.semantic import normalize_transcript

@dataclass
class InputPreparationResult:
    processed_audio_bytes: bytes
    audio_meta: AudioMetadata | None
    transcript: str

def prepare_audio_input(raw_audio_bytes: bytes, manual_transcript: str) -> InputPreparationResult:
    if raw_audio_bytes:
        processed_audio, audio_meta = preprocess_audio(raw_audio_bytes)
    else:
        processed_audio, audio_meta = b"", None

    transcript = normalize_transcript(manual_transcript)

    return InputPreparationResult(
        processed_audio_bytes=processed_audio,
        audio_meta=audio_meta,
        transcript=transcript,
    )
