from __future__ import annotations

from datetime import datetime
import hashlib
import importlib
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid
import wave

import streamlit as st

from transmitter.audio_processing import AudioMetadata, AudioPreprocessError, preprocess_audio
from transmitter.semantic import encode_semantics, normalize_transcript
from transmitter.transport import DeliveryResult, build_semantic_packet, send_packet
from transmitter.ui_theme import apply_theme, log_item, pipeline_card


st.set_page_config(
    page_title="Semantic Audio Transmitter",
    page_icon="SAT",
    layout="wide",
)


@st.cache_resource(show_spinner=False)
def get_semanticodec_model():
    # SemantiCodec lives in project scope, so we ensure cwd is importable.
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())

    semanticodec = importlib.import_module("semanticodec")
    return semanticodec.SemantiCodec(token_rate=100, semantic_vocab_size=16384)

# TODO: 
def initialize_state() -> None:
    defaults = {
        "session_id": f"tx-{uuid.uuid4().hex[:8]}",
        "speaker_label": "Speaker A",
        "language_hint": "auto",
        "transport_mode": "Mock demo",
        "receiver_endpoint": "http://localhost:8000/semantic-packet",
        "bearer_token": "",
        "network_timeout": 12,
        "manual_transcript": "",
        "raw_audio_bytes": b"",
        "raw_audio_format": "audio/wav",
        "processed_audio_bytes": b"",
        "audio_source": "",
        "audio_meta": None,
        "audio_fingerprint": "",
        "transcript": "",
        "transcript_editor": "",
        "semantic_payload": None,
        "semantic_packet": None,
        "semantic_token_file": "",
        "semantic_token_count": 0,
        "semantic_codec_latency_ms": 0,
        "decoded_audio_bytes": b"",
        "decoded_audio_sample_rate": 16_000,
        "semantic_decode_latency_ms": 0,
        "audio_widget_nonce": 0,
        "delivery_result": None,
        "event_log": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_pipeline_outputs() -> None:
    st.session_state.processed_audio_bytes = b""
    st.session_state.audio_meta = None
    st.session_state.transcript = ""
    st.session_state.transcript_editor = ""
    st.session_state.semantic_payload = None
    st.session_state.semantic_packet = None
    st.session_state.semantic_token_file = ""
    st.session_state.semantic_token_count = 0
    st.session_state.semantic_codec_latency_ms = 0
    st.session_state.decoded_audio_bytes = b""
    st.session_state.decoded_audio_sample_rate = 16_000
    st.session_state.semantic_decode_latency_ms = 0
    st.session_state.delivery_result = None


def add_event(stage: str, message: str, status: str = "info") -> None:
    st.session_state.event_log.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "stage": stage,
            "message": message,
            "status": status,
        }
    )
    st.session_state.event_log = st.session_state.event_log[-30:]


def register_audio(audio_bytes: bytes, source: str, audio_format: str = "audio/wav") -> None:
    if not audio_bytes:
        return
    fingerprint = hashlib.sha256(audio_bytes).hexdigest()
    if fingerprint == st.session_state.audio_fingerprint:
        return
    st.session_state.raw_audio_bytes = audio_bytes
    st.session_state.raw_audio_format = audio_format or "audio/wav"
    st.session_state.audio_fingerprint = fingerprint
    st.session_state.audio_source = source
    clear_pipeline_outputs()
    add_event("Capture", f"New audio sample loaded from {source}.", "success")


def render_sidebar() -> dict:

    return {
        "speaker_label": st.session_state.speaker_label.strip() or "Speaker A",
        "session_id": st.session_state.session_id.strip() or f"tx-{uuid.uuid4().hex[:8]}",
        "language_hint": st.session_state.language_hint,
        "transport_mode": st.session_state.transport_mode,
        "receiver_endpoint": st.session_state.receiver_endpoint.strip(),
        "bearer_token": st.session_state.bearer_token.strip(),
        "network_timeout": int(st.session_state.network_timeout),
    }


def render_hero(config: dict) -> None:
    st.markdown(
        f"""
        <div class="hero-wrap">
            <div class="hero-title">Semantic Audio Communication using Generative AI</div>
            <div class="hero-meta">
                <span class="hero-pill">Transmitter</span>
                <span class="hero-session">Session {config["session_id"]}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def process_and_transcribe(config: dict) -> None:
    transcript = ""

    if st.session_state.raw_audio_bytes:
        processed_audio, audio_meta = preprocess_audio(st.session_state.raw_audio_bytes)
        st.session_state.processed_audio_bytes = processed_audio
        st.session_state.audio_meta = audio_meta
        add_event(
            "Preprocess",
            f"Audio normalized to {audio_meta.sample_rate_hz} Hz mono and trimmed to "
            f"{audio_meta.processed_duration_sec:.2f}s.",
            "success",
        )
    else:
        st.session_state.processed_audio_bytes = b""
        st.session_state.audio_meta = None

    manual = normalize_transcript(st.session_state.manual_transcript)
    transcript = manual
    if transcript:
        add_event("STT", "Manual transcript provided.", "info")
    else:
        add_event("STT", "No manual transcript provided. You can still build tokens and edit transcript later.", "info")

    st.session_state.transcript = transcript
    st.session_state.transcript_editor = transcript
    st.session_state.semantic_payload = None
    st.session_state.semantic_packet = None
    st.session_state.decoded_audio_bytes = b""
    st.session_state.semantic_decode_latency_ms = 0
    st.session_state.delivery_result = None


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
            "Missing dependency while running SemantiCodec. Ensure torch and semanticodec are installed."
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


def build_packet(config: dict, transcript_text: str) -> None:
    cleaned = normalize_transcript(transcript_text)
    if not cleaned:
        raise ValueError("Transcript cannot be empty.")

    semantics = encode_semantics(cleaned)
    packet = build_semantic_packet(
        transcript=cleaned,
        semantics=semantics,
        session_id=config["session_id"],
        speaker_label=config["speaker_label"],
        audio_meta=st.session_state.audio_meta,
        language_hint=config["language_hint"],
    )
    st.session_state.semantic_payload = semantics
    st.session_state.semantic_packet = packet
    st.session_state.delivery_result = None
    add_event("Packet", "Semantic packet built and ready for transmission.", "success")


def show_audio_metrics(audio_meta: AudioMetadata | None) -> None:
    if not audio_meta:
        return
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Duration", f"{audio_meta.processed_duration_sec:.2f}s")
    col_b.metric("Sample Rate", f"{audio_meta.sample_rate_hz} Hz")
    col_c.metric("Peak Level", f"{audio_meta.peak_dbfs:.1f} dBFS")
    col_d.metric("RMS Level", f"{audio_meta.rms_dbfs:.1f} dBFS")


def main() -> None:
    initialize_state()
    apply_theme()
    config = render_sidebar()
    render_hero(config)

    st.markdown("### 1) Audio Capture and Preprocessing")

    # Keys include a nonce so Clear can force-reset widget state.
    audio_from_mic = st.audio_input(
        "Record a short speech sample (recommended: 5-30 seconds)",
        key=f"audio_input_{st.session_state.audio_widget_nonce}",
    )
    audio_uploaded = st.file_uploader(
        "Or upload an audio file",
        type=["wav", "mp3", "ogg", "m4a"],
        key=f"audio_upload_{st.session_state.audio_widget_nonce}",
    )

    if audio_from_mic is not None:
        register_audio(audio_from_mic.getvalue(), "microphone", "audio/wav")
    elif audio_uploaded is not None:
        register_audio(
            audio_uploaded.getvalue(),
            "file upload",
            audio_uploaded.type or "audio/wav",
        )

    if st.session_state.raw_audio_bytes:
        st.caption(f"Current sample source: `{st.session_state.audio_source}`")
        st.audio(st.session_state.raw_audio_bytes, format=st.session_state.raw_audio_format)
    else:
        st.info("No audio sample yet. Record from microphone or upload a file.")

    run_col, clear_col = st.columns([3, 1])
    process_disabled = not st.session_state.raw_audio_bytes
    with run_col:
        if st.button(
            "Encode",
            type="primary",
            use_container_width=True,
            disabled=process_disabled,
        ):
            status = st.status("Running audio pipeline...", expanded=True)
            progress = st.progress(0)
            try:
                status.write("Step 1/4: Preprocessing audio and validating transcript...")
                process_and_transcribe(config)
                progress.progress(25)

                status.write("Step 2/4: Encoding semantic tokens with SemantiCodec...")
                codec_result = run_semantic_codec(st.session_state.processed_audio_bytes)
                st.session_state.semantic_token_file = codec_result["output_path"]
                st.session_state.semantic_token_count = codec_result["token_count"]
                st.session_state.semantic_codec_latency_ms = codec_result["latency_ms"]
                add_event(
                    "SemantiCodec",
                    f"Token file generated at {codec_result['output_path']} in {codec_result['latency_ms']} ms.",
                    "success",
                )
                progress.progress(60)

                status.write("Step 3/4: Decoding tokens back to WAV preview...")
                decode_result = decode_semantic_tokens(st.session_state.semantic_token_file)
                st.session_state.decoded_audio_bytes = decode_result["wav_bytes"]
                st.session_state.decoded_audio_sample_rate = decode_result["sample_rate"]
                st.session_state.semantic_decode_latency_ms = decode_result["latency_ms"]
                add_event(
                    "Decode",
                    f"Decoded token file to audio in {decode_result['latency_ms']} ms.",
                    "success",
                )
                progress.progress(90)

                status.write("Step 4/4: Finalizing UI state...")
                progress.progress(100)
                status.update(label="Pipeline complete", state="complete", expanded=False)
                st.success("Encoding complete. Token file and decoded preview are ready.")
            except Exception as exc:
                status.update(label="Pipeline failed", state="error", expanded=True)
                add_event("Pipeline", str(exc), "error")
                st.error(str(exc))
    with clear_col:
        if st.button("Clear", use_container_width=True):
            st.session_state.raw_audio_bytes = b""
            st.session_state.raw_audio_format = "audio/wav"
            st.session_state.audio_fingerprint = ""
            st.session_state.audio_source = ""
            st.session_state.manual_transcript = ""
            st.session_state.audio_widget_nonce += 1
            clear_pipeline_outputs()
            add_event("Capture", "Audio sample, widgets, and pipeline state cleared.", "info")
            st.rerun()

    if st.session_state.processed_audio_bytes:
        st.caption("Preprocessed audio preview (mono, normalized, trimmed):")
        st.audio(st.session_state.processed_audio_bytes, format="audio/wav")
    show_audio_metrics(st.session_state.audio_meta)

    if st.session_state.semantic_token_file:
        t1, t2, t3 = st.columns(3)
        t1.metric("SemantiCodec Tokens", st.session_state.semantic_token_count)
        t2.metric("Encode Latency", f"{st.session_state.semantic_codec_latency_ms} ms")
        t3.metric("Token File", Path(st.session_state.semantic_token_file).name)

        token_path = Path(st.session_state.semantic_token_file)
        if token_path.exists():
            with token_path.open("rb") as token_file:
                st.download_button(
                    "Download Semantic Token File",
                    data=token_file.read(),
                    file_name=token_path.name,
                    mime="application/octet-stream",
                    use_container_width=True,
                )

    st.markdown("### 2) Semantic Encoding")
    
    if st.session_state.decoded_audio_bytes:
        st.caption(
            f"Decoded preview ready ({st.session_state.decoded_audio_sample_rate} Hz, "
            f"{st.session_state.semantic_decode_latency_ms} ms)."
        )
        st.audio(st.session_state.decoded_audio_bytes, format="audio/wav")
        st.download_button(
            "Download Decoded Audio (WAV)",
            data=st.session_state.decoded_audio_bytes,
            file_name="decoded_preview.wav",
            mime="audio/wav",
            use_container_width=True,
        )

    st.markdown("### 3) Transmit to Receiver")
    transmit_disabled = st.session_state.semantic_packet is None
    if st.button(
        "Transmit Packet",
        use_container_width=True,
        disabled=transmit_disabled,
    ):
        with st.spinner("Sending semantic packet to receiver..."):
            try:
                result = send_packet(
                    packet=st.session_state.semantic_packet,
                    transport_mode=config["transport_mode"],
                    endpoint=config["receiver_endpoint"],
                    timeout_sec=config["network_timeout"],
                    bearer_token=config["bearer_token"],
                )
                st.session_state.delivery_result = result
                add_event("Delivery", result.message, "success" if result.ok else "error")
            except Exception as exc:
                st.session_state.delivery_result = None
                add_event("Delivery", str(exc), "error")
                st.error(str(exc))

    delivery: DeliveryResult | None = st.session_state.delivery_result
    if delivery:
        if delivery.ok:
            st.success(
                f"{delivery.message} ({delivery.transport}, {delivery.latency_ms} ms)"
            )
        else:
            st.error(
                f"{delivery.message} (status={delivery.status_code}, {delivery.transport})"
            )
        d1, d2, d3 = st.columns(3)
        d1.metric("Transport", delivery.transport)
        d2.metric("Status", delivery.status_code)
        d3.metric("Latency", f"{delivery.latency_ms} ms")
        if delivery.response_payload is not None:
            st.markdown("#### Receiver Response")
            st.json(delivery.response_payload)



if __name__ == "__main__":
    main()
