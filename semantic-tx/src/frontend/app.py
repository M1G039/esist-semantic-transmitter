from __future__ import annotations

from datetime import datetime
import hashlib, json, os, uuid

import streamlit as st

from stt_llm.audio_processing import AudioMetadata, AudioPreprocessError, preprocess_audio
from stt_llm.semantic import encode_semantics, normalize_transcript
from stt_llm.stt import STTError, transcribe_with_openai
from tx_comms.transport import DeliveryResult, build_semantic_packet, send_packet
from tx_comms.tx_mqttclient_wrapper import MQTT_ClientWrapper, ConnectionState
from frontend.ui_theme import apply_theme, log_item, pipeline_card


st.set_page_config(
    page_title="Semantic Audio Transmitter",
    page_icon="SAT",
    layout="wide",
)

def initialize_state() -> None:
    defaults = {
        "session_id": f"tx-{uuid.uuid4().hex[:8]}",
        "speaker_label": "Speaker A",
        "language_hint": "auto",
        "stt_mode": "Auto (OpenAI if key)",
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": "whisper-1",
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
        "delivery_result": None,
        "last_stt_provider": "N/A",
        "last_stt_latency_ms": 0,
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
    st.session_state.delivery_result = None
    st.session_state.last_stt_provider = "N/A"
    st.session_state.last_stt_latency_ms = 0


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
    with st.sidebar:
        st.markdown("## Transmitter Controls")

        st.session_state.speaker_label = st.text_input(
            "Speaker label",
            value=st.session_state.speaker_label,
        )
        st.session_state.session_id = st.text_input(
            "Session ID",
            value=st.session_state.session_id,
        )

        st.session_state.language_hint = st.selectbox(
            "Language hint",
            options=["auto", "en", "pt"],
            index=["auto", "en", "pt"].index(st.session_state.language_hint),
            help="Hint sent to STT and included in packet metadata.",
        )

        st.session_state.stt_mode = st.selectbox(
            "Speech-to-text mode",
            options=[
                "Auto (OpenAI if key)",
                "OpenAI Whisper API",
                "Manual transcript only",
            ],
            index=[
                "Auto (OpenAI if key)",
                "OpenAI Whisper API",
                "Manual transcript only",
            ].index(st.session_state.stt_mode),
        )

        st.session_state.openai_api_key = st.text_input(
            "OpenAI API key",
            type="password",
            value=st.session_state.openai_api_key,
        )
        st.session_state.openai_model = st.text_input(
            "Transcription model",
            value=st.session_state.openai_model,
        )

        st.session_state.transport_mode = st.selectbox(
            "Transport mode",
            options=[
                "Mock demo",
                "MQTT"
            ],
            index=["Mock demo",
                   "MQTT"].index(
                st.session_state.transport_mode
            ),
        )

        if st.session_state.transport_mode == "MQTT":
            if "mqtt_client" not in st.session_state:
                st.session_state.mqtt_client = MQTT_ClientWrapper(
                    broker_host="100.79.237.17" # this is placeholder - in future it should be the IP from the broker device (RPi??) in the network
                    # [or 10.227.xxx.xxx if in FEUP's eduroam]
                )
                st.session_state.mqtt_client.connect()

        if st.session_state.transport_mode not in ("Mock demo", "MQTT"):
            st.session_state.receiver_endpoint = st.text_input(
            "Receiver endpoint",
            value=st.session_state.receiver_endpoint,
        )

        # st.session_state.receiver_endpoint = st.text_input(
        #     "Receiver endpoint",
        #     value=st.session_state.receiver_endpoint,
        #     disabled=st.session_state.transport_mode == "Mock demo",
        # )
        st.session_state.bearer_token = st.text_input(
            "Bearer token (optional)",
            type="password",
            value=st.session_state.bearer_token,
        )
        st.session_state.network_timeout = st.slider(
            "Network timeout (seconds)",
            min_value=3,
            max_value=60,
            value=int(st.session_state.network_timeout),
        )

        if st.button("Load Demo Transcript", use_container_width=True):
            st.session_state.manual_transcript = (
                "Hello team, this is a semantic communication test. "
                "Please send this message to the receiver for voice reconstruction."
            )
            add_event("Demo", "Demo transcript loaded.", "info")

        if st.button("Start New Session", use_container_width=True):
            st.session_state.session_id = f"tx-{uuid.uuid4().hex[:8]}"
            st.session_state.raw_audio_bytes = b""
            st.session_state.raw_audio_format = "audio/wav"
            st.session_state.audio_fingerprint = ""
            st.session_state.audio_source = ""
            st.session_state.manual_transcript = ""
            clear_pipeline_outputs()
            add_event("Session", "New session started.", "info")
            st.rerun()

    return {
        "speaker_label": st.session_state.speaker_label.strip() or "Speaker A",
        "session_id": st.session_state.session_id.strip() or f"tx-{uuid.uuid4().hex[:8]}",
        "language_hint": st.session_state.language_hint,
        "stt_mode": st.session_state.stt_mode,
        "openai_api_key": st.session_state.openai_api_key.strip(),
        "openai_model": st.session_state.openai_model.strip() or "whisper-1",
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

    stt_mode = config["stt_mode"]
    manual = normalize_transcript(st.session_state.manual_transcript)

    if stt_mode == "Manual transcript only":
        transcript = manual
        if not transcript:
            raise ValueError("Manual transcript is empty.")
        add_event("STT", "Manual transcript mode selected.", "info")
    elif stt_mode == "Auto (OpenAI if key)" and not config["openai_api_key"]:
        transcript = manual
        if not transcript:
            raise STTError(
                "No OpenAI API key detected. Add a key, switch to manual mode, "
                "or write a manual transcript fallback."
            )
        add_event("STT", "OpenAI key missing, manual fallback used.", "info")
    else:
        if not st.session_state.processed_audio_bytes:
            raise AudioPreprocessError("Record or upload audio before automatic STT.")
        result = transcribe_with_openai(
            st.session_state.processed_audio_bytes,
            api_key=config["openai_api_key"],
            model=config["openai_model"],
            language_hint=config["language_hint"],
        )
        transcript = normalize_transcript(result.text)
        st.session_state.last_stt_provider = f"{result.provider} ({result.model})"
        st.session_state.last_stt_latency_ms = result.latency_ms
        add_event(
            "STT",
            f"Automatic transcription complete in {result.latency_ms} ms.",
            "success",
        )

    if not transcript:
        raise ValueError("Transcript is empty after processing.")

    st.session_state.transcript = transcript
    st.session_state.transcript_editor = transcript
    st.session_state.semantic_payload = None
    st.session_state.semantic_packet = None
    st.session_state.delivery_result = None


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

    status_capture = bool(st.session_state.raw_audio_bytes)
    status_stt = bool(st.session_state.transcript.strip())
    status_semantic = st.session_state.semantic_payload is not None
    status_packet = st.session_state.semantic_packet is not None
    status_delivery = bool(
        st.session_state.delivery_result and st.session_state.delivery_result.ok
    )

    step_cols = st.columns(5)
    cards = [
        ("1) Capture", "Short speech recording from user input.", status_capture),
        ("2) STT", "Whisper/OpenAI or manual transcript fallback.", status_stt),
        ("3) Semantics", "Intent, keywords, entities, summary extraction.", status_semantic),
        ("4) Packaging", "JSON semantic packet + checksum.", status_packet),
        ("5) Delivery", "Transmit to receiver (Mock/HTTP/WebSocket).", status_delivery),
    ]
    for col, (title, desc, done) in zip(step_cols, cards, strict=False):
        with col:
            st.markdown(pipeline_card(title, desc, done), unsafe_allow_html=True)

    st.markdown("### 1) Audio Capture and Preprocessing")
    audio_from_mic = st.audio_input("Record a short speech sample (recommended: 5-30 seconds)")
    audio_uploaded = st.file_uploader(
        "Or upload an audio file",
        type=["wav", "mp3", "ogg", "m4a"],
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

    st.session_state.manual_transcript = st.text_area(
        "Manual transcript fallback",
        value=st.session_state.manual_transcript,
        height=95,
        placeholder="Write transcript here if you want manual mode or fallback.",
    )

    run_col, clear_col = st.columns([3, 1])
    process_disabled = not (
        st.session_state.raw_audio_bytes or st.session_state.manual_transcript.strip()
    )
    with run_col:
        if st.button(
            "Process Audio + Generate Transcript",
            type="primary",
            use_container_width=True,
            disabled=process_disabled,
        ):
            with st.spinner("Processing speech and preparing semantic transmitter pipeline..."):
                try:
                    process_and_transcribe(config)
                    st.success("Transcript is ready. Continue to semantic encoding.")
                except Exception as exc:
                    add_event("Pipeline", str(exc), "error")
                    st.error(str(exc))
    with clear_col:
        if st.button("Clear", use_container_width=True):
            st.session_state.raw_audio_bytes = b""
            st.session_state.raw_audio_format = "audio/wav"
            st.session_state.audio_fingerprint = ""
            st.session_state.audio_source = ""
            st.session_state.manual_transcript = ""
            clear_pipeline_outputs()
            add_event("Capture", "Audio sample and pipeline state cleared.", "info")
            st.rerun()

    if st.session_state.processed_audio_bytes:
        st.caption("Preprocessed audio preview (mono, normalized, trimmed):")
        st.audio(st.session_state.processed_audio_bytes, format="audio/wav")
    show_audio_metrics(st.session_state.audio_meta)

    st.markdown("### 2) Semantic Encoding and Packet Build")
    st.session_state.transcript_editor = st.text_area(
        "Transcript (editable before packaging)",
        value=st.session_state.transcript_editor,
        height=130,
        placeholder="Transcript will appear here after STT or manual input.",
    )

    if st.button(
        "Build Semantic Packet",
        use_container_width=True,
        disabled=not st.session_state.transcript_editor.strip(),
    ):
        try:
            build_packet(config, st.session_state.transcript_editor)
            st.success("Semantic packet built successfully.")
        except Exception as exc:
            add_event("Packet", str(exc), "error")
            st.error(str(exc))

    if st.session_state.semantic_payload:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Intent", st.session_state.semantic_payload["intent"].title())
        m2.metric("Tone", st.session_state.semantic_payload["tone"].title())
        m3.metric("Keywords", len(st.session_state.semantic_payload["keywords"]))
        m4.metric(
            "Words",
            st.session_state.semantic_payload["word_count"],
        )

        semantic_col, packet_col = st.columns(2)
        with semantic_col:
            st.markdown("#### Semantic Encoding Output")
            st.json(st.session_state.semantic_payload)
        with packet_col:
            st.markdown("#### JSON Semantic Packet")
            st.code(
                json.dumps(st.session_state.semantic_packet, indent=2, ensure_ascii=False),
                language="json",
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
                    mqtt_client=st.session_state.get("mqtt_client"),
                    # packet=st.session_state.semantic_packet,
                    # transport_mode=config["transport_mode"],
                    # endpoint=config["receiver_endpoint"],
                    # timeout_sec=config["network_timeout"],
                    # bearer_token=config["bearer_token"],
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

    st.markdown("### Pipeline Timeline")
    if not st.session_state.event_log:
        st.caption("No events yet. Start by capturing audio and running the pipeline.")
    for event in reversed(st.session_state.event_log):
        st.markdown(
            log_item(event["time"], event["stage"], event["message"], event["status"]),
            unsafe_allow_html=True,
        )

    st.caption(
        "Transmitter aligned with project diagram: Audio Capture & Preprocessing -> STT -> "
        "Semantic Encoding -> Data Packaging -> Receiver Transmission."
    )


if __name__ == "__main__":
    main()
