from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CHAT_MODES, AVAILABLE_LANGUAGES, AVAILABLE_MODELS, CREDIT_COSTS, DEFAULT_MODEL, BOT_NAME
from utils.translations import get_text
from database.supabase_client import get_message_status
from database.credits_client import get_user_credits, get_credit_packages
from utils.user_utils import get_user_language, mark_chat_initialized, is_chat_initialized
from utils.ui_elements import info_card, credit_status_bar, section_divider, feature_badge
from utils.message_formatter_enhanced import enhance_credits_display, enhance_help_message, format_mode_selection
from utils.visual_styles import style_message, create_header, create_section
from utils.tips import get_random_tip, should_show_tip
from utils.credit_warnings import get_low_credits_notification, get_credit_recommendation

# Import centralnego systemu menu
from utils.menu_manager import (
    store_menu_state,
    get_menu_state,
    get_menu_message_id,
    update_menu_message,
    get_navigation_path,
    create_new_menu_message
)

# ==================== FUNKCJE POMOCNICZE DO ZARZĄDZANIA DANYMI UŻYTKOWNIKA ====================

def get_user_current_mode(context, user_id):
    """Pobiera aktualny tryb czatu użytkownika"""
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            return user_data['current_mode']
    return "no_mode"

def get_user_current_model(context, user_id):
    """Pobiera aktualny model AI użytkownika"""
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_model' in user_data and user_data['current_model'] in AVAILABLE_MODELS:
            return user_data['current_model']
    return DEFAULT_MODEL  # Domyślny model

# ==================== FUNKCJE GENERUJĄCE UKŁADY MENU ====================

def create_main_menu_markup(language):
    """Tworzy klawiaturę dla głównego menu"""
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
        ],
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_chat_modes_markup(language):
    """Tworzy klawiaturę dla menu trybów czatu"""
    keyboard = []
    for mode_id, mode_info in CHAT_MODES.items():
        # Pobierz przetłumaczoną nazwę trybu
        mode_name = get_text(f"chat_mode_{mode_id}", language, default=mode_info['name'])
        # Pobierz przetłumaczony tekst dla kredytów
        credit_text = get_text("credit", language, default="kredyt")
        if mode_info['credit_cost'] != 1:
            credit_text = get_text("credits", language, default="kredytów")
        
        keyboard.append([
            InlineKeyboardButton(
                f"{mode_name} ({mode_info['credit_cost']} {credit_text})", 
                callback_data=f"mode_{mode_id}"
            )
        ])
    
    # Pasek szybkiego dostępu
    keyboard.append([
        InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
        InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
        InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
    ])
    
    # Dodaj przycisk powrotu w jednolitym miejscu
    keyboard.append([
        InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def create_credits_menu_markup(language):
    """Tworzy klawiaturę dla menu kredytów"""
    keyboard = [
        [InlineKeyboardButton(get_text("check_balance", language), callback_data="menu_credits_check")],
        [InlineKeyboardButton(get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
        
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat")
        ],
        
        # Przycisk "Wstecz"
        [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_settings_menu_markup(language):
    """Tworzy klawiaturę dla menu ustawień"""
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
    return InlineKeyboardMarkup(keyboard)

def create_history_menu_markup(language):
    """Tworzy klawiaturę dla menu historii"""
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
    return InlineKeyboardMarkup(keyboard)

def create_model_selection_markup(language):
    """Tworzy klawiaturę dla wyboru modelu AI"""
    keyboard = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        # Dodaj informację o koszcie kredytów
        credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"{model_name} ({credit_cost} {get_text('credits_per_message', language)})", 
                callback_data=f"model_{model_id}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def create_language_selection_markup(language):
    """Tworzy klawiaturę dla wyboru języka"""
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
    
    return InlineKeyboardMarkup(keyboard)

# ==================== FUNKCJE OBSŁUGUJĄCE POSZCZEGÓLNE SEKCJE MENU ====================

async def handle_chat_modes_section(update, context):
    """Obsługuje sekcję trybów czatu z ulepszoną prezentacją"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz ścieżkę nawigacyjną
    navigation_path = get_navigation_path('chat_modes', language)
    
    # Dodajemy pasek nawigacyjny do tekstu
    message_text = f"*{navigation_path}*\n\n"
    
    # Add styled header for chat modes section
    message_text += create_header("Tryby Konwersacji", "chat")
    message_text += get_text("select_chat_mode", language)
    
    # Add visual explanation of cost indicators
    message_text += "\n\n" + create_section("Oznaczenia Kosztów", 
        "🟢 1 kredyt - tryby ekonomiczne\n🟠 2-3 kredytów - tryby standardowe\n🔴 5+ kredytów - tryby premium")
    
    # Customized keyboard with cost indicators
    keyboard = []
    for mode_id, mode_info in CHAT_MODES.items():
        # Pobierz przetłumaczoną nazwę trybu
        mode_name = get_text(f"chat_mode_{mode_id}", language, default=mode_info['name'])
        
        # Add cost indicator emoji based on credit cost
        if mode_info['credit_cost'] == 1:
            cost_indicator = "🟢"  # Green for economy options
        elif mode_info['credit_cost'] <= 3:
            cost_indicator = "🟠"  # Orange for standard options
        else:
            cost_indicator = "🔴"  # Red for expensive options
        
        # Add premium star for premium modes
        if mode_info['credit_cost'] >= 3 and "gpt-4" in mode_info.get('model', ''):
            premium_marker = "⭐ "
        else:
            premium_marker = ""
        
        # Create button with visual indicators
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
    
    # Dodaj przycisk powrotu w jednolitym miejscu
    keyboard.append([
        InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Używamy centralnej funkcji update_menu_message
    result = await update_menu_message(
        query, 
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu używając centralnej funkcji
    store_menu_state(context, user_id, 'chat_modes')
    
    return result

async def handle_credits_section(update, context):
    """Obsługuje sekcję kredytów z ulepszoną wizualizacją"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz ścieżkę nawigacyjną
    navigation_path = get_navigation_path('credits', language)
    
    # Dodajemy pasek nawigacyjny do tekstu
    message_text = f"*{navigation_path}*\n\n"
    
    credits = get_user_credits(user_id)
    
    # Use enhanced credit display with status bar and visual indicators
    message_text += enhance_credits_display(credits, BOT_NAME)
    
    # Add a random tip about credits if appropriate
    if should_show_tip(user_id, context):
        tip = get_random_tip('credits')
        message_text += f"\n\n{section_divider('Porada')}\n💡 *Porada:* {tip}"
    
    # Check for low credits and add warning if needed
    low_credits_warning = get_low_credits_notification(credits)
    if low_credits_warning:
        message_text += f"\n\n{section_divider('Uwaga')}\n{low_credits_warning}"
    
    reply_markup = create_credits_menu_markup(language)
    
    # Używamy centralnej funkcji update_menu_message
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu używając centralnej funkcji
    store_menu_state(context, user_id, 'credits')
    
    return result

async def handle_history_section(update, context):
    """Obsługuje sekcję historii"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz ścieżkę nawigacyjną
    navigation_path = get_navigation_path('history', language)
    
    # Dodajemy pasek nawigacyjny do tekstu
    message_text = f"*{navigation_path}*\n\n"
    
    message_text += get_text("history_options", language) + "\n\n" + get_text("export_info", language, default="Aby wyeksportować konwersację, użyj komendy /export")
    reply_markup = create_history_menu_markup(language)
    
    # Używamy centralnej funkcji update_menu_message
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu używając centralnej funkcji
    store_menu_state(context, user_id, 'history')
    
    return result

async def handle_settings_section(update, context):
    """Obsługuje sekcję ustawień"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz ścieżkę nawigacyjną
    navigation_path = get_navigation_path('settings', language)
    
    # Dodajemy pasek nawigacyjny do tekstu
    message_text = f"*{navigation_path}*\n\n"
    
    message_text += get_text("settings_options", language)
    reply_markup = create_settings_menu_markup(language)
    
    # Używamy centralnej funkcji update_menu_message
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu używając centralnej funkcji
    store_menu_state(context, user_id, 'settings')
    
    return result

async def handle_help_section(update, context):
    """Obsługuje sekcję pomocy z ulepszoną wizualizacją"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz ścieżkę nawigacyjną
    navigation_path = get_navigation_path('help', language)
    
    # Dodajemy pasek nawigacyjny do tekstu
    message_text = f"*{navigation_path}*\n\n"
    
    # Get the base help text
    help_text = get_text("help_text", language)
    
    # Apply enhanced formatting
    message_text += enhance_help_message(help_text)
    
    # Add a command shortcuts section
    command_shortcuts = (
        "▪️ /start - Rozpocznij bota\n"
        "▪️ /menu - Otwórz menu główne\n"
        "▪️ /credits - Sprawdź kredyty\n"
        "▪️ /buy - Kup kredyty\n" 
        "▪️ /mode - Wybierz tryb czatu\n"
        "▪️ /image - Generuj obraz\n"
        "▪️ /help - Wyświetl pomoc\n"
        "▪️ /status - Sprawdź status\n"
    )
    
    message_text += f"\n\n{section_divider('Skróty Komend')}\n{command_shortcuts}"
    
    # Add a random tip if appropriate
    if should_show_tip(user_id, context):
        tip = get_random_tip()
        message_text += f"\n\n{section_divider('Porada Dnia')}\n💡 *Porada:* {tip}"
    
    keyboard = [
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ],
        [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Używamy centralnej funkcji update_menu_message
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu używając centralnej funkcji
    store_menu_state(context, user_id, 'help')
    
    return result

async def handle_image_section(update, context):
    """Obsługuje sekcję generowania obrazów"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz ścieżkę nawigacyjną
    navigation_path = get_navigation_path('image', language)
    
    # Dodajemy pasek nawigacyjny do tekstu
    message_text = f"*{navigation_path}*\n\n"
    
    message_text += get_text("image_usage", language)
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
    
    # Używamy centralnej funkcji update_menu_message
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu używając centralnej funkcji
    store_menu_state(context, user_id, 'image')
    
    return result

async def handle_back_to_main(update, context):
    """Obsługuje powrót do głównego menu"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Usuń aktualną wiadomość menu
    try:
        await query.message.delete()
    except Exception as e:
        print(f"Błąd przy usuwaniu wiadomości: {e}")
    
    # Pobierz tekst powitalny i usuń potencjalnie problematyczne znaczniki
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    # Link do zdjęcia bannera
    banner_url = "https://i.imgur.com/YPubLDE.png?v-1123"
    
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
        # Najpierw próba bez formatowania Markdown
        message = await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=banner_url,
            caption=welcome_text,
            reply_markup=reply_markup
        )
        
        # Zapisz ID wiadomości menu i stan menu używając centralnej funkcji
        store_menu_state(context, user_id, 'main', message.message_id)
        
        return True
    except Exception as e:
        print(f"Błąd przy wysyłaniu głównego menu ze zdjęciem: {e}")
        
        # Usuń wszystkie znaki formatowania Markdown
        clean_text = welcome_text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
        
        try:
            message = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=clean_text,
                reply_markup=reply_markup
            )
            
            # Zapisz stan menu używając centralnej funkcji
            store_menu_state(context, user_id, 'main', message.message_id)
            
            return True
        except Exception as e2:
            print(f"Błąd przy wysyłaniu fallbacku menu: {e2}")
            
            # Ostatnia próba - podstawowa wiadomość
            try:
                message = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Menu główne",
                    reply_markup=reply_markup
                )
                
                # Zapisz stan menu używając centralnej funkcji
                store_menu_state(context, user_id, 'main', message.message_id)
                
                return True
            except:
                return False

async def handle_model_selection(update, context):
    """Obsługuje wybór modelu AI z ulepszonym UI"""
    # Check if we're handling a callback query or a direct command
    if isinstance(update, Update) and update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()  # Acknowledge the callback query
    else:
        # This is a direct command or non-callback context
        user_id = update.effective_user.id

    language = get_user_language(context, user_id)
    
    print(f"Obsługa wyboru modelu dla użytkownika {user_id}")
    
    reply_markup = create_model_selection_markup(language)
    
    # If this is a callback query, update the message
    if isinstance(update, Update) and update.callback_query:
        # Używamy centralnej funkcji update_menu_message
        result = await update_menu_message(
            update.callback_query, 
            get_text("settings_choose_model", language),
            reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # In any other case, just return the markup for use by caller
        return reply_markup
    
    return result

# ==================== GŁÓWNE FUNKCJE MENU ====================

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla główne menu bota z przyciskami inline
    """
    user_id = update.effective_user.id
    
    # Upewnij się, że klawiatura systemowa jest usunięta
    await update.message.reply_text("Usuwam klawiaturę...", reply_markup=ReplyKeyboardRemove())
    
    # Pobierz język użytkownika
    language = get_user_language(context, user_id)
    
    # Przygotuj tekst powitalny
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    # Utwórz klawiaturę menu
    reply_markup = create_main_menu_markup(language)
    
    # Wyślij menu
    message = await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz ID wiadomości menu i stan menu używając centralnej funkcji
    store_menu_state(context, user_id, 'main', message.message_id)

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje wszystkie callbacki związane z menu - CENTRALNA FUNKCJA
    
    Returns:
        bool: True jeśli callback został obsłużony, False w przeciwnym razie
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Najpierw odpowiedz, aby usunąć oczekiwanie
    await query.answer()
    
    # Dodajmy logging dla debugowania
    print(f"Menu callback received: {query.data}")
    
    # Sekcje menu
    if query.data == "menu_section_chat_modes":
        return await handle_chat_modes_section(update, context)
    elif query.data == "menu_section_credits":
        return await handle_credits_section(update, context)
    elif query.data == "menu_section_history":
        return await handle_history_section(update, context)
    elif query.data == "menu_section_settings":
        return await handle_settings_section(update, context)
    elif query.data == "menu_help":
        return await handle_help_section(update, context)
    elif query.data == "menu_image_generate":
        return await handle_image_section(update, context)
    elif query.data == "menu_back_main":
        return await handle_back_to_main(update, context)
        
    # Opcje menu kredytów
    elif query.data == "menu_credits_check" or query.data == "credits_check":
        try:
            from handlers.credit_handler import handle_credit_callback
            handled = await handle_credit_callback(update, context)
            return handled
        except Exception as e:
            print(f"Błąd przy obsłudze kredytów: {e}")
            keyboard = [[InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_section_credits")]]
            await update_menu_message(query, "Wystąpił błąd przy sprawdzaniu kredytów. Spróbuj ponownie później.", 
                             InlineKeyboardMarkup(keyboard))
            return True
            
    elif query.data == "menu_credits_buy" or query.data == "credits_buy" or query.data == "Kup":
        try:
            # Importuj funkcję buy_command
            from handlers.credit_handler import buy_command
            
            # Utwórz sztuczny obiekt update
            fake_update = type('obj', (object,), {
                'effective_user': query.from_user,
                'message': query.message,
                'effective_chat': query.message.chat
            })
            
            # Usuń oryginalną wiadomość z menu
            try:
                await query.message.delete()
            except Exception as e:
                print(f"Nie można usunąć wiadomości: {e}")
            
            # Wywołaj nowy interfejs zakupów (/buy)
            await buy_command(fake_update, context)
            return True
            
        except Exception as e:
            print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
            import traceback
            traceback.print_exc()
            
            # W przypadku błędu, wyświetl komunikat
            try:
                keyboard = [[InlineKeyboardButton("⬅️ Menu główne", callback_data="menu_back_main")]]
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Wystąpił błąd. Spróbuj użyć komendy /buy",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e2:
                print(f"Błąd przy wyświetlaniu komunikatu: {e2}")
            return True
    
    # Obsługa szybkich akcji - przekazuje do odpowiednich handlerów
    elif query.data.startswith("quick_"):
        try:
            from handlers.callback_handler import handle_callback_query
            handled = await handle_callback_query(update, context)
            if handled:
                return True
        except Exception as e:
            print(f"Błąd przy obsłudze szybkiej akcji: {e}")
            
    # Obsługa ustawień
    elif query.data.startswith("settings_"):
        try:
            return await handle_settings_callbacks(update, context)
        except Exception as e:
            print(f"Błąd przy obsłudze ustawień: {e}")
    
    # Obsługa historii
    elif query.data.startswith("history_"):
        try:
            from handlers.menu_handler import handle_history_callbacks
            return await handle_history_callbacks(update, context)
        except Exception as e:
            print(f"Błąd przy obsłudze historii: {e}")
    
    # Obsługa callbacków związanych z trybami
    elif query.data.startswith("mode_"):
        try:
            from handlers.mode_handler import handle_mode_selection
            await handle_mode_selection(update, context)
            return True
        except Exception as e:
            print(f"Błąd przy obsłudze trybu: {e}")
            
    # Obsługa wyboru modelu
    elif query.data.startswith("model_"):
        try:
            model_id = query.data[6:]  # Usuń prefiks "model_"
            
            # Zapisz model w kontekście
            if 'user_data' not in context.chat_data:
                context.chat_data['user_data'] = {}
            
            if user_id not in context.chat_data['user_data']:
                context.chat_data['user_data'][user_id] = {}
            
            context.chat_data['user_data'][user_id]['current_model'] = model_id
            
            # Oznacz czat jako zainicjowany
            mark_chat_initialized(context, user_id)
            
            # Pobierz koszt kredytów dla wybranego modelu
            credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
            
            # Powiadom użytkownika o zmianie modelu
            model_name = AVAILABLE_MODELS.get(model_id, "Nieznany model")
            message = f"Wybrany model: *{model_name}*\nKoszt: *{credit_cost}* kredyt(ów) za wiadomość\n\nMożesz teraz zadać pytanie."
            
            # Przyciski powrotu
            keyboard = [[InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_section_settings")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Używamy centralnej funkcji update_menu_message
            await update_menu_message(
                query,
                message,
                reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return True
        except Exception as e:
            print(f"Błąd przy obsłudze wyboru modelu: {e}")
        
    # Obsługa wyboru języka
    elif query.data.startswith("start_lang_"):
        try:
            from handlers.start_handler import handle_language_selection
            return await handle_language_selection(update, context)
        except Exception as e:
            print(f"Błąd przy obsłudze wyboru języka: {e}")
    
    # Przekierowanie do innych handlerów
    try:
        # Sprawdź, czy to callback związany z kredytami
        if query.data.startswith("credits_") or query.data.startswith("buy_package_") or query.data == "credit_advanced_analytics":
            from handlers.credit_handler import handle_credit_callback
            handled = await handle_credit_callback(update, context)
            if handled:
                return True
    except Exception as e:
        print(f"Błąd w obsłudze callbacków kredytów: {e}")
        
    try:
        # Sprawdź, czy to callback związany z płatnościami
        if query.data.startswith("payment_") or query.data.startswith("buy_package_"):
            from handlers.payment_handler import handle_payment_callback
            handled = await handle_payment_callback(update, context)
            if handled:
                return True
    except Exception as e:
        print(f"Błąd w obsłudze callbacków płatności: {e}")
    
    # Obsługa callbacków dla onboardingu
    if query.data.startswith("onboarding_"):
        try:
            from handlers.onboarding_handler import handle_onboarding_callback
            return await handle_onboarding_callback(update, context)
        except Exception as e:
            print(f"Błąd w obsłudze onboardingu: {e}")
    
    # Obsługa callbacków dla funkcji zdjęć i dokumentów
    elif query.data in ["analyze_photo", "translate_photo", "analyze_document", "translate_document"]:
        try:
            from handlers.callback_handler import handle_callback_query
            return await handle_callback_query(update, context)
        except Exception as e:
            print(f"Błąd przy obsłudze funkcji zdjęć/dokumentów: {e}")
    
    # Obsługa callbacków dla potwierdzeń
    elif query.data.startswith("confirm_") or query.data == "cancel_operation":
        try:
            # Spróbuj różne handlery potwierdzeń
            from handlers.confirmation_handler import (
                handle_image_confirmation, handle_document_confirmation, 
                handle_photo_confirmation, handle_message_confirmation
            )
            
            if query.data.startswith("confirm_image_"):
                return await handle_image_confirmation(update, context)
            elif query.data.startswith("confirm_doc_"):
                return await handle_document_confirmation(update, context)
            elif query.data.startswith("confirm_photo_"):
                return await handle_photo_confirmation(update, context)
            elif query.data == "confirm_message" or query.data == "cancel_operation":
                return await handle_message_confirmation(update, context)
        except Exception as e:
            print(f"Błąd przy obsłudze potwierdzeń: {e}")
    
    # Jeśli dotarliśmy tutaj, oznacza to, że callback nie został obsłużony
    print(f"Nieobsłużony callback: {query.data}")
    
    # Zamiast próbować edytować istniejącą wiadomość, po prostu wysyłamy nową
    try:
        keyboard = [[InlineKeyboardButton("⬅️ Menu główne", callback_data="menu_back_main")]]
        
        # Używamy centralnej funkcji update_menu_message
        await update_menu_message(
            query,
            f"Nieznany przycisk '{query.data}'. Spróbuj ponownie później.",
            InlineKeyboardMarkup(keyboard)
        )
        
        return True
    except Exception as e:
        print(f"Błąd przy obsłudze nieobsłużonego callbacku: {e}")
        return False

# Funkcje pomocnicze obsługujące callbacki z różnych kategorii

async def handle_settings_callbacks(update, context):
    """Obsługuje callbacki związane z ustawieniami"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Obsługa opcji ustawień
    if query.data == "settings_model":
        return await handle_model_selection(update, context)
    elif query.data == "settings_language":
        # Pokaż menu wyboru języka
        keyboard = create_language_selection_markup(language)
        
        # Używamy centralnej funkcji update_menu_message
        await update_menu_message(
            query,
            get_text("settings_choose_language", language, default="Wybierz język:"),
            keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    elif query.data == "settings_name":
        message_text = get_text("settings_change_name", language, default="Aby zmienić swoją nazwę, użyj komendy /setname [twoja_nazwa].\n\nNa przykład: /setname Jan Kowalski")
        keyboard = [[InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")]]
        
        # Używamy centralnej funkcji update_menu_message
        await update_menu_message(
            query,
            message_text,
            InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    return False  # Nie obsłużono callbacku

async def handle_history_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje callbacki związane z historią
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    print(f"History callback: {query.data}")  # Debugging
    
    if query.data == "history_view":
        print("Handling history_view callback")  # Debugging
        
        # Pobierz aktywną konwersację
        try:
            from database.supabase_client import get_active_conversation, get_conversation_history
            conversation = get_active_conversation(user_id)
            
            if not conversation:
                message_text = "Brak aktywnej konwersacji."
                keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
                
                # Używamy centralnej funkcji update_menu_message
                await update_menu_message(
                    query,
                    message_text,
                    InlineKeyboardMarkup(keyboard)
                )
                return True
            
            # Pobierz historię konwersacji
            history = get_conversation_history(conversation['id'])
            
            if not history:
                message_text = "Historia jest pusta."
                keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
                
                # Używamy centralnej funkcji update_menu_message
                await update_menu_message(
                    query,
                    message_text,
                    InlineKeyboardMarkup(keyboard)
                )
                return True
            
            # Przygotuj tekst z historią
            message_text = "*Historia konwersacji*\n\n"
            
            for i, msg in enumerate(history[-10:]):  # Ostatnie 10 wiadomości
                sender = "Użytkownik" if msg.get('is_from_user') else "Bot"
                
                # Skróć treść wiadomości, jeśli jest zbyt długa
                content = msg.get('content', '')
                if content and len(content) > 100:
                    content = content[:97] + "..."
                    
                # Usuń znaki formatowania Markdown
                content = content.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
                
                message_text += f"{i+1}. *{sender}*: {content}\n\n"
            
            # Dodaj przycisk do powrotu
            keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
            
            # Używamy centralnej funkcji update_menu_message
            try:
                await update_menu_message(
                    query,
                    message_text,
                    InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                print(f"Error in update_menu_message: {e}")
                # Fallback bez formatowania
                await update_menu_message(
                    query,
                    message_text.replace("*", ""),
                    InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            print(f"Error in history_view: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                # Informuj o błędzie
                await update_menu_message(
                    query,
                    "Wystąpił błąd podczas ładowania historii.",
                    InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]])
                )
            except:
                pass
            
        return True
    
    elif query.data == "history_new":
        print("Handling history_new callback")  # Debugging
        
        try:
            # Twórz nową konwersację
            from database.supabase_client import create_new_conversation
            conversation = create_new_conversation(user_id)
            
            # Oznacz czat jako zainicjowany
            mark_chat_initialized(context, user_id)
            
            # Aktualizuj wiadomość
            message_text = "✅ Utworzono nową konwersację."
            keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
            
            # Używamy centralnej funkcji update_menu_message
            await update_menu_message(
                query,
                message_text,
                InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Error in history_new: {e}")
            
            try:
                # Informuj o błędzie
                await update_menu_message(
                    query,
                    "Wystąpił błąd podczas tworzenia nowej konwersacji.",
                    InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]])
                )
            except:
                pass
                
        return True
    
    elif query.data == "history_delete":
        print("Handling history_delete callback")  # Debugging
        
        try:
            # Pytanie o potwierdzenie
            message_text = "Czy na pewno chcesz usunąć historię? Tej operacji nie można cofnąć."
            keyboard = [
                [
                    InlineKeyboardButton("✅ Tak", callback_data="history_confirm_delete"),
                    InlineKeyboardButton("❌ Nie", callback_data="menu_section_history")
                ]
            ]
            
            # Używamy centralnej funkcji update_menu_message
            await update_menu_message(
                query,
                message_text,
                InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Error in history_delete: {e}")
            
            try:
                # Informuj o błędzie
                await update_menu_message(
                    query,
                    "Wystąpił błąd.",
                    InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]])
                )
            except:
                pass
                
        return True
    
    elif query.data == "history_confirm_delete":
        print("Handling history_confirm_delete callback")  # Debugging
        
        try:
            # Usuń historię (tworząc nową konwersację)
            from database.supabase_client import create_new_conversation
            conversation = create_new_conversation(user_id)
            
            # Aktualizuj wiadomość
            message_text = "✅ Historia została pomyślnie usunięta."
            keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]
            
            # Używamy centralnej funkcji update_menu_message
            await update_menu_message(
                query,
                message_text,
                InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Error in history_confirm_delete: {e}")
            
            try:
                # Informuj o błędzie
                await update_menu_message(
                    query,
                    "Wystąpił błąd podczas usuwania historii.",
                    InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]])
                )
            except:
                pass
                
        return True
    
    return False  # Nie obsłużono callbacku

async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla dostępne modele AI i pozwala użytkownikowi wybrać jeden z nich
    Użycie: /models
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    message_text = f"*{get_text('main_menu', language, default='Menu główne')} > {get_text('settings_choose_model', language, default='Wybór modelu')}*\n\n"
    message_text += get_text("settings_choose_model", language, default="Wybierz model AI, którego chcesz używać:")
    
    # Tworzenie klawiatury przy użyciu funkcji pomocniczej
    reply_markup = create_model_selection_markup(language)
    
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje komendę /help
    Wyświetla informacje pomocnicze o bocie z nowym interfejsem
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz tekst pomocy z tłumaczeń
    help_text = get_text("help_text", language)
    
    # Dodaj klawiaturę z przyciskami szybkiego dostępu i powrotem do menu
    keyboard = [
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ],
        [InlineKeyboardButton("⬅️ " + get_text("back_to_main_menu", language, default="Powrót do menu głównego"), callback_data="menu_back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Próba wysłania z formatowaniem Markdown
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except Exception as e:
        # W przypadku błędu, spróbuj wysłać bez formatowania
        print(f"Błąd formatowania Markdown w help_command: {e}")
        try:
            # Usuń wszystkie znaki Markdown
            clean_text = help_text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
            await update.message.reply_text(
                clean_text,
                reply_markup=reply_markup
            )
        except Exception as e2:
            print(f"Drugi błąd w help_command: {e2}")
            # Ostateczna próba - wysłanie uproszczonego tekstu pomocy
            simple_help = "Pomoc i informacje o bocie. Dostępne komendy: /start, /credits, /buy, /status, /newchat, /mode, /image, /restart, /help, /code."
            await update.message.reply_text(
                simple_help,
                reply_markup=reply_markup
            )

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sprawdza status konta użytkownika z nowym interfejsem
    Użycie: /status
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz status kredytów
    credits = get_user_credits(user_id)
    
    # Pobranie aktualnego trybu czatu
    current_mode = get_text("no_mode", language)
    current_mode_cost = 1
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            mode_id = user_data['current_mode']
            current_mode = get_text(f"chat_mode_{mode_id}", language, default=CHAT_MODES[mode_id]["name"])
            current_mode_cost = CHAT_MODES[mode_id]["credit_cost"]
    
    # Pobierz aktualny model
    current_model = DEFAULT_MODEL
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_model' in user_data and user_data['current_model'] in AVAILABLE_MODELS:
            current_model = user_data['current_model']
    
    model_name = AVAILABLE_MODELS.get(current_model, "Unknown Model")
    
    # Pobierz status wiadomości
    message_status = get_message_status(user_id)
    
    # Stwórz wiadomość o statusie, używając tłumaczeń
    message = f"""
*{get_text("status_command", language, bot_name=BOT_NAME)}*

{get_text("available_credits", language)}: *{credits}*
{get_text("current_mode", language)}: *{current_mode}* ({get_text("cost", language)}: {current_mode_cost} {get_text("credits_per_message", language)})
{get_text("current_model", language)}: *{model_name}*

{get_text("messages_info", language)}:
- {get_text("messages_used", language)}: *{message_status["messages_used"]}*
- {get_text("messages_limit", language)}: *{message_status["messages_limit"]}*
- {get_text("messages_left", language)}: *{message_status["messages_left"]}*

{get_text("operation_costs", language)}:
- {get_text("standard_message", language)} (GPT-3.5): 1 {get_text("credit", language)}
- {get_text("premium_message", language)} (GPT-4o): 3 {get_text("credits", language)}
- {get_text("expert_message", language)} (GPT-4): 5 {get_text("credits", language)}
- {get_text("dalle_image", language)}: 10-15 {get_text("credits", language)}
- {get_text("document_analysis", language)}: 5 {get_text("credits", language)}
- {get_text("photo_analysis", language)}: 8 {get_text("credits", language)}

{get_text("buy_more_credits", language)}: /buy
"""
    
    # Dodaj przyciski menu dla łatwiejszej nawigacji
    keyboard = [
        [InlineKeyboardButton(get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
        [InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes")],
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat")
        ],
        [InlineKeyboardButton("⬅️ " + get_text("back_to_main_menu", language, default="Powrót do menu głównego"), callback_data="menu_back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except Exception as e:
        print(f"Błąd formatowania w check_status: {e}")
        # Próba wysłania bez formatowania
        await update.message.reply_text(message, reply_markup=reply_markup)

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rozpoczyna nową konwersację z ulepszonym interfejsem"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Utwórz nową konwersację
    from database.supabase_client import create_new_conversation
    conversation = create_new_conversation(user_id)
    
    if conversation:
        # Oznacz czat jako zainicjowany
        mark_chat_initialized(context, user_id)
        
        # Dodaj przyciski menu dla łatwiejszej nawigacji
        keyboard = [
            [InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes")],
            [InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits")],
            # Pasek szybkiego dostępu
            [
                InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
                InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
            ],
            [InlineKeyboardButton("⬅️ " + get_text("back_to_main_menu", language, default="Powrót do menu głównego"), callback_data="menu_back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            get_text("newchat_command", language),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            get_text("new_chat_error", language),
            parse_mode=ParseMode.MARKDOWN
        )

async def set_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ustawia nazwę użytkownika
    Użycie: /setname [nazwa]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy podano argumenty
    if not context.args or len(' '.join(context.args)) < 1:
        await update.message.reply_text(
            get_text("settings_change_name", language),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Połącz argumenty, aby utworzyć nazwę
    new_name = ' '.join(context.args)
    
    # Ogranicz długość nazwy
    if len(new_name) > 50:
        new_name = new_name[:47] + "..."
    
    try:
        # Aktualizuj nazwę użytkownika w bazie danych Supabase
        from database.supabase_client import supabase
        
        response = supabase.table('users').update(
            {"first_name": new_name}
        ).eq('id', user_id).execute()
        
        # Aktualizuj nazwę w kontekście, jeśli istnieje
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['name'] = new_name
        
        # Potwierdź zmianę nazwy
        await update.message.reply_text(
            f"{get_text('name_changed', language)} *{new_name}*",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Błąd przy zmianie nazwy użytkownika: {e}")
        await update.message.reply_text(
            "Wystąpił błąd podczas zmiany nazwy. Spróbuj ponownie później.",
            parse_mode=ParseMode.MARKDOWN
        )