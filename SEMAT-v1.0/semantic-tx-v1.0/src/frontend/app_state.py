from __future__ import annotations

import uuid
import hashlib
from datetime import datetime

import streamlit as st
from tx_comms.transport import TRANSPORT_DEMO
from tx_comms.tx_mqttclient_wrapper import MQTT_BROKER_ADDRESS, DEFAULT_PORT

def initialize_state() -> None:
    defaults = {
        "session_id": f"tx-{uuid.uuid4().hex[:8]}",
        "speaker_label": "Speaker A",
        "language_hint": "auto",
        "transport_mode": TRANSPORT_DEMO,
        # "receiver_endpoint": "http://localhost:8000/semantic-packet", TODO: remove later
        "contact_username": "user123",
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
        "mqtt_broker_host": MQTT_BROKER_ADDRESS,
        "mqtt_broker_port": DEFAULT_PORT,
        "mqtt_client": None
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
