import paho.mqtt.client as mqtt
import json
import time
import uuid
import hashlib
from datetime import datetime, timezone
from cryptography.fernet import Fernet

BROKER = "broker.hivemq.com"
PORT = 1883
TOPICO_ENVIAR = "feup/equipa9/mensagem"
TOPICO_STATUS = "feup/equipa9/status"


# chave nova corre: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CHAVE = b"R9blsT9Won2e6GwB3JGflM_FyAdHmJQXQFINozSlngU="

try:
    fernet = Fernet(CHAVE)
except Exception:
    print("⚠ Chave inválida! A correr sem encriptação.")
    fernet = None

# Guarda o estado da ligação e as mensagens
estado = {
    "ligado": False,
    "mensagens": []
}

def ao_ligar(client, userdata, flags, rc, properties=None):
    if rc == 0:
        estado["ligado"] = True
        client.subscribe(TOPICO_STATUS)

def ao_desligar(client, userdata, rc, properties=None):
    estado["ligado"] = False
    if rc != 0:
        print("⚠ Ligação perdida! A tentar reconectar...")

def ao_receber_mensagem(client, userdata, msg):
    dados = json.loads(msg.payload.decode())
    estado["mensagens"].append(dados)

# Cria o cliente MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = ao_ligar
client.on_disconnect = ao_desligar
client.on_message = ao_receber_mensagem
client.reconnect_delay_set(min_delay=1, max_delay=5)
client.connect(BROKER, PORT)
client.loop_start()

def construir_payload(texto, semantic_encoding, audio_profile, speaker_label="Speaker A"):
    return json.dumps({
        "packet_id": str(uuid.uuid4()),
        "protocol_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "session_id": f"tx-{str(uuid.uuid4())[:8]}",
        "sender": {
            "team": "Transmitter",
            "speaker_label": speaker_label
        },
        "transcript": {
            "text": texto,
            "language_hint": "auto"
        },
        "semantic_encoding": semantic_encoding,
        "audio_profile": audio_profile,
        "checksum_sha256": hashlib.sha256(texto.encode()).hexdigest()
    }, ensure_ascii=False)

def esta_ligado():
    """A equipa de UI usa isto para saber se há ligação."""
    return estado["ligado"]

def enviar(texto, semantic_encoding, audio_profile, speaker_label="Speaker A"):
    """A equipa de UI chama esta função para enviar uma mensagem."""

    # Espera até 10 segundos pela ligação
    tentativas = 0
    while not estado["ligado"] and tentativas < 10:
        print("⏳ À espera de ligação...")
        time.sleep(1)
        tentativas += 1

    if not estado["ligado"]:
        print("✗ Não foi possível ligar. Mensagem não enviada.")
        return False

    mensagem_json = construir_payload(texto, semantic_encoding, audio_profile, speaker_label)

    
    if fernet:
        dados_a_enviar = fernet.encrypt(mensagem_json.encode()).decode()
        encriptado = True
    else:
        dados_a_enviar = mensagem_json
        encriptado = False

    
    tamanho_enviado = len(dados_a_enviar.encode("utf-8"))
    duracao = audio_profile.get("original_duration_sec", 3)
    tamanho_audio = int(16000 * 16 / 8 * duracao)
    reducao = (1 - tamanho_enviado / tamanho_audio) * 100
    print(f"\n  Encriptação:       {'✓ ativa' if encriptado else '✗ inativa'}")
    print(f"  Dados enviados:    {tamanho_enviado} bytes")
    print(f"  Áudio original:    {tamanho_audio:,} bytes")
    print(f"  Redução bandwidth: {reducao:.1f}%\n")

    resultado = client.publish(TOPICO_ENVIAR, dados_a_enviar, qos=1)
    return resultado.rc == 0

def obter_respostas():
    """A equipa de UI usa isto para ver as confirmações da equipa 10."""
    respostas = estado["mensagens"].copy()
    estado["mensagens"].clear()
    return respostas