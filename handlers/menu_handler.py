# handlers/menu_handler.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CHAT_MODES, AVAILABLE_LANGUAGES, AVAILABLE_MODELS, BOT_NAME
from utils.translations import get_text
from utils.user_utils import get_user_language, mark_chat_initialized
from database.supabase_client import update_user_language, create_new_conversation
from utils.menu import update_menu, store_menu_state, get_navigation_path

logger = logging.getLogger(__name__)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main menu with inline buttons"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    keyboard = [
        [
            InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes"),
            InlineKeyboardButton(get_text("image_generate", language), callback_data="menu_image_generate")
        ],
        [
            InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits"),
            InlineKeyboardButton(get_text("menu_dialog_history", language), callback_data="menu_section_history")
        ],
        [
            InlineKeyboardButton(get_text("menu_settings", language), callback_data="menu_section_settings"),
            InlineKeyboardButton(get_text("menu_help", language), callback_data="menu_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'main', message.message_id)

async def _create_section_menu(query, context, section_name, text_key, buttons, quick_access=True):
    """Reusable function to create section menus with consistent styling and navigation"""
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    nav_path = get_navigation_path(section_name, language)
    message_text = f"*{nav_path}*\n\n{get_text(text_key, language)}"
    
    # Add quick access buttons if requested
    if quick_access:
        buttons.append([
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ])
    
    # Always add back button
    buttons.append([InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, section_name)
    return result

async def handle_chat_modes_section(update, context, navigation_path=""):
    """Chat modes section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    buttons = []
    for mode_id, mode_info in CHAT_MODES.items():
        mode_name = get_text(f"chat_mode_{mode_id}", language, default=mode_info['name'])
        
        # Add cost indicators
        cost_indicator = "🟢" if mode_info['credit_cost'] == 1 else "🟠" if mode_info['credit_cost'] <= 3 else "🔴"
        premium_marker = "⭐ " if mode_info['credit_cost'] >= 3 else ""
        
        buttons.append([
            InlineKeyboardButton(
                f"{premium_marker}{mode_name} {cost_indicator} {mode_info['credit_cost']} kr.", 
                callback_data=f"mode_{mode_id}"
            )
        ])
    
    return await _create_section_menu(
        query, context, 'chat_modes', "select_chat_mode", buttons
    )

async def handle_credits_section(update, context, navigation_path=""):
    """Credits section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    credits = get_user_credits(user_id)
    
    message_text = f"*{navigation_path or get_navigation_path('credits', language)}*\n\n"
    message_text += f"*Stan kredytów*\n\nDostępne kredyty: *{credits}*\n\n*Koszty operacji:*\n"
    message_text += f"▪️ Wiadomość standardowa (GPT-3.5): 1 kredyt\n"
    message_text += f"▪️ Wiadomość premium (GPT-4o): 3 kredyty\n"
    message_text += f"▪️ Wiadomość ekspercka (GPT-4): 5 kredytów\n"
    message_text += f"▪️ Generowanie obrazu: 10-15 kredytów\n"
    message_text += f"▪️ Analiza dokumentu: 5 kredytów\n"
    message_text += f"▪️ Analiza zdjęcia: 8 kredytów\n\n"
    
    buttons = [
        [InlineKeyboardButton("💳 Kup kredyty", callback_data="menu_credits_buy")],
        [
            InlineKeyboardButton("💰 Metody płatności", callback_data="payment_command"),
            InlineKeyboardButton("🔄 Subskrypcje", callback_data="subscription_command")
        ],
        [InlineKeyboardButton("📜 Historia transakcji", callback_data="transactions_command")],
        # Quick access buttons
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language), callback_data="quick_last_chat")
        ],
        [InlineKeyboardButton("⬅️ Powrót", callback_data="menu_back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'credits')
    return result

async def handle_history_section(update, context, navigation_path=""):
    """History section handler"""
    buttons = [
        [InlineKeyboardButton(get_text("new_chat", language), callback_data="history_new")],
        [InlineKeyboardButton(get_text("view_history", language), callback_data="history_view")],
        [InlineKeyboardButton(get_text("delete_history", language), callback_data="history_delete")]
    ]
    
    return await _create_section_menu(
        update.callback_query, context, 'history', 
        "history_options", buttons
    )

async def handle_settings_section(update, context, navigation_path=""):
    """Settings section handler"""
    buttons = [
        [InlineKeyboardButton(get_text("settings_model", language), callback_data="settings_model")],
        [InlineKeyboardButton(get_text("settings_language", language), callback_data="settings_language")],
        [InlineKeyboardButton(get_text("settings_name", language), callback_data="settings_name")]
    ]
    
    return await _create_section_menu(
        update.callback_query, context, 'settings', 
        "settings_options", buttons
    )

async def handle_help_section(update, context, navigation_path=""):
    """Help section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    message_text = f"*{navigation_path or get_navigation_path('help', language)}*\n\n"
    message_text += get_text("help_text", language)
    
    # Add command shortcuts
    message_text += "\n\n● *Skróty Komend* ●\n"
    commands = [
        "/start - Rozpocznij bota", "/menu - Otwórz menu główne", 
        "/credits - Sprawdź kredyty", "/buy - Kup kredyty",
        "/mode - Wybierz tryb czatu", "/image - Generuj obraz",
        "/help - Wyświetl pomoc", "/status - Sprawdź status"
    ]
    message_text += "\n".join([f"▪️ {cmd}" for cmd in commands])
    
    buttons = [[
        InlineKeyboardButton("🆕 " + get_text("new_chat", language), callback_data="quick_new_chat"),
        InlineKeyboardButton("💬 " + get_text("last_chat", language), callback_data="quick_last_chat"),
        InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language), callback_data="quick_buy_credits")
    ], [
        InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")
    ]]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'help')
    return result

async def handle_image_section(update, context, navigation_path=""):
    """Image generation section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    text_key = "image_usage"
    message_text = f"*{navigation_path or get_navigation_path('image', language)}*\n\n"
    message_text += get_text(text_key, language, default="Aby wygenerować obraz, użyj komendy /image [opis obrazu]")
    
    # Add examples and tips
    message_text += "\n\n*Przykłady:*\n"
    message_text += "▪️ /image zachód słońca nad górami z jeziorem\n"
    message_text += "▪️ /image portret kobiety w stylu renesansowym\n"
    message_text += "▪️ /image futurystyczne miasto nocą\n\n"
    message_text += "*Wskazówki:*\n"
    message_text += "▪️ Im bardziej szczegółowy opis, tym lepszy efekt\n"
    message_text += "▪️ Możesz określić styl artystyczny (np. olejny, akwarela)\n"
    message_text += "▪️ Dodaj informacje o oświetleniu, kolorach i kompozycji"
    
    buttons = [[
        InlineKeyboardButton("🆕 " + get_text("new_chat", language), callback_data="quick_new_chat"),
        InlineKeyboardButton("💬 " + get_text("last_chat", language), callback_data="quick_last_chat"),
        InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language), callback_data="quick_buy_credits")
    ], [
        InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")
    ]]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'image')
    return result

async def handle_back_to_main(update, context):
    """Back to main menu handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    keyboard = [
        [
            InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes"),
            InlineKeyboardButton(get_text("image_generate", language), callback_data="menu_image_generate")
        ],
        [
            InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits"),
            InlineKeyboardButton(get_text("menu_dialog_history", language), callback_data="menu_section_history")
        ],
        [
            InlineKeyboardButton(get_text("menu_settings", language), callback_data="menu_section_settings"),
            InlineKeyboardButton(get_text("menu_help", language), callback_data="menu_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        result = await update_menu(query, welcome_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
        store_menu_state(context, user_id, 'main')
        return result
    except Exception as e:
        logger.error(f"Error returning to main menu: {e}")
        await query.message.delete()
        message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        store_menu_state(context, user_id, 'main', message.message_id)
        return True

async def handle_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Model selection handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    message_text = f"*{get_navigation_path('settings', language)} > {get_text('settings_choose_model', language)}*\n\n"
    message_text += get_text("settings_choose_model", language, default="Wybierz model AI:")
    
    buttons = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
        buttons.append([
            InlineKeyboardButton(
                f"{model_name} ({credit_cost} {get_text('credits_per_message', language)})", 
                callback_data=f"model_{model_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'model_selection')
    return result

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Language selection handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    message_text = f"*{get_navigation_path('settings', language)} > {get_text('settings_choose_language', language)}*\n\n"
    message_text += get_text("settings_choose_language", language, default="Wybierz język:")
    
    buttons = []
    for lang_code, lang_name in AVAILABLE_LANGUAGES.items():
        buttons.append([InlineKeyboardButton(lang_name, callback_data=f"start_lang_{lang_code}")])
    
    buttons.append([InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'language_selection')
    return result

async def handle_history_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """History-related callbacks handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    if query.data == "history_view":
        from database.supabase_client import get_active_conversation, get_conversation_history
        conversation = get_active_conversation(user_id)
        
        if not conversation:
            message_text = get_text("history_no_conversation", language, default="Brak aktywnej konwersacji.")
            await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            return True
            
        history = get_conversation_history(conversation['id'])
        
        if not history:
            message_text = get_text("history_empty", language, default="Historia jest pusta.")
            await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            return True
        
        message_text = f"*{get_text('history_title', language, default='Historia konwersacji')}*\n\n"
        
        for i, msg in enumerate(history[-10:]):
            sender = get_text("history_user", language) if msg.get('is_from_user') else get_text("history_bot", language)
            content = msg.get('content', '')
            if content and len(content) > 100:
                content = content[:97] + "..."
            content = content.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
            message_text += f"{i+1}. *{sender}*: {content}\n\n"
        
        try:
            await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update_menu(query, message_text.replace("*", ""), InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
        
        return True
    
    elif query.data == "history_new":
        try:
            conversation = create_new_conversation(user_id)
            mark_chat_initialized(context, user_id)
            message_text = "✅ Utworzono nową konwersację."
            await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
        except Exception as e:
            logger.error(f"Error in history_new: {e}")
            await update_menu(query, "Wystąpił błąd podczas tworzenia nowej konwersacji.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
        return True
    
    elif query.data == "history_delete":
        message_text = "Czy na pewno chcesz usunąć historię? Tej operacji nie można cofnąć."
        keyboard = [
            [InlineKeyboardButton("✅ Tak", callback_data="history_confirm_delete"), 
             InlineKeyboardButton("❌ Nie", callback_data="menu_section_history")]
        ]
        await update_menu(query, message_text, InlineKeyboardMarkup(keyboard))
        return True
    
    elif query.data == "history_confirm_delete":
        try:
            conversation = create_new_conversation(user_id)
            message_text = "✅ Historia została pomyślnie usunięta."
            await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
        except Exception as e:
            logger.error(f"Error in history_confirm_delete: {e}")
            await update_menu(query, "Wystąpił błąd podczas usuwania historii.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
        return True
    
    return False

async def handle_settings_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings-related callbacks handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    if query.data == "settings_name":
        message_text = get_text("settings_change_name", language, default="Aby zmienić swoją nazwę, użyj komendy /setname [twoja_nazwa].")
        await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_settings")]]), parse_mode=ParseMode.MARKDOWN)
        return True
    
    return False