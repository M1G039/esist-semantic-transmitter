from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import time

import requests


class STTError(RuntimeError):
    """Raised when transcription fails."""


@dataclass
class TranscriptionResult:
    text: str
    provider: str
    latency_ms: int
    model: str


def transcribe_with_openai(
    audio_wav: bytes,
    *,
    api_key: str,
    model: str = "whisper-1",
    language_hint: str = "auto",
    timeout_sec: int = 90,
) -> TranscriptionResult:
    if not api_key:
        raise STTError("OpenAI API key is required for automatic transcription.")
    if not audio_wav:
        raise STTError("Audio payload is empty.")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key.strip()}"}
    files = {
        "file": ("speech.wav", BytesIO(audio_wav), "audio/wav"),
    }
    data = {"model": model}
    if language_hint and language_hint != "auto":
        data["language"] = language_hint

    start = time.perf_counter()
    response = requests.post(
        url,
        headers=headers,
        files=files,
        data=data,
        timeout=timeout_sec,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    if response.status_code >= 400:
        error_text = response.text.strip()[:500]
        raise STTError(
            f"OpenAI transcription failed with status {response.status_code}: {error_text}"
        )

    payload = response.json()
    text = str(payload.get("text", "")).strip()
    if not text:
        raise STTError("Transcription response was successful but empty.")

    return TranscriptionResult(
        text=text,
        provider="OpenAI",
        latency_ms=latency_ms,
        model=model,
    )

