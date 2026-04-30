from __future__ import annotations

import streamlit as st
import importlib, os, sys, time, tempfile, wave
from pathlib import Path
from io import BytesIO

class STTError(RuntimeError):
    """Raised when speech-to-text processing fails."""



@st.cache_resource(show_spinner=False)
def get_semanticodec_model():
    # SemantiCodec lives in project scope, so we ensure cwd is importable.
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())

    semanticodec = importlib.import_module("semanticodec")
    return semanticodec.SemantiCodec(token_rate=100, semantic_vocab_size=16384)

def run_semantic_codec(audio_wav: bytes, output_filename: str = "pacote_semantico.pt") -> dict:
    if not audio_wav:
        raise ValueError("Processed audio is empty. Capture audio before semantic encoding.")

    torch_mod = importlib.import_module("torch")
    model = get_semanticodec_model()
    temp_audio_path = ""
    start = time.perf_counter()

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_wav)
            temp_audio_path = temp_audio.name

        with torch_mod.no_grad():
            tokens = model.encode(temp_audio_path)

        output_path = Path(os.getcwd()) / output_filename
        torch_mod.save(tokens, output_path)

        token_count = 0
        if hasattr(tokens, "numel"):
            token_count = int(tokens.numel())
        elif hasattr(tokens, "__len__"):
            token_count = int(len(tokens))

        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "output_path": str(output_path),
            "token_count": token_count,
            "latency_ms": latency_ms,
        }
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Missing module while running SemantiCodec: {exc.name}"
        ) from exc
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


def waveform_to_wav_bytes(waveform, sample_rate: int = 16_000) -> bytes:
    torch_mod = importlib.import_module("torch")
    np_mod = importlib.import_module("numpy")

    # SemantiCodec decode may return either torch.Tensor or numpy.ndarray.
    if isinstance(waveform, np_mod.ndarray):
        waveform = torch_mod.from_numpy(waveform)

    if waveform.ndim == 3:
        waveform = waveform[0]
    if waveform.ndim == 2:
        waveform = waveform[0]
    if waveform.ndim != 1:
        raise ValueError("Decoded waveform has an unsupported shape.")

    if hasattr(waveform, "detach"):
        waveform = waveform.detach()

    pcm = (
        waveform.cpu()
        .clamp(-1.0, 1.0)
        .mul(32767.0)
        .to(torch_mod.int16)
        .numpy()
        .tobytes()
    )

    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return buffer.getvalue()


def decode_semantic_tokens(token_file: str) -> dict:
    if not token_file:
        raise ValueError("No semantic token file available to decode.")

    token_path = Path(token_file)
    if not token_path.exists():
        raise ValueError(f"Semantic token file not found: {token_file}")

    torch_mod = importlib.import_module("torch")
    model = get_semanticodec_model()
    start = time.perf_counter()

    with torch_mod.no_grad():
        tokens = torch_mod.load(token_path, map_location="cpu")
        if hasattr(tokens, "to"):
            tokens = tokens.to(model.device)
        waveform = model.decode(tokens)

    wav_bytes = waveform_to_wav_bytes(waveform, sample_rate=16_000)
    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "wav_bytes": wav_bytes,
        "sample_rate": 16_000,
        "latency_ms": latency_ms,
    }
