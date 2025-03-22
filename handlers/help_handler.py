from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import DEFAULT_MODEL, BOT_NAME, CREDIT_COSTS, AVAILABLE_MODELS, CHAT_MODES
from utils.translations import get_text
from handlers.menu_handler import get_user_language
from database.credits_client import get_user_credits
from database.supabase_client import get_message_status

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje komendę /help
    Wyświetla informacje pomocnicze o bocie
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz tekst pomocy z tłumaczeń
    help_text = get_text("help_text", language)
    
    # Dodaj tylko przycisk Menu
    keyboard = [
        [InlineKeyboardButton("Menu", callback_data="menu_back_main")]
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
            await update.message.reply_text(
                help_text,
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
    Sprawdza status konta użytkownika
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
        [InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except Exception as e:
        print(f"Błąd formatowania w check_status: {e}")
        # Próba wysłania bez formatowania
        await update.message.reply_text(message, reply_markup=reply_markup)