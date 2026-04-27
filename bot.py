# -*- coding: utf-8 -*-
# Point d'entrée du bot Telegram d'alarme IoT.
# Lance le pont MQTT et relaie les changements de niveau aux abonnés Telegram.

import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

import commands
from config import TELEGRAM_TOKEN, LEVEL_LABELS
from mqtt_bridge import AlarmBridge
from responses import handle_response

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("alarm-bot")


# ── Texte libre ────────────────────────────────────────────────

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    await update.message.reply_text(handle_response(update.message.text))


async def error_handler(update, context):
    log.error("Update %s a déclenché une erreur : %s", update, context.error)


# ── Notifications de changement de niveau ──────────────────────

def make_level_change_handler(application):
    async def on_level_change(prev, new, snapshot):
        # On ne notifie qu'à l'escalade (0→1, 0→2, 1→2).
        if new <= prev:
            return
        # Notifier uniquement quand le système est explicitement armé.
        if snapshot.get("armed") is not True:
            return
        text = "🚨 Niveau d'alarme : %s\n" % LEVEL_LABELS.get(new, str(new))
        if snapshot.get("motion"):
            text += "• Mouvement détecté\n"
        if snapshot.get("sound"):
            text += "• Bruit détecté\n"
        if snapshot.get("accel"):
            text += "• Choc / vibration détectés\n"

        for chat_id in commands.get_subscribers():
            try:
                await application.bot.send_message(chat_id=chat_id, text=text)
            except Exception as exc:
                log.warning("Échec envoi à %s : %s", chat_id, exc)

    return on_level_change


def make_arm_change_handler(application):
    async def on_arm_change(armed, snapshot):
        text = "🔒 Alarme ARMÉE" if armed else "🔓 Alarme DÉSARMÉE"
        for chat_id in commands.get_subscribers():
            try:
                await application.bot.send_message(chat_id=chat_id, text=text)
            except Exception as exc:
                log.warning("Échec envoi à %s : %s", chat_id, exc)

    return on_arm_change


# ── Hooks de cycle de vie ──────────────────────────────────────

async def post_init(application: Application):
    bridge: AlarmBridge = application.bot_data["bridge"]
    bridge.set_loop(asyncio.get_running_loop())
    bridge.on_level_change = make_level_change_handler(application)
    bridge.on_arm_change = make_arm_change_handler(application)
    bridge.start()
    log.info("Pont MQTT démarré")


async def post_shutdown(application: Application):
    bridge: AlarmBridge = application.bot_data["bridge"]
    bridge.stop()
    log.info("Pont MQTT arrêté")


# ── Entrée ─────────────────────────────────────────────────────

def main():
    bridge = AlarmBridge()

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.bot_data["bridge"] = bridge

    app.add_handler(CommandHandler("start",       commands.start))
    app.add_handler(CommandHandler("help",        commands.help_command))
    app.add_handler(CommandHandler("status",      commands.status))
    app.add_handler(CommandHandler("mute",        commands.mute))
    app.add_handler(CommandHandler("reset",       commands.reset))
    app.add_handler(CommandHandler("arm",         commands.arm))
    app.add_handler(CommandHandler("disarm",      commands.disarm))
    app.add_handler(CommandHandler("subscribe",   commands.subscribe))
    app.add_handler(CommandHandler("unsubscribe", commands.unsubscribe))
    app.add_handler(CallbackQueryHandler(commands.button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)

    log.info("Bot Telegram démarré")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
