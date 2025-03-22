from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CHAT_MODES, AVAILABLE_MODELS, DEFAULT_MODEL
from utils.translations import get_text
from database.credits_client import get_user_credits
from utils.user_utils import mark_chat_initialized
from database.supabase_client import create_new_conversation

def get_user_language(context, user_id):
    """Pomocnicza funkcja do pobierania języka użytkownika"""
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data'] and 'language' in context.chat_data['user_data'][user_id]:
        return context.chat_data['user_data'][user_id]['language']
    return "pl"  # Domyślny język

async def show_modes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pokazuje dostępne tryby czatu"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Usuń poprzednią wiadomość, jeśli to odpowiedź na komendę
    try:
        # Próba usunięcia wiadomości z komendą /mode
        await update.message.delete()
    except Exception as e:
        print(f"Nie można usunąć wiadomości z komendą: {e}")
    
    # Import potrzebne rzeczy z menu_handler
    from config import CHAT_MODES
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Stwórz nagłówek wiadomości
    message_text = f"*{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_chat_mode', language)}*\n\n"
    message_text += get_text("select_chat_mode", language, default="Wybierz tryb czatu:")
    
    # Stwórz przyciski dla trybów - tak samo jak w menu
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
    
    # Wyślij wiadomość z menu
    try:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Błąd pokazywania menu trybów: {e}")
        # Fallback bez formatowania
        await update.message.reply_text(
            "Wybierz tryb czatu:",
            reply_markup=reply_markup
        )

async def handle_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje wybór trybu czatu z ulepszoną wizualizacją"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Wyodrębnij mode_id z callback_data
    mode_id = query.data.replace("mode_", "")
    
    print(f"Obsługiwanie wyboru trybu: {mode_id}")
    
    # Sprawdź, czy tryb istnieje
    if mode_id not in CHAT_MODES:
        try:
            await query.answer(get_text("mode_not_available", language, default="Wybrany tryb nie jest dostępny."))
            
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=get_text("mode_not_available", language, default="Wybrany tryb nie jest dostępny."),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=get_text("mode_not_available", language, default="Wybrany tryb nie jest dostępny."),
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            print(f"Błąd przy edycji wiadomości: {e}")
        return
    
    # Zapisz wybrany tryb w kontekście użytkownika
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    context.chat_data['user_data'][user_id]['current_mode'] = mode_id
    print(f"Zapisano tryb {mode_id} dla użytkownika {user_id}")
    
    # Jeśli tryb ma określony model, ustaw go również
    if "model" in CHAT_MODES[mode_id]:
        context.chat_data['user_data'][user_id]['current_model'] = CHAT_MODES[mode_id]["model"]
        print(f"Ustawiono model {CHAT_MODES[mode_id]['model']} dla użytkownika {user_id}")
    
    # Pobierz przetłumaczoną nazwę trybu i inne informacje
    mode_name = get_text(f"chat_mode_{mode_id}", language, default=CHAT_MODES[mode_id]["name"])
    prompt_key = f"prompt_{mode_id}"
    mode_description = get_text(prompt_key, language, default=CHAT_MODES[mode_id]["prompt"])
    credit_cost = CHAT_MODES[mode_id]["credit_cost"]
    model_name = AVAILABLE_MODELS.get(CHAT_MODES[mode_id].get("model", DEFAULT_MODEL), "Model standardowy")
    
    # Skróć opis, jeśli jest zbyt długi
    if len(mode_description) > 200:
        short_description = mode_description[:197] + "..."
    else:
        short_description = mode_description
    
    try:
        print(f"Przygotowywanie wiadomości dla trybu {mode_id}")
        # Use enhanced formatting with visual card
        from utils.message_formatter_enhanced import format_mode_selection
        message_text = format_mode_selection(mode_name, short_description, credit_cost, model_name)
        
        # Add tip about mode usage if appropriate
        from utils.tips import should_show_tip, get_random_tip
        if should_show_tip(user_id, context):
            tip = get_random_tip('general')
            message_text += f"\n\n💡 *Porada:* {tip}"
        
        # Dodaj przyciski powrotu do menu trybów
        keyboard = [
            [InlineKeyboardButton("✏️ " + get_text("start_chat", language, default="Rozpocznij rozmowę"), callback_data="quick_new_chat")],
            [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_section_chat_modes")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        print(f"Przygotowano przyciski dla trybu {mode_id}, aktualizacja wiadomości...")
        
        # Improved check for caption - make sure the message has a caption attribute WITH content
        if hasattr(query.message, 'caption') and query.message.caption is not None:
            try:
                await query.edit_message_caption(
                    caption=message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                print(f"Zaktualizowano caption dla trybu {mode_id}")
            except Exception as e:
                print(f"Błąd przy edycji caption: {e}")
                # Fallback to editing text instead
                await query.edit_message_text(
                    text=message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                print(f"Fallback: Zaktualizowano text dla trybu {mode_id}")
        else:
            # Use edit_message_text for regular text messages
            await query.edit_message_text(
                text=message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            print(f"Zaktualizowano text dla trybu {mode_id}")
            
        await query.answer(get_text("mode_selected", language, default="Tryb wybrany pomyślnie"))
    except Exception as e:
        print(f"Błąd przy edycji wiadomości dla trybu {mode_id}: {e}")
        import traceback
        traceback.print_exc()
        try:
            # Próba wysłania bez formatowania Markdown
            plain_message = f"Wybrano tryb: {mode_name}\n\n{short_description}\n\nKoszt: {credit_cost} kredytów"
            
            # Always use edit_message_text here as a fallback
            await query.edit_message_text(
                text=plain_message,
                reply_markup=reply_markup
            )
            print(f"Zaktualizowano text (bez Markdown) dla trybu {mode_id}")
        except Exception as e2:
            print(f"Drugi błąd przy edycji wiadomości dla trybu {mode_id}: {e2}")
            traceback.print_exc()
        
    # Utwórz nową konwersację dla wybranego trybu
    try:
        from database.supabase_client import create_new_conversation
        conversation = create_new_conversation(user_id)
        print(f"Utworzono nową konwersację dla użytkownika {user_id} w trybie {mode_id}")
        
        # Mark chat as initialized
        try:
            from utils.user_utils import mark_chat_initialized
            mark_chat_initialized(context, user_id)
            print(f"Oznaczono czat jako zainicjowany dla użytkownika {user_id}")
        except Exception as e:
            print(f"Błąd przy oznaczaniu czatu jako zainicjowany: {e}")
            traceback.print_exc()
    except Exception as e:
        print(f"Błąd przy tworzeniu nowej konwersacji: {e}")
        traceback.print_exc()