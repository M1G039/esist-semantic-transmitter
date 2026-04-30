# ///////////////////////////////////// IMPORTS /////////////////////////////////////////

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import json , os, sys, tempfile, time, uuid, wave, hashlib, importlib
import streamlit as st
from pathlib import Path
from frontend.ui_theme import apply_theme, log_item, pipeline_card, render_hero, show_audio_metrics

from frontend.app_state import (
        initialize_state,
        register_audio,
        clear_pipeline_outputs,
        add_event,
)

from ai_sound.pipeline import prepare_audio_input
from ai_sound.codec import run_semantic_codec, decode_semantic_tokens
from tx_comms.transport import (
        DeliveryResult,
        TRANSPORT_DEMO,
        TRANSPORT_MQTT,
        prepare_semantic_packet,
        send_packet
)
from tx_comms.tx_mqttclient_wrapper import ConnectionState # e.g. only access to ConnectionState artifact on the mqtt client...
# This way of importing prevents the UI to access low level details!

# ///////////////////////////////////// IMPORTS /////////////////////////////////////////

st.set_page_config(
    page_title="Semantic Audio Transmitter",
    page_icon="SAT",
    layout="wide",
)

# TODO: what?? did I add this? ...

# ///////////////////////////////////// UI DOMAIN /////////////////////////////////////////

def render_sidebar() -> dict:

    with st.sidebar:
        st.markdown("### Contacts")
        st.session_state.contact_username = st.text_input(
            "Search Contact",
            value=st.session_state.get("contact_username", "user123")
        )

    return {
        "speaker_label": st.session_state.speaker_label.strip() or "Speaker A",
        "session_id": st.session_state.session_id.strip() or f"tx-{uuid.uuid4().hex[:8]}",
        "language_hint": st.session_state.language_hint,
        "transport_mode": st.session_state.transport_mode,
        "contact_username": st.session_state.contact_username.strip(),
        "bearer_token": st.session_state.bearer_token.strip(),
        "network_timeout": int(st.session_state.network_timeout),
    }


def process_and_transcribe() -> None:
    result = prepare_audio_input(
        raw_audio_bytes=st.session_state.raw_audio_bytes,
        manual_transcript=st.session_state.manual_transcript,
    )

    st.session_state.processed_audio_bytes = result.processed_audio_bytes
    st.session_state.audio_meta = result.audio_meta
    st.session_state.transcript = result.transcript
    st.session_state.transcript_editor = result.transcript
    st.session_state.semantic_payload = None
    st.session_state.semantic_packet = None
    st.session_state.decoded_audio_bytes = b""
    st.session_state.semantic_decode_latency_ms = 0
    st.session_state.delivery_result = None

    if result.audio_meta:
        add_event(
            "Preprocess",
            f"Audio normalized to {result.audio_meta.sample_rate_hz} Hz mono and trimmed to "
            f"{result.audio_meta.processed_duration_sec:.2f}s.",
            "success",
        )

    if result.transcript:
        add_event("STT", "Manual transcript provided.", "info")
    else:
        add_event(
            "STT",
            "No manual transcript provided. You can still build tokens and edit transcript later.",
            "info",
        )


def build_packet_for_ui(config: dict) -> None:
    semantics, packet = prepare_semantic_packet(
        token_file_path=st.session_state.semantic_token_file,
        session_id=config["session_id"],
        speaker_label=config["speaker_label"],
        contact=config["contact_username"],
        audio_meta=st.session_state.audio_meta,
        language_hint=config["language_hint"],
        token_count=st.session_state.semantic_token_count,
    )
    st.session_state.semantic_payload = semantics
    st.session_state.semantic_packet = packet
    st.session_state.delivery_result = None
    add_event("Packet", "Codec packet built and ready for transmission.", "success")
# ///////////////////////////////////// UI DOMAIN /////////////////////////////////////////


# ///////////////////////////////////////// MAIN ///////////////////////////////////////////
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
                process_and_transcribe()
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

                status.write("Step 4/4: Building codec packet for transmission...")
                build_packet_for_ui(config)
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

    mqtt_not_connected = (
        st.session_state.transport_mode == TRANSPORT_MQTT
        and (
            st.session_state.mqtt_client is None
            or st.session_state.mqtt_client.connection_state != ConnectionState.CONNECTED
        )
    ) # also expanded the condition for the trasmit button to be disabled ot include the mqtt
    transmit_disabled = st.session_state.semantic_packet is None or mqtt_not_connected

    # selection field for Mock Demo/MQTT transport mode with a little connection state feedback
    st.session_state.transport_mode = st.selectbox(
        "Transport Mode",
        options= [TRANSPORT_DEMO, TRANSPORT_MQTT],
        index=[TRANSPORT_DEMO, TRANSPORT_MQTT].index(st.session_state.transport_mode),
    )
    if st.session_state.transport_mode == TRANSPORT_MQTT:
        broker_host = st.session_state.get("mqtt_broker_host", "").strip()
        broker_port = int(st.session_state.get("mqtt_broker_port", 1883))

        if broker_host and st.session_state.mqtt_client is None:
            from tx_comms.tx_mqttclient_wrapper import MQTT_ClientWrapper
            try:
                st.session_state.mqtt_client = MQTT_ClientWrapper(
                    broker_host=broker_host,
                    broker_port=broker_port,
                )
                st.session_state.mqtt_client.connect()
                add_event("MQTT", f"Connecting to broker at {broker_host}:{broker_port}...", "info")
            except Exception as exc:
                st.session_state.mqtt_client = None
                add_event("MQTT", str(exc), "error")
                st.error(str(exc))

        if st.session_state.mqtt_client is not None:
            state = st.session_state.mqtt_client.connection_state
            if state == ConnectionState.CONNECTED:
                st.success(f"Connected to MQTT broker at {broker_host}:{broker_port}")
            elif state == ConnectionState.CONNECTING:
                st.info(f"Connecting to MQTT broker at {broker_host}:{broker_port}...")
            else:
                st.error("Not connected to MQTT broker")
        else:
            st.error("MQTT broker host is not configured.")
    # -------------------------------------------------------
    if st.button(
        "Transmit Packet",
        use_container_width=True,
        disabled=transmit_disabled,
    ):
        with st.spinner("Sending semantic packet to receiver..."):
            try:
                result = send_packet(
                    packet=st.session_state.semantic_packet,
                    # transport_mode=config["transport_mode"],
                    transport_mode=st.session_state.transport_mode,
                    mqtt_client=st.session_state.mqtt_client,
                    # endpoint=config["receiver_endpoint"], # no enpoints in MQTT
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
# ///////////////////////////////////////// MAIN ///////////////////////////////////////////
