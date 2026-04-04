import paho.mqtt.client as mqtt
import time
import json
from enum import Enum                   # creating enum classes to make things more intuitive
from datetime import datetime, timezone # more for message metadata
from typing import Optional, Dict, Callable
import uuid

#  ---------------- definitions/config

TOPIC = "team9/messages"
FEEDBACK_TOPIC = "semantic/tx"

QoS = 1 # by default - prof said not to mess with this too much for know
PORT =  1883 # 8883 # this port uses TLS/SSL - no eavesdropping on traffic

"""
*** Brief Description of this code ***

- This is a wrapper for mqtt client that already exits from the paho-mqtt lib
- It contains the client and helper methods to configure +  connect it as well as
flags to send info back to the UI for displying purposes (for example,  the statis of the message and/or the status of the connection...)
"""

# --------------- Useful enum classes -Just for readablility -some others could be added, for example for the ports, QoS levels, etc.

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING   = "connecting"
    CONNECTED    = "connected"
    ERROR        = "error"

class MessageStatus(Enum):
    SENT         = "sent"
    PENDING      = "pending"
    READ         = "read"
    FAILED       = "failed"

#-------------------------------------

class MQTT_ClientWrapper:
    def __init__(
        self,
        broker_host    : str, # this is url
        broker_port    : int=PORT,
        tx_topic       : str=TOPIC,
        feedback_topic : str=FEEDBACK_TOPIC,
        client_id      : Optional[str] = None,
        qos            : int= QoS,
        on_connection_state_change : Optional[Callable[[ConnectionState], None]] = None,
        on_message_status_change   : Optional[Callable[[str, MessageStatus], None]] = None,
    ) -> None:
        self.broker_host    = broker_host
        self.broker_port    = broker_port
        self.tx_topic       = tx_topic
        self.feedback_topic = feedback_topic
        self.client_id      = client_id or f"tx-{uuid.uuid4()}"
        self._mqtt_client   = mqtt.Client(client_id=self.client_id)
        #self._mqtt_client.tls_set(ca_certs="ca.crt") for now it stays commented but these certs must be in put the src directory


        self.on_connection_state_change = on_connection_state_change
        self.on_message_status_change = on_message_status_change

        self.connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self.message_status: Dict[str, MessageStatus] = {}
        self._last_error: Optional[str] = None

        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.on_message = self._on_message


# ----------------- API >> Wrapper (dis)connect + send functions

    # connect to the MQTT broker
    def connect(self, keepalive: int = 60) -> None:
        self._set_connection_state(ConnectionState.CONNECTING)

        try:
            self._mqtt_client.connect(self.broker_host, self.broker_port, keepalive)
            self._mqtt_client.loop_start()

        except Exception as e:
            self._last_error = str(e)
            self._set_connection_state(ConnectionState.ERROR)

    # disconnect the client from the MQTT broker
    def disconnect(self) -> None:
        try:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()

        finally:
            self._set_connection_state(ConnectionState.DISCONNECTED)


    # building the JSON formatted payload to send to the broker
    def build_payload(self, text: str, metadata: Dict)  -> Dict:
        return {
            "message_id": str(uuid.uuid4()) ,
            "timestamp" : int(time.time())  ,
            "text"      : text              ,
            "metadata"  : metadata          ,
        }

    # function to send the payload over to the broker
    def send_payload(self, text: str, metadata: Dict) -> str:
        if self.connection_state != ConnectionState.CONNECTED:
            raise RuntimeError("Disconnected from Broker...")

        # build the payload and assign an id
        payload = self.build_payload(text, metadata)
        message_id = payload["message_id"]

        # publish the payload to the topic
        result = self._mqtt_client.publish(
            self.tx_topic,
            json.dumps(payload),
            qos = QoS,
        )

        self._update_message_status(message_id, MessageStatus.PENDING)

        return message_id

# -------------------------- Getters --------------------------

    #  used to check on the connection state
    @property
    def get_connection_state(self) -> ConnectionState:
        return self.connection_state

    # used to check on the status of the message
    @property
    def get_message_status(self, message_id: str) -> Optional[MessageStatus]:
        return self.message_status.get(message_id)

    @property
    def get_last_error(self) -> Optional[str]:
        return self._last_error


# ---------- Connection/Disconnection from Broker -------------


    # connect/subscribe client to mqtt broker
    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self._set_connection_state(ConnectionState.CONNECTED)
            self._mqtt_client.subscribe(self.feedback_topic, qos=QoS)

        else:
            self._last_error = f"Connect failed with rc = {rc}"
            self._set_connection_state(ConnectionState.ERROR)

    # disconnect from broker
    def _on_disconnect(self, client, userdata, rc) -> None:

        if rc != 0:
            self._last_error = f"Unexpected disconnect rc = {rc}"

        self._set_connection_state(ConnectionState.DISCONNECTED)


    # when messages are sean we update the message ID and the status
    def _on_message(self, client, userdata, msg) -> None:

        if msg.topic != self.feedback_topic:
            return

        try:
            data =json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            self._last_error = "Invalid JSON on feedback topic"
            return

        message_id = data.get("message_id")
        status_str = data.get("status")
        error = data.get("error")

        if not message_id or not status_str:
            self._last_error = "Incomplete payload on feedback"
            return

        if error:
            self._last_error = error

        status_map = {
            "pending": MessageStatus.PENDING,
            "sent"   : MessageStatus.SENT,
            "read"   : MessageStatus.READ,
            "failed" : MessageStatus.FAILED,
        }

        status = status_map.get(status_str.lower())

        if status is None:
            self._last_error = f"Unknown feedback status: {status_str}"
            return

        self._update_message_status(message_id, status)

# --------------------------- Helper Methods ---------------------------

    # for setting a change in the state of the connection to the broker
    def _set_connection_state(self, new_state: ConnectionState) -> None:
        if self.connection_state == new_state:
            return

        self.connection_state = new_state

        if self.on_connection_state_change:
            self.on_connection_state_change(new_state)


    # for updating the message status when it change between sent, read, etc.
    def _update_message_status(self, message_id: str, new_status: MessageStatus) -> None:
        self.message_status[message_id] = new_status

        if self.on_message_status_change:
            self.on_message_status_change(message_id, new_status)


