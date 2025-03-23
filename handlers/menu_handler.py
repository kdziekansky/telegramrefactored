# handlers/menu_handler.py
"""
Moduł obsługujący menu bota
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CHAT_MODES, AVAILABLE_LANGUAGES, AVAILABLE_MODELS, CREDIT_COSTS, DEFAULT_MODEL, BOT_NAME
from utils.translations import get_text
from utils.user_utils import get_user_language, mark_chat_initialized
from database.credits_client import get_user_credits
from database.supabase_client import update_user_language, create_new_conversation
from utils.menu import update_menu, store_menu_state, get_navigation_path

logger = logging.getLogger(__name__)

# ==================== GŁÓWNE FUNKCJE MENU ====================

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla główne menu bota z przyciskami inline
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Przygotuj tekst powitalny
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    # Utwórz klawiaturę menu
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
    
    # Wyślij menu
    message = await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz ID wiadomości menu i stan menu
    store_menu_state(context, user_id, 'main', message.message_id)

# ==================== FUNKCJE OBSŁUGUJĄCE POSZCZEGÓLNE SEKCJE MENU ====================

async def handle_chat_modes_section(update, context, navigation_path=""):
    """Obsługuje sekcję trybów czatu"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    message_text = ""
    if not navigation_path:
        navigation_path = get_navigation_path('chat_modes', language)
    
    message_text = f"*{navigation_path}*\n\n"
    message_text += get_text("select_chat_mode", language)
    
    # Przygotuj klawiaturę dla trybów czatu
    keyboard = []
    for mode_id, mode_info in CHAT_MODES.items():
        # Pobierz przetłumaczoną nazwę trybu
        mode_name = get_text(f"chat_mode_{mode_id}", language, default=mode_info['name'])
        
        # Dodaj oznaczenie kosztu
        if mode_info['credit_cost'] == 1:
            cost_indicator = "🟢"  # Zielony dla ekonomicznych
        elif mode_info['credit_cost'] <= 3:
            cost_indicator = "🟠"  # Pomarańczowy dla standardowych
        else:
            cost_indicator = "🔴"  # Czerwony dla drogich
        
        # Dodaj gwiazdkę dla premium
        premium_marker = "⭐ " if mode_info['credit_cost'] >= 3 else ""
        
        keyboard.append([
            InlineKeyboardButton(
                f"{premium_marker}{mode_name} {cost_indicator} {mode_info['credit_cost']} kr.", 
                callback_data=f"mode_{mode_id}"
            )
        ])
    
    # Pasek szybkiego dostępu
    keyboard.append([
        InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
        InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
        InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
    ])
    
    # Przycisk powrotu
    keyboard.append([
        InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu(
        query, 
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'chat_modes')
    
    return result

async def handle_credits_section(update, context, navigation_path=""):
    """Obsługuje sekcję kredytów"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    if not navigation_path:
        navigation_path = get_navigation_path('credits', language)
    
    message_text = f"*{navigation_path}*\n\n"
    
    credits = get_user_credits(user_id)
    
    message_text += f"*Stan kredytów*\n\n"
    message_text += f"Dostępne kredyty: *{credits}*\n\n"
    
    # Dodaj informację o kosztach operacji
    message_text += f"*Koszty operacji:*\n"
    message_text += f"▪️ Wiadomość standardowa (GPT-3.5): 1 kredyt\n"
    message_text += f"▪️ Wiadomość premium (GPT-4o): 3 kredyty\n"
    message_text += f"▪️ Wiadomość ekspercka (GPT-4): 5 kredytów\n"
    message_text += f"▪️ Generowanie obrazu: 10-15 kredytów\n"
    message_text += f"▪️ Analiza dokumentu: 5 kredytów\n"
    message_text += f"▪️ Analiza zdjęcia: 8 kredytów\n\n"
    
    # Stwórz przyciski
    keyboard = [
        [InlineKeyboardButton("💳 Kup kredyty", callback_data="menu_credits_buy")],
        [
            InlineKeyboardButton("💰 Metody płatności", callback_data="payment_command"),
            InlineKeyboardButton("🔄 Subskrypcje", callback_data="subscription_command")
        ],
        [InlineKeyboardButton("📜 Historia transakcji", callback_data="transactions_command")],
        
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat")
        ],
        
        [InlineKeyboardButton("⬅️ Powrót", callback_data="menu_back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'credits')
    
    return result

async def handle_history_section(update, context, navigation_path=""):
    """Obsługuje sekcję historii"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    if not navigation_path:
        navigation_path = get_navigation_path('history', language)
    
    message_text = f"*{navigation_path}*\n\n"
    message_text += get_text("history_options", language, default="Zarządzaj swoją historią rozmów") + "\n\n" + get_text("export_info", language, default="Aby wyeksportować konwersację, użyj komendy /export")
    
    # Przygotuj klawiaturę
    keyboard = [
        [InlineKeyboardButton(get_text("new_chat", language), callback_data="history_new")],
        [InlineKeyboardButton(get_text("view_history", language), callback_data="history_view")],
        [InlineKeyboardButton(get_text("delete_history", language), callback_data="history_delete")],
        
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ],
        
        # Przycisk "Wstecz"
        [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'history')
    
    return result

async def handle_settings_section(update, context, navigation_path=""):
    """Obsługuje sekcję ustawień"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    if not navigation_path:
        navigation_path = get_navigation_path('settings', language)
    
    message_text = f"*{navigation_path}*\n\n"
    message_text += get_text("settings_options", language, default="Wybierz opcję ustawień:")
    
    # Przygotuj klawiaturę
    keyboard = [
        [InlineKeyboardButton(get_text("settings_model", language), callback_data="settings_model")],
        [InlineKeyboardButton(get_text("settings_language", language), callback_data="settings_language")],
        [InlineKeyboardButton(get_text("settings_name", language), callback_data="settings_name")],
        
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ],
        
        # Przycisk "Wstecz"
        [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'settings')
    
    return result

async def handle_help_section(update, context, navigation_path=""):
    """Obsługuje sekcję pomocy"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    if not navigation_path:
        navigation_path = get_navigation_path('help', language)
    
    message_text = f"*{navigation_path}*\n\n"
    
    # Pobierz tekst pomocy
    help_text = get_text("help_text", language)
    message_text += help_text
    
    # Dodaj sekcję ze skrótami komend
    message_text += "\n\n● *Skróty Komend* ●\n"
    message_text += "▪️ /start - Rozpocznij bota\n"
    message_text += "▪️ /menu - Otwórz menu główne\n"
    message_text += "▪️ /credits - Sprawdź kredyty\n"
    message_text += "▪️ /buy - Kup kredyty\n" 
    message_text += "▪️ /mode - Wybierz tryb czatu\n"
    message_text += "▪️ /image - Generuj obraz\n"
    message_text += "▪️ /help - Wyświetl pomoc\n"
    message_text += "▪️ /status - Sprawdź status\n"
    
    keyboard = [
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ],
        [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'help')
    
    return result

async def handle_image_section(update, context, navigation_path=""):
    """Obsługuje sekcję generowania obrazów"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    if not navigation_path:
        navigation_path = get_navigation_path('image', language)
    
    message_text = f"*{navigation_path}*\n\n"
    message_text += get_text("image_usage", language, default="Aby wygenerować obraz, użyj komendy /image [opis obrazu]")
    
    # Przygotuj instrukcje i przykłady
    message_text += "\n\n*Przykłady:*\n"
    message_text += "▪️ /image zachód słońca nad górami z jeziorem\n"
    message_text += "▪️ /image portret kobiety w stylu renesansowym\n"
    message_text += "▪️ /image futurystyczne miasto nocą\n\n"
    message_text += "*Wskazówki:*\n"
    message_text += "▪️ Im bardziej szczegółowy opis, tym lepszy efekt\n"
    message_text += "▪️ Możesz określić styl artystyczny (np. olejny, akwarela)\n"
    message_text += "▪️ Dodaj informacje o oświetleniu, kolorach i kompozycji"
    
    keyboard = [
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ],
        [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'image')
    
    return result

# ==================== FUNKCJE OBSŁUGUJĄCE PRZYCISKI POWROTU ====================

async def handle_back_to_main(update, context):
    """Obsługuje powrót do głównego menu"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz tekst powitalny
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    # Utwórz klawiaturę menu
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
        result = await update_menu(
            query,
            welcome_text,
            reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Zapisz stan menu
        store_menu_state(context, user_id, 'main')
        
        return result
    except Exception as e:
        logger.error(f"Błąd przy powrocie do menu głównego: {e}")
        
        # W przypadku błędu spróbuj wysłać nową wiadomość
        await query.message.delete()
        
        message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Zapisz ID nowej wiadomości menu
        store_menu_state(context, user_id, 'main', message.message_id)
        
        return True

# ==================== FUNKCJE POMOCNICZE DO POSZCZEGÓLNYCH OPERACJI ====================

async def handle_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje wybór modelu AI"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    message_text = f"*{get_navigation_path('settings', language)} > {get_text('settings_choose_model', language, default='Wybór modelu')}*\n\n"
    message_text += get_text("settings_choose_model", language, default="Wybierz model AI, którego chcesz używać:")
    
    # Stwórz przyciski dla dostępnych modeli
    keyboard = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        # Dodaj informację o koszcie kredytów
        credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"{model_name} ({credit_cost} {get_text('credits_per_message', language, default='kredytów/wiadomość')})", 
                callback_data=f"model_{model_id}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(get_text("back", language, default="Powrót"), callback_data="menu_section_settings")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'model_selection')
    
    return result

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje wybór języka"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    message_text = f"*{get_navigation_path('settings', language)} > {get_text('settings_choose_language', language, default='Wybór języka')}*\n\n"
    message_text += get_text("settings_choose_language", language, default="Wybierz język:")
    
    # Stwórz przyciski dla dostępnych języków
    keyboard = []
    for lang_code, lang_name in AVAILABLE_LANGUAGES.items():
        keyboard.append([
            InlineKeyboardButton(
                lang_name, 
                callback_data=f"start_lang_{lang_code}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'language_selection')
    
    return result

async def handle_history_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje callbacki związane z historią rozmów"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    logger.debug(f"Historia callback: {query.data}")
    
    if query.data == "history_view":
        from database.supabase_client import get_active_conversation, get_conversation_history
        
        conversation = get_active_conversation(user_id)
        
        if not conversation:
            message_text = get_text("history_no_conversation", language, default="Brak aktywnej konwersacji.")
            keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update_menu(query, message_text, reply_markup)
            return True
            
        # Pobierz historię konwersacji
        history = get_conversation_history(conversation['id'])
        
        if not history:
            message_text = get_text("history_empty", language, default="Historia jest pusta.")
            keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update_menu(query, message_text, reply_markup)
            return True
        
        # Przygotuj tekst z historią
        message_text = f"*{get_text('history_title', language, default='Historia konwersacji')}*\n\n"
        
        for i, msg in enumerate(history[-10:]):  # Ostatnie 10 wiadomości
            sender = get_text("history_user", language, default="Użytkownik") if msg.get('is_from_user') else get_text("history_bot", language, default="Bot")
            
            # Skróć treść wiadomości, jeśli jest zbyt długa
            content = msg.get('content', '')
            if content and len(content) > 100:
                content = content[:97] + "..."
                
            # Usuń znaki formatowania Markdown
            content = content.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
            
            message_text += f"{i+1}. *{sender}*: {content}\n\n"
        
        # Dodaj przycisk do powrotu
        keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await update_menu(
                query,
                message_text,
                reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Błąd w edit_message_text: {e}")
            # Fallback bez formatowania
            await update_menu(
                query,
                message_text.replace("*", ""),
                reply_markup
            )
        
        return True
    
    elif query.data == "history_new":
        try:
            # Utwórz nową konwersację
            conversation = create_new_conversation(user_id)
            mark_chat_initialized(context, user_id)
            
            message_text = "✅ Utworzono nową konwersację."
            keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update_menu(
                query,
                message_text,
                reply_markup
            )
        except Exception as e:
            logger.error(f"Błąd w history_new: {e}")
            
            await update_menu(
                query,
                "Wystąpił błąd podczas tworzenia nowej konwersacji.",
                InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]])
            )
                
        return True
    
    elif query.data == "history_delete":
        try:
            # Pytanie o potwierdzenie
            message_text = "Czy na pewno chcesz usunąć historię? Tej operacji nie można cofnąć."
            keyboard = [
                [
                    InlineKeyboardButton("✅ Tak", callback_data="history_confirm_delete"),
                    InlineKeyboardButton("❌ Nie", callback_data="menu_section_history")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update_menu(
                query,
                message_text,
                reply_markup
            )
        except Exception as e:
            logger.error(f"Błąd w history_delete: {e}")
            
            await update_menu(
                query,
                "Wystąpił błąd.",
                InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]])
            )
                
        return True
    
    elif query.data == "history_confirm_delete":
        try:
            # Usuń historię (tworząc nową konwersację)
            conversation = create_new_conversation(user_id)
            
            # Aktualizuj wiadomość
            message_text = "✅ Historia została pomyślnie usunięta."
            keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update_menu(
                query,
                message_text,
                reply_markup
            )
        except Exception as e:
            logger.error(f"Błąd w history_confirm_delete: {e}")
            
            await update_menu(
                query,
                "Wystąpił błąd podczas usuwania historii.",
                InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]])
            )
                
        return True
    
    return False