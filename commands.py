# -*- coding: utf-8 -*-
# Handlers Telegram pour le bot d'alarme IoT.

import json
import os
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext

from config import LEVEL_LABELS, SUBSCRIBERS_FILE


# ── Persistance des abonnés ────────────────────────────────────

def _load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            return set(json.load(f).get("chat_ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_subscribers(chat_ids):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump({"chat_ids": sorted(chat_ids)}, f, indent=2)


def get_subscribers():
    return _load_subscribers()


# ── Formatage ──────────────────────────────────────────────────

def _format_timestamp(ts):
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S")
        except (ValueError, OSError):
            return str(ts)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts).strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            return ts
    return str(ts)


def _format_state(state):
    armed = state.get("armed")
    if armed is True:
        armed_line = "🔒 ARMÉE"
    elif armed is False:
        armed_line = "🔓 DÉSARMÉE"
    else:
        armed_line = "❔ inconnu"
    lines = [
        "Système          : " + armed_line,
        "État : " + LEVEL_LABELS.get(state["level"], "?"),
        "• Mouvement       : " + ("🔴" if state["motion"] else "🟢"),
        "• Bruit           : " + ("🔴" if state["sound"]  else "🟢"),
        "• Accéléromètre   : " + ("🔴" if state["accel"]  else "🟢"),
    ]
    if state.get("distance_cm") is not None:
        lines.append("• Distance        : %s cm" % state["distance_cm"])
    if state.get("sound_value") is not None:
        lines.append("• Niveau sonore   : %s" % state["sound_value"])
    if state.get("last_update"):
        lines.append("_Mis à jour : %s_" % _format_timestamp(state["last_update"]))
    return "\n".join(lines)


def _menu_markup():
    keyboard = [
        [
            InlineKeyboardButton("🔍 Statut",          callback_data="status"),
            InlineKeyboardButton("🔕 Couper sonnerie", callback_data="mute"),
        ],
        [
            InlineKeyboardButton("🔒 Armer",           callback_data="arm"),
            InlineKeyboardButton("🔓 Désarmer",        callback_data="disarm"),
        ],
        [
            InlineKeyboardButton("🔄 Réinitialiser",   callback_data="reset"),
            InlineKeyboardButton("🔔 S'abonner",       callback_data="subscribe"),
        ],
        [
            InlineKeyboardButton("🚫 Se désabonner",   callback_data="unsubscribe"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ── Commandes ──────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bienvenue dans le bot d'alarme IoT.\n"
        "Choisissez une action :",
        reply_markup=_menu_markup(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commandes disponibles :\n"
        "/start        — menu principal\n"
        "/status       — état actuel des capteurs\n"
        "/arm          — armer l'alarme\n"
        "/disarm       — désarmer l'alarme\n"
        "/mute         — couper la sonnerie\n"
        "/reset        — réinitialiser les alarmes\n"
        "/subscribe    — recevoir les notifications d'alerte\n"
        "/unsubscribe  — arrêter les notifications\n"
        "/help         — afficher cette aide"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bridge = context.bot_data["bridge"]
    if not bridge.is_connected():
        await update.message.reply_text("⚠️ MQTT non connecté.")
        return
    await update.message.reply_text(
        _format_state(bridge.get_state()), parse_mode="Markdown"
    )


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bridge = context.bot_data["bridge"]
    bridge.buzzer_off()
    await update.message.reply_text("🔕 Sonnerie coupée.")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bridge = context.bot_data["bridge"]
    bridge.reset()
    await update.message.reply_text("🔄 Alarmes réinitialisées.")


async def arm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bridge = context.bot_data["bridge"]
    bridge.set_armed(True)
    await update.message.reply_text("🔒 Demande d'armement envoyée.")


async def disarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bridge = context.bot_data["bridge"]
    bridge.set_armed(False)
    await update.message.reply_text("🔓 Demande de désarmement envoyée.")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = _load_subscribers()
    if chat_id in subs:
        await update.message.reply_text("Vous êtes déjà abonné aux alertes.")
        return
    subs.add(chat_id)
    _save_subscribers(subs)
    await update.message.reply_text("🔔 Abonné aux alertes.")


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = _load_subscribers()
    if chat_id not in subs:
        await update.message.reply_text("Vous n'étiez pas abonné.")
        return
    subs.discard(chat_id)
    _save_subscribers(subs)
    await update.message.reply_text("🔕 Désabonné des alertes.")


# ── Boutons inline ─────────────────────────────────────────────

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    bridge = context.bot_data["bridge"]
    chat_id = update.effective_chat.id
    data = query.data

    if data == "status":
        if bridge.is_connected():
            await query.message.reply_text(
                _format_state(bridge.get_state()), parse_mode="Markdown"
            )
        else:
            await query.message.reply_text("⚠️ MQTT non connecté.")

    elif data == "mute":
        bridge.buzzer_off()
        await query.message.reply_text("🔕 Sonnerie coupée.")

    elif data == "reset":
        bridge.reset()
        await query.message.reply_text("🔄 Alarmes réinitialisées.")

    elif data == "arm":
        bridge.set_armed(True)
        await query.message.reply_text("🔒 Demande d'armement envoyée.")

    elif data == "disarm":
        bridge.set_armed(False)
        await query.message.reply_text("🔓 Demande de désarmement envoyée.")

    elif data == "subscribe":
        subs = _load_subscribers()
        if chat_id in subs:
            await query.message.reply_text("Déjà abonné.")
        else:
            subs.add(chat_id)
            _save_subscribers(subs)
            await query.message.reply_text("🔔 Abonné aux alertes.")

    elif data == "unsubscribe":
        subs = _load_subscribers()
        if chat_id not in subs:
            await query.message.reply_text("Pas abonné.")
        else:
            subs.discard(chat_id)
            _save_subscribers(subs)
            await query.message.reply_text("🔕 Désabonné des alertes.")
