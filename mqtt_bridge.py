# -*- coding: utf-8 -*-
# Pont MQTT pour le bot Telegram. Maintient l'état des capteurs publiés par
# alarm_mqtt.py et expose les commandes de contrôle (buzzer_off / reset).

import asyncio
import json
import threading
from datetime import datetime

import paho.mqtt.client as mqtt

from config import (
    BROKER_HOST, BROKER_PORT, MQTT_CLIENT_ID,
    MQTT_TRANSPORT, MQTT_WS_PATH,
    TOPIC_MOTION, TOPIC_SOUND, TOPIC_ACCEL,
    TOPIC_CTRL_BUZZER, TOPIC_CTRL_RESET, TOPIC_CTRL_ARM,
)


class AlarmBridge:
    def __init__(self):
        self._lock = threading.Lock()
        self.state = {
            "motion":       False,
            "sound":        False,
            "accel":        False,
            "level":        0,
            "armed":        None,    # None tant qu'aucun message reçu
            "last_update":  None,
            "distance_cm":  None,
            "sound_value":  None,
        }
        self._client = None
        self._connected = False
        self._loop = None
        self.on_level_change = None  # async callable(prev, new, snapshot)
        self.on_arm_change = None    # async callable(armed, snapshot)

    # ── Configuration ─────────────────────────────────────────
    def set_loop(self, loop):
        self._loop = loop

    # ── Lecture d'état ────────────────────────────────────────
    def get_state(self):
        with self._lock:
            return dict(self.state)

    def is_connected(self):
        return self._connected

    # ── Logique de niveau ─────────────────────────────────────
    @staticmethod
    def _compute_level(s):
        count = sum([s["motion"], s["sound"], s["accel"]])
        if count >= 3:
            return 2
        if count >= 2:
            return 1
        return 0

    # ── Callbacks MQTT ────────────────────────────────────────
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            client.subscribe(TOPIC_MOTION)
            client.subscribe(TOPIC_SOUND)
            client.subscribe(TOPIC_ACCEL)
            client.subscribe(TOPIC_CTRL_ARM)
            print("[MQTT] Connecté à %s:%d" % (BROKER_HOST, BROKER_PORT))
        else:
            self._connected = False
            print("[MQTT] Erreur connexion rc=%d" % rc)

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        print("[MQTT] Déconnecté rc=%d" % rc)

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return

        with self._lock:
            previous_level = self.state["level"]
            previous_armed = self.state["armed"]
            arm_event = False

            if msg.topic == TOPIC_MOTION:
                self.state["motion"] = bool(data.get("alarm", False))
                if "distance_cm" in data:
                    self.state["distance_cm"] = data["distance_cm"]
            elif msg.topic == TOPIC_SOUND:
                self.state["sound"] = bool(data.get("alarm", False))
                if "sound_value" in data:
                    self.state["sound_value"] = data["sound_value"]
            elif msg.topic == TOPIC_ACCEL:
                self.state["accel"] = bool(data.get("alarm", False))
            elif msg.topic == TOPIC_CTRL_ARM:
                if "armed" not in data:
                    return
                self.state["armed"] = bool(data["armed"])
                arm_event = self.state["armed"] != previous_armed
            else:
                return

            self.state["level"] = self._compute_level(self.state)
            self.state["last_update"] = data.get(
                "timestamp", datetime.now().isoformat()
            )
            new_level = self.state["level"]
            snapshot = dict(self.state)

        if new_level != previous_level and self.on_level_change and self._loop:
            asyncio.run_coroutine_threadsafe(
                self.on_level_change(previous_level, new_level, snapshot),
                self._loop,
            )

        if arm_event and self.on_arm_change and self._loop:
            asyncio.run_coroutine_threadsafe(
                self.on_arm_change(snapshot["armed"], snapshot),
                self._loop,
            )

    # ── Cycle de vie ──────────────────────────────────────────
    def start(self):
        self._client = mqtt.Client(client_id=MQTT_CLIENT_ID, transport=MQTT_TRANSPORT)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        if MQTT_TRANSPORT == "websockets":
            self._client.ws_set_options(path=MQTT_WS_PATH)
        if BROKER_PORT in (8883, 8884):
            self._client.tls_set()
        self._client.connect_async(BROKER_HOST, BROKER_PORT)
        self._client.loop_start()

    def stop(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    # ── Commandes de contrôle ─────────────────────────────────
    def buzzer_off(self):
        if self._client:
            self._client.publish(TOPIC_CTRL_BUZZER, "off", qos=1)

    def reset(self):
        if self._client:
            self._client.publish(TOPIC_CTRL_RESET, "reset", qos=1)
        with self._lock:
            self.state["motion"] = False
            self.state["sound"]  = False
            self.state["accel"]  = False
            self.state["level"]  = 0

    def set_armed(self, armed):
        if self._client:
            payload = json.dumps({"armed": bool(armed)})
            self._client.publish(TOPIC_CTRL_ARM, payload, qos=1, retain=True)
