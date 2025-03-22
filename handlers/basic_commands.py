from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import BOT_NAME
from utils.translations import get_text
from utils.user_utils import get_user_language, mark_chat_initialized
from database.supabase_client import create_new_conversation, get_active_conversation, get_message_status
from database.credits_client import get_user_credits

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /restart
    Resetuje kontekst bota, pokazuje informacje o bocie i aktualnych ustawieniach użytkownika
    """
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Resetowanie konwersacji - tworzymy nową konwersację i czyścimy kontekst
        conversation = create_new_conversation(user_id)
        
        # Zachowujemy wybrane ustawienia użytkownika (język, model)
        user_data = {}
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            # Pobieramy tylko podstawowe ustawienia, reszta jest resetowana
            old_user_data = context.chat_data['user_data'][user_id]
            if 'language' in old_user_data:
                user_data['language'] = old_user_data['language']
            if 'current_model' in old_user_data:
                user_data['current_model'] = old_user_data['current_model']
            if 'current_mode' in old_user_data:
                user_data['current_mode'] = old_user_data['current_mode']
        
        # Resetujemy dane użytkownika w kontekście i ustawiamy tylko zachowane ustawienia
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        context.chat_data['user_data'][user_id] = user_data
        
        # Pobierz język użytkownika
        language = get_user_language(context, user_id)
        
        # Wyślij potwierdzenie restartu
        restart_message = get_text("restart_command", language)
        
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
        
        # Wyślij wiadomość z menu
        try:
            # Używamy welcome_message zamiast main_menu + status
            welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=restart_message + "\n\n" + welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Zapisz ID wiadomości menu i stan menu
            from handlers.menu_handler import store_menu_state
            store_menu_state(context, user_id, 'main', message.message_id)
        except Exception as e:
            print(f"Błąd przy wysyłaniu wiadomości po restarcie: {e}")
            # Próbuj wysłać prostą wiadomość
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=restart_message
                )
            except Exception as e2:
                print(f"Nie udało się wysłać nawet prostej wiadomości: {e2}")
        
    except Exception as e:
        print(f"Błąd w funkcji restart_command: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            # Używamy context.bot.send_message zamiast update.message.reply_text
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=get_text("restart_error", get_user_language(context, update.effective_user.id))
            )
        except Exception as e2:
            print(f"Błąd przy wysyłaniu wiadomości o błędzie: {e2}")

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sprawdza status konta użytkownika
    Użycie: /status
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz status kredytów
    credits = get_user_credits(user_id)
    
    # Pobranie aktualnego trybu czatu
    from config import CHAT_MODES
    current_mode = get_text("no_mode", language)
    current_mode_cost = 1
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            mode_id = user_data['current_mode']
            current_mode = get_text(f"chat_mode_{mode_id}", language, default=CHAT_MODES[mode_id]["name"])
            current_mode_cost = CHAT_MODES[mode_id]["credit_cost"]
    
    # Pobierz aktualny model
    from config import DEFAULT_MODEL, AVAILABLE_MODELS
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