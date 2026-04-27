import paho.mqtt.client as mqtt
import json
import time
from cryptography.fernet import Fernet

BROKER = "broker.hivemq.com"
PORT = 1883
TOPICO_RECEBER = "feup/equipa9/mensagem"
TOPICO_STATUS  = "feup/equipa9/status"

# Tem de ser a mesma chave do modulo_comunicacao.py!
CHAVE = b"R9blsT9Won2e6GwB3JGflM_FyAdHmJQXQFINozSlngU="
fernet = Fernet(CHAVE)

def ao_ligar(client, userdata, flags, rc, properties=None):
    print("✓ Receiver ligado!")
    client.subscribe(TOPICO_RECEBER)
    print(f"✓ À escuta em: {TOPICO_RECEBER}")

def ao_receber(client, userdata, msg):
    try:
        # Desencripta a mensagem
        mensagem_desencriptada = fernet.decrypt(msg.payload).decode()
        dados = json.loads(mensagem_desencriptada)
        print(f"\n📨 Mensagem recebida: {dados['transcript']['text']}")
        print(f"   Intent: {dados['semantic_encoding']['intent']}")
        print(f"   Tone:   {dados['semantic_encoding']['tone']}")

        # Envia confirmação de volta
        resposta = json.dumps({"status": "read", "mensagem_recebida": dados['transcript']['text']}, ensure_ascii=False)
        client.publish(TOPICO_STATUS, resposta, qos=1)
        print("✓ Confirmação enviada de volta!")
    except Exception as e:
        print(f"✗ Erro ao processar mensagem: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = ao_ligar
client.on_message = ao_receber

client.connect(BROKER, PORT)
print("Receiver à espera de mensagens...")
client.loop_forever()