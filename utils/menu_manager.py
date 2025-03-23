# utils/menu_manager.py
"""
Centralny moduł do zarządzania systemem menu bota
"""
import logging
from telegram import InlineKeyboardMarkup
from utils.menu_utils import update_menu, menu_state
from utils.translations import get_text
from utils.user_utils import get_user_language

logger = logging.getLogger(__name__)

def store_menu_state(context, user_id, state, message_id=None):
    """
    Zapisuje stan menu dla użytkownika
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        state: Stan menu (np. 'main', 'chat_modes', 'credits', etc.)
        message_id: ID wiadomości z menu (opcjonalnie)
    """
    menu_state.set_state(user_id, state)
    if message_id:
        menu_state.set_message_id(user_id, message_id)
    menu_state.save_to_context(context, user_id)
    logger.debug(f"Zapisano stan menu '{state}' dla użytkownika {user_id}")

def get_menu_state(context, user_id):
    """
    Pobiera stan menu dla użytkownika
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        
    Returns:
        str: Stan menu
    """
    menu_state.load_from_context(context, user_id)
    return menu_state.get_state(user_id)

def get_menu_message_id(context, user_id):
    """
    Pobiera ID wiadomości menu dla użytkownika
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        
    Returns:
        int: ID wiadomości menu
    """
    menu_state.load_from_context(context, user_id)
    return menu_state.get_message_id(user_id)

async def update_menu_message(query, text, keyboard, parse_mode=None):
    """
    Aktualizuje wiadomość menu
    
    Args:
        query: Obiekt callback_query
        text: Tekst do wyświetlenia
        keyboard: Klawiatura z przyciskami
        parse_mode: Tryb formatowania (opcjonalnie)
        
    Returns:
        bool: Czy aktualizacja się powiodła
    """
    return await update_menu(query, text, keyboard, parse_mode)

async def create_new_menu_message(context, chat_id, text, keyboard, parse_mode=None):
    """
    Tworzy nową wiadomość menu
    
    Args:
        context: Kontekst bota
        chat_id: ID czatu
        text: Tekst do wyświetlenia
        keyboard: Klawiatura z przyciskami
        parse_mode: Tryb formatowania (opcjonalnie)
        
    Returns:
        telegram.Message: Utworzona wiadomość
    """
    try:
        return await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode=parse_mode
        )
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu nowej wiadomości menu: {e}")
        try:
            # Fallback bez formatowania
            return await context.bot.send_message(
                chat_id=chat_id,
                text=text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", ""),
                reply_markup=keyboard
            )
        except Exception as e2:
            logger.error(f"Drugi błąd przy tworzeniu wiadomości menu: {e2}")
            return None
            
def get_navigation_path(state, language):
    """
    Generuje tekst paska nawigacyjnego
    
    Args:
        state: Stan menu (np. 'main', 'chat_modes', 'credits', etc.)
        language: Kod języka
        
    Returns:
        str: Tekst paska nawigacyjnego
    """
    # Mapowanie stanów menu na ścieżki nawigacji
    navigation_map = {
        'main': get_text("main_menu", language, default="Menu główne"),
        'chat_modes': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_chat_mode', language, default='Tryb czatu')}",
        'credits': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_credits', language, default='Kredyty')}",
        'settings': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_settings', language, default='Ustawienia')}",
        'history': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_dialog_history', language, default='Historia')}",
        'help': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_help', language, default='Pomoc')}",
        'image': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('image_generate', language, default='Generowanie obrazu')}"
    }
    
    return navigation_map.get(state, get_text("main_menu", language, default="Menu główne"))