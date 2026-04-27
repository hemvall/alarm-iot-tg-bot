def handle_response(text: str) -> str:
    text = text.lower()

    if any(w in text for w in ("hello", "hi", "hey", "bonjour", "salut", "yo")):
        return "👋 Salut ! Tapez /help pour voir les commandes."

    if "help" in text or "aide" in text:
        return (
            "Commandes disponibles :\n"
            "/start, /status, /mute, /reset, /subscribe, /unsubscribe, /help"
        )

    if "status" in text or "état" in text or "etat" in text or "capteur" in text:
        return "Tapez /status pour voir l'état des capteurs."

    if "mute" in text or "buzzer" in text or "sonnerie" in text or "silence" in text:
        return "Tapez /mute pour couper la sonnerie."

    if "reset" in text or "réinit" in text or "reinit" in text:
        return "Tapez /reset pour réinitialiser les alarmes."

    if "abonn" in text or "subscribe" in text or "notif" in text:
        return "Tapez /subscribe pour recevoir les alertes, /unsubscribe pour arrêter."

    return "Je ne comprends pas. Tapez /help pour voir les commandes disponibles."
