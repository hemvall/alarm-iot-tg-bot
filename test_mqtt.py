# -*- coding: utf-8 -*-
# Diagnostic standalone : se connecte au broker et affiche tout ce qui arrive
# sur les topics ppe2025/alarm/*. Lancer dans un terminal séparé du bot.

import time
import paho.mqtt.client as mqtt

from config import BROKER_HOST, BROKER_PORT, MQTT_TRANSPORT, MQTT_WS_PATH, TOPIC_PREFIX


def on_connect(client, userdata, flags, rc):
    print("[on_connect] rc=%d (%s)" % (rc, mqtt.connack_string(rc)))
    if rc == 0:
        client.subscribe(TOPIC_PREFIX + "/#")
        print("[OK] Abonné à %s/#" % TOPIC_PREFIX)


def on_disconnect(client, userdata, rc):
    print("[on_disconnect] rc=%d" % rc)


def on_message(client, userdata, msg):
    print("[MSG] %s -> %s" % (msg.topic, msg.payload.decode(errors="replace")))


print("Tentative connexion à %s:%d (transport=%s) ..." % (BROKER_HOST, BROKER_PORT, MQTT_TRANSPORT))
c = mqtt.Client(client_id="alarm_diag", transport=MQTT_TRANSPORT)
c.on_connect = on_connect
c.on_disconnect = on_disconnect
c.on_message = on_message
if MQTT_TRANSPORT == "websockets":
    c.ws_set_options(path=MQTT_WS_PATH)
    print("[INFO] WebSocket path=%s" % MQTT_WS_PATH)
if BROKER_PORT in (8883, 8884):
    c.tls_set()
    print("[INFO] TLS activé")

try:
    c.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
except Exception as exc:
    print("[ERREUR connect()] %s" % exc)
    raise SystemExit(1)

c.loop_start()
print("Boucle démarrée. Ctrl+C pour quitter.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    c.loop_stop()
    c.disconnect()
