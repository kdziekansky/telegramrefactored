# handlers/callback_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from utils.user_utils import get_user_language

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa callbacków, które nie zostały obsłużone przez centralny router
    Ta funkcja jest używana tylko jako fallback dla zgodności ze starszym kodem
    """
    # Przekieruj do centralnego routera
    from handlers.callback_router import route_callback
    return await route_callback(update, context)

async def handle_buy_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy handler dla zgodności z poprzednim kodem"""
    from handlers.credit_handler import buy_command
    
    # Utwórz obiekt symulujący standardowe wywołanie komendy
    query = update.callback_query
    fake_update = type('obj', (object,), {
        'effective_user': query.from_user,
        'message': query.message,
        'effective_chat': query.message.chat
    })
    
    # Usuń oryginalną wiadomość
    await query.message.delete()
    
    # Wywołaj komendę zakupu
    await buy_command(fake_update, context)
    return True

async def handle_unknown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy handler dla nieznanych callbacków - przekieruj do centralnego routera"""
    from handlers.callback_router import route_callback
    return await route_callback(update, context)