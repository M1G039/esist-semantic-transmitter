from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib, json, time, uuid, base64

from pathlib import Path

from ai_sound.audio_processing import AudioMetadata
from tx_comms.tx_mqttclient_wrapper import MQTT_ClientWrapper, ConnectionState
from ai_sound.semantic import normalize_transcript, encode_semantics

TRANSPORT_DEMO="Mock Demo"
TRANSPORT_MQTT="MQTT"

@dataclass
class DeliveryResult:
    ok: bool
    transport: str
    status_code: int
    latency_ms: int
    message: str
    response_payload: dict | str | None = None


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def prepare_semantic_packet(
    *,
    token_file_path: str,
    session_id: str,
    speaker_label: str,
    contact: str,
    audio_meta: AudioMetadata | None,
    language_hint: str = "auto",
    token_count: int | None = None,
) -> tuple[dict, dict]:
    token_path = Path(token_file_path)

    if not token_path.exists():
        raise ValueError("Semantic token file not found. Current path is {token_path}")

    token_bytes = token_path.read_bytes()
    if not token_bytes:
        raise ValueError("Semantic token file is empty")

    token_b64 = base64.b64encode(token_bytes).decode("ascii")
    created_at = datetime.now(timezone.utc).isoformat()

    payload_summary = {
            "codec_name": "SemantiCodec",
            "file_name": token_path.name,
            "file_size_bytes": len(token_bytes),
            "token_count": token_count if token_count is not None else 0,
            "encoding": "base64",
            "sha256": _sha256_bytes(token_bytes),
    }

    packet = {
            "packet_id": str(uuid.uuid4()),
            "packet_type": "semantic_audio_codec",
            "protocol_version": "2.0",
            "created_at_utc": created_at,
            "sender": {
                    "team": "Transmitter",
                    "speaker_label": speaker_label,
                    "contact": contact,
            },
            "transcript": None,
            "language_hint": language_hint,
            "audio_profile": audio_meta.as_dict() if audio_meta else None,
            "semantic_encoding": {
                "codec_name": "SemantiCodec",
                "representation": "semantic_token_file",
                "token_count": token_count if token_count is not None else 0,
                "file_name": token_path.name,
                "file_size_bytes": len(token_bytes),
                "encoding": "base64",
            },
            "payload": {
                "token_file_b64": token_b64,
            },
    }

    cannonical = json.dumps(packet, sort_keys=True, ensure_ascii=False).encode("utf-8")
    packet["checksum_sha256"] = hashlib.sha256(cannonical).hexdigest()

    return payload_summary, packet


def build_semantic_packet(
    *,
    transcript: str,
    semantics: dict,
    session_id: str,
    speaker_label: str,
    contact: str,
    audio_meta: AudioMetadata | None,
    language_hint: str = "auto",
) -> dict:
    packet = {
        "packet_id": str(uuid.uuid4()),
        "protocol_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "sender": {
            "team": "Transmitter",
            "speaker_label": speaker_label,
        },
        "destination": contact,
        "transcript": {
            "text": transcript,
            "language_hint": language_hint,
        },
        "semantic_encoding": semantics,
        "audio_profile": audio_meta.as_dict() if audio_meta else None,
    }

    canonical = json.dumps(packet, sort_keys=True, ensure_ascii=False).encode("utf-8")
    packet["checksum_sha256"] = hashlib.sha256(canonical).hexdigest()
    return packet

def send_packet(
    *,
    packet: dict,
    transport_mode: str,
    mqtt_client: MQTT_ClientWrapper | None=None,
    timeout_sec: int=12,
    bearer_token: str = "",
) -> DeliveryResult:
    if packet is None:
        raise ValueError("There is no packet avaliable to send...")

    if transport_mode == TRANSPORT_DEMO:
        payload_info = packet.get("semantic_encoding", {})
        return DeliveryResult(
            ok=True,
            transport=TRANSPORT_DEMO,
            status_code=200,
            latency_ms=35,
            message="Packet delivered to mock receiver successfully.",
            response_payload={
                "receiver_ack": True,
                "packet_type": packet.get("packet_type"),
                "codec_name": payload_info.get("codec_name"),
                "token_count": payload_info.get("token_count"),
                "file_name": payload_info.get("file_name"),
            },
    )

    if transport_mode == TRANSPORT_MQTT:
        if mqtt_client == None:
            raise ValueError("There is no MQTT Client provided.")

        if mqtt_client.connection_state != ConnectionState.CONNECTED:
            raise ValueError("MQTT Client is not connected to the Broker.")

        # if the checks give an ALL CLEAR we tell the backend to send the packet
        start= time.perf_counter()
        message_id=mqtt_client.send_payload(packet)
        latency_ms= int((time.perf_counter()-start)*1000)

        return DeliveryResult(
            ok=True,
            transport=TRANSPORT_MQTT,
            status_code=0,
            latency_ms=latency_ms,
            message=f"[*] Packet published. Message ID: {message_id}",
            response_payload={
                "message_id": message_id,
                "packet_id": packet.get("packet_id"),
                "packet_type": packet.get("packet_type"),
                "topic": getattr(mqtt_client, "tx_topic", None),
            },
        )


    raise ValueError(f"Unsupported transport mode: {transport_mode}")

