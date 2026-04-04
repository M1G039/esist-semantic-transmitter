from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib, json, time, uuid

from stt_llm.audio_processing import AudioMetadata
from tx_comms.tx_mqttclient_wrapper import MQTT_ClientWrapper, ConnectionState

@dataclass
class DeliveryResult:
    ok: bool
    transport: str
    status_code: int
    latency_ms: int
    message: str
    response_payload: dict | str | None = None


def build_semantic_packet(
    *,
    transcript: str,
    semantics: dict,
    session_id: str,
    speaker_label: str,
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
    if transport_mode == "Mock demo":
        preview = packet.get("semantic_encoding", {}).get("semantic_summary", "")
        return DeliveryResult(
            ok=True,
            transport="Mock demo",
            status_code=200,
            latency_ms=35,
            message="Packet delivered to mock receiver successfully.",
            response_payload={
                "receiver_ack": True,
                "receiver_preview": f"Receiver will reconstruct: {preview}",
            },
        )
    if transport_mode == "MQTT":
        if mqtt_client == None:
            raise ValueError("There is no MQTT Client provided.")

            if mqtt_client.connection_state != ConnectionState.CONNECTED:
                raise ValueError("MQTT Client is not connected to the Broker.")

            # if the checks give an ALL CLEAR we tell the backend to send the packet
            start= time.perf_counter()
            message_id=mqtt_client.send_payload(
                text=packet["transcript"]["text"], metadata=packet)
            latency_ms= int((time.perf_counter()-start)*1000)

            return DeliveryResult(
                ok=True,
                transport="MQTT",
                status_code=0,
                latency_ms=latency_ms,
                message=f"[*] Packet published. Message ID: {message_id}",
                response_payload={"message_id": message_id},
            )

    raise ValueError(f"Unsupported transport mode: {transport_mode}")

