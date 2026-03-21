import modulo_comunicacao as comms
import time

print("A ligar...")
time.sleep(2)

if comms.esta_ligado():
    print("✓ Ligado!\n")
else:
    print("✗ Não ligou. Verifica a internet.")

# Testa o envio com o formato da equipa de UI
sucesso = comms.enviar(
    texto="Olá, este é o meu progresso no projeto.",
    semantic_encoding={
        "language_guess": "unknown",
        "intent": "statement",
        "tone": "neutral",
        "keywords": ["olá", "este", "meu", "progresso", "projeto"],
        "entities": {"numbers": [], "emails": [], "urls": []},
        "semantic_summary": "Olá, este é o meu progresso no projeto.",
        "word_count": 8,
        "character_count": 39
    },
    audio_profile={
        "original_duration_sec": 9.6,
        "processed_duration_sec": 9.6,
        "sample_rate_hz": 16000,
        "channels": 1,
        "peak_dbfs": -1.0,
        "rms_dbfs": -19.354
    }
)

if sucesso:
    print("✓ Mensagem enviada com sucesso!")
else:
    print("✗ Erro ao enviar mensagem.")

time.sleep(3)

respostas = comms.obter_respostas()
if respostas:
    print(f"📩 Respostas da equipa 10: {respostas}")
else:
    print("(sem respostas — normal se a equipa 10 não estiver ligada)")