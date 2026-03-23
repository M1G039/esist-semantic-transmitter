from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import time
import uuid

import requests

from transmitter.audio_processing import AudioMetadata


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
    endpoint: str,
    timeout_sec: int,
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

    if transport_mode == "HTTP POST":
        headers = {}
        if bearer_token.strip():
            headers["Authorization"] = f"Bearer {bearer_token.strip()}"

        start = time.perf_counter()
        response = requests.post(
            endpoint.strip(),
            json=packet,
            headers=headers or None,
            timeout=timeout_sec,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        payload: dict | str
        try:
            payload = response.json()
        except Exception:
            payload = response.text.strip()[:1000]

        return DeliveryResult(
            ok=response.ok,
            transport="HTTP POST",
            status_code=response.status_code,
            latency_ms=latency_ms,
            message="Packet delivered." if response.ok else "Receiver returned an error.",
            response_payload=payload,
        )

    if transport_mode == "WebSocket":
        try:
            import websocket
        except Exception as exc:
            raise RuntimeError(
                "websocket-client dependency is missing. Install it to use WebSocket transport."
            ) from exc

        start = time.perf_counter()
        ws = websocket.create_connection(endpoint.strip(), timeout=timeout_sec)
        try:
            ws.send(json.dumps(packet, ensure_ascii=False))
            response_message = ws.recv()
        finally:
            ws.close()

        latency_ms = int((time.perf_counter() - start) * 1000)
        parsed_payload: dict | str
        try:
            parsed_payload = json.loads(response_message)
        except Exception:
            parsed_payload = str(response_message)

        return DeliveryResult(
            ok=True,
            transport="WebSocket",
            status_code=101,
            latency_ms=latency_ms,
            message="Packet delivered over WebSocket.",
            response_payload=parsed_payload,
        )

    raise ValueError(f"Unsupported transport mode: {transport_mode}")

