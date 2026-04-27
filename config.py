import os

from dotenv import load_dotenv

load_dotenv()

# ── Telegram ───────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

# ── MQTT broker (doit correspondre à alarm_mqtt.py / web_alarm.py) ──
BROKER_HOST    = os.environ.get("MQTT_BROKER_HOST", "broker.hivemq.com")
BROKER_PORT    = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
MQTT_TRANSPORT = os.environ.get("MQTT_TRANSPORT", "tcp")    # "tcp" ou "websockets"
MQTT_WS_PATH   = os.environ.get("MQTT_WS_PATH", "/mqtt")
MQTT_CLIENT_ID = "alarm_tg_bot"

# ── Topics ─────────────────────────────────────────────────────
TOPIC_PREFIX      = "ppe2025/alarm"
TOPIC_MOTION      = TOPIC_PREFIX + "/motion"
TOPIC_SOUND       = TOPIC_PREFIX + "/sound"
TOPIC_ACCEL       = TOPIC_PREFIX + "/accel"
TOPIC_CTRL_BUZZER = TOPIC_PREFIX + "/control/buzzer_off"
TOPIC_CTRL_RESET  = TOPIC_PREFIX + "/control/reset"
TOPIC_CTRL_ARM    = TOPIC_PREFIX + "/control/arm"

# ── Persistance ────────────────────────────────────────────────
SUBSCRIBERS_FILE = "subscribers.json"

# ── Affichage ──────────────────────────────────────────────────
LEVEL_LABELS = {
    0: "🟢 OK",
    1: "🟡 ALERTE LÉGÈRE",
    2: "🔴 ALERTE ROUGE",
}
