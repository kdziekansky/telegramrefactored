from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from utils.visual_styles import create_header, create_status_indicator
from utils.user_utils import get_user_language
from utils.menu import update_menu
from utils.translations import get_text
from utils.credit_warnings import format_credit_usage_report
from utils.tips import get_random_tip, should_show_tip, get_contextual_tip
from database.credits_client import get_user_credits, check_user_credits, deduct_user_credits
from database.supabase_client import save_message, get_active_conversation, get_conversation_history, increment_messages_used
from utils.openai_client import generate_image_dall_e, analyze_document, analyze_image, chat_completion_stream, prepare_messages_from_history
from config import CREDIT_COSTS, MAX_CONTEXT_MESSAGES, CHAT_MODES
import datetime

async def handle_image_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje potwierdzenie generowania obrazu"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data.startswith("confirm_image_"):
        prompt = query.data[14:].replace('_', ' ')
        
        await update_menu(
            query,
            create_status_indicator('loading', "Generowanie obrazu") + "\n\n" +
            f"*Prompt:* {prompt}",
            None,
            parse_mode=ParseMode.MARKDOWN
        )
        
        credits = get_user_credits(user_id)
        if not check_user_credits(user_id, credit_cost):
            await query.edit_message_text(
                create_header("Brak wystarczających kredytów", "error") +
                "W międzyczasie twój stan kredytów zmienił się i nie masz już wystarczającej liczby kredytów.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        credits_before = credits
        
        image_url = await generate_image_dall_e(prompt)
        
        deduct_user_credits(user_id, credit_cost, get_text("image_generation", language, default="Generowanie obrazu"))
        
        credits_after = get_user_credits(user_id)
        
        if image_url:
            caption = create_header("Wygenerowany obraz", "image")
            caption += f"*Prompt:* {prompt}\n"
            
            usage_report = format_credit_usage_report(
                "Generowanie obrazu", 
                credit_cost, 
                credits_before, 
                credits_after
            )
            caption += f"\n{usage_report}"
            
            if should_show_tip(user_id, context):
                tip = get_random_tip('image')
                caption += f"\n\n💡 *Porada:* {tip}"
            
            await query.message.delete()
            
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=image_url,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                create_header("Błąd generowania", "error") +
                get_text("image_generation_error", language, default="Przepraszam, wystąpił błąd podczas generowania obrazu. Spróbuj ponownie z innym opisem."),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "cancel_operation":
        await query.edit_message_text(
            create_header("Operacja anulowana", "info") +
            "Generowanie obrazu zostało anulowane.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_document_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles confirmation of document operations when cost warning was shown"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data.startswith("confirm_doc_analysis_"):
        document_id = query.data[20:]
        
        if ('user_data' not in context.chat_data or 
            user_id not in context.chat_data['user_data'] or
            'last_document_name' not in context.chat_data['user_data'][user_id]):
            
            await query.edit_message_text(
                create_header("Błąd operacji", "error") +
                "Nie znaleziono informacji o dokumencie. Spróbuj wysłać go ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        file_name = context.chat_data['user_data'][user_id]['last_document_name']
        
        await query.edit_message_text(
            create_status_indicator('loading', "Analizowanie dokumentu") + "\n\n" +
            f"*Dokument:* {file_name}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        credit_cost = CREDIT_COSTS["document"]
        
        credits = get_user_credits(user_id)
        if not check_user_credits(user_id, credit_cost):
            await query.edit_message_text(
                create_header("Brak wystarczających kredytów", "error") +
                "W międzyczasie twój stan kredytów zmienił się i nie masz już wystarczającej liczby kredytów.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        credits_before = credits
        
        try:
            file = await context.bot.get_file(document_id)
            file_bytes = await file.download_as_bytearray()
            
            analysis = await analyze_document(file_bytes, file_name)
            
            deduct_user_credits(user_id, credit_cost, f"Analiza dokumentu: {file_name}")
            
            credits_after = get_user_credits(user_id)
            
            result_message = create_header(f"Analiza dokumentu: {file_name}", "document")
            
            analysis_excerpt = analysis[:3000]
            if len(analysis) > 3000:
                analysis_excerpt += "...\n\n(Analiza została skrócona ze względu na długość)"
            
            result_message += analysis_excerpt
            
            usage_report = format_credit_usage_report(
                "Analiza dokumentu", 
                credit_cost, 
                credits_before, 
                credits_after
            )
            result_message += f"\n\n{usage_report}"
            
            if should_show_tip(user_id, context):
                tip = get_random_tip('document')
                result_message += f"\n\n💡 *Porada:* {tip}"
            
            await query.edit_message_text(
                result_message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Error analyzing document: {e}")
            await query.edit_message_text(
                create_header("Błąd analizy", "error") +
                "Wystąpił błąd podczas analizowania dokumentu. Spróbuj ponownie później.",
                parse_mode=ParseMode.MARKDOWN
            )

async def handle_photo_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles confirmation of photo operations when cost warning was shown"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data.startswith("confirm_photo_"):
        parts = query.data.split("_")
        if len(parts) >= 4:
            mode = parts[2]
            photo_id = "_".join(parts[3:])
            
            if ('user_data' not in context.chat_data or 
                user_id not in context.chat_data['user_data'] or
                'last_photo_id' not in context.chat_data['user_data'][user_id]):
                
                await query.edit_message_text(
                    create_header("Błąd operacji", "error") +
                    "Nie znaleziono informacji o zdjęciu. Spróbuj wysłać je ponownie.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            if mode == "translate":
                operation_name = "Tłumaczenie tekstu ze zdjęcia"
                status_message = create_status_indicator('loading', "Tłumaczenie tekstu ze zdjęcia")
            else:
                operation_name = "Analiza zdjęcia"
                status_message = create_status_indicator('loading', "Analizowanie zdjęcia")
            
            await query.edit_message_text(
                status_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            credit_cost = CREDIT_COSTS["photo"]
            
            credits = get_user_credits(user_id)
            if not check_user_credits(user_id, credit_cost):
                await query.edit_message_text(
                    create_header("Brak wystarczających kredytów", "error") +
                    "W międzyczasie twój stan kredytów zmienił się i nie masz już wystarczającej liczby kredytów.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            credits_before = credits
            
            try:
                file = await context.bot.get_file(photo_id)
                file_bytes = await file.download_as_bytearray()
                
                result = await analyze_image(file_bytes, f"photo_{photo_id}.jpg", mode=mode)
                
                deduct_user_credits(user_id, credit_cost, operation_name)
                
                credits_after = get_user_credits(user_id)
                
                if mode == "translate":
                    result_message = create_header("Tłumaczenie tekstu ze zdjęcia", "translation")
                else:
                    result_message = create_header("Analiza zdjęcia", "analysis")
                
                result_message += result
                
                usage_report = format_credit_usage_report(
                    operation_name, 
                    credit_cost, 
                    credits_before, 
                    credits_after
                )
                result_message += f"\n\n{usage_report}"
                
                if should_show_tip(user_id, context):
                    tip = get_random_tip('document')
                    result_message += f"\n\n💡 *Porada:* {tip}"
                
                await query.edit_message_text(
                    result_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                print(f"Error processing photo: {e}")
                await query.edit_message_text(
                    create_header("Błąd operacji", "error") +
                    f"Wystąpił błąd podczas {operation_name.lower()}. Spróbuj ponownie później.",
                    parse_mode=ParseMode.MARKDOWN
                )
    
    elif query.data == "cancel_operation":
        await query.edit_message_text(
            create_header("Operacja anulowana", "info") +
            "Operacja została anulowana.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_message_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles confirmation of AI message when cost warning was shown"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data == "confirm_message":
        if ('user_data' not in context.chat_data or 
            user_id not in context.chat_data['user_data'] or 
            'pending_message' not in context.chat_data['user_data'][user_id]):
            
            await query.edit_message_text(
                create_header("Błąd operacji", "error") +
                "Nie znaleziono oczekującej wiadomości. Spróbuj ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user_message = context.chat_data['user_data'][user_id]['pending_message']
        
        await query.message.delete()
        
        status_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=create_status_indicator('loading', "Generowanie odpowiedzi"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        current_mode = "no_mode"
        credit_cost = 1
        
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            user_data = context.chat_data['user_data'][user_id]
            if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
                current_mode = user_data['current_mode']
                credit_cost = CHAT_MODES[current_mode]["credit_cost"]
        
        try:
            conversation = get_active_conversation(user_id)
            conversation_id = conversation['id']
        except Exception as e:
            print(f"Błąd przy pobieraniu konwersacji: {e}")
            await status_message.edit_text(
                create_header("Błąd konwersacji", "error") +
                "Wystąpił błąd przy pobieraniu konwersacji. Spróbuj ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            save_message(conversation_id, user_id, user_message, is_from_user=True)
        except Exception as e:
            print(f"Błąd przy zapisie wiadomości użytkownika: {e}")
        
        try:
            history = get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
        except Exception as e:
            print(f"Błąd przy pobieraniu historii: {e}")
            history = []
        
        model_to_use = CHAT_MODES[current_mode].get("model", DEFAULT_MODEL)
        
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            user_data = context.chat_data['user_data'][user_id]
            if 'current_model' in user_data:
                model_to_use = user_data['current_model']
                credit_cost = CREDIT_COSTS["message"].get(model_to_use, CREDIT_COSTS["message"]["default"])
        
        system_prompt = CHAT_MODES[current_mode]["prompt"]
        
        messages = prepare_messages_from_history(history, user_message, system_prompt)
        
        credits_before = get_user_credits(user_id)
        
        full_response = ""
        buffer = ""
        last_update = datetime.datetime.now().timestamp()
        
        try:
            response_message = await status_message.edit_text(
                create_header("Odpowiedź AI", "chat"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            async for chunk in chat_completion_stream(messages, model=model_to_use):
                full_response += chunk
                buffer += chunk
                
                current_time = datetime.datetime.now().timestamp()
                if current_time - last_update >= 1.0 or len(buffer) > 100:
                    try:
                        await response_message.edit_text(
                            create_header("Odpowiedź AI", "chat") + full_response + "▌",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        buffer = ""
                        last_update = current_time
                    except Exception as e:
                        print(f"Błąd przy aktualizacji wiadomości: {e}")
            
            try:
                await response_message.edit_text(
                    create_header("Odpowiedź AI", "chat") + full_response,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                print(f"Błąd formatowania Markdown: {e}")
                await response_message.edit_text(
                    create_header("Odpowiedź AI", "chat") + full_response,
                    parse_mode=None
                )
            
            save_message(conversation_id, user_id, full_response, is_from_user=False, model_used=model_to_use)
            
            deduct_user_credits(user_id, credit_cost, 
                               get_text("message_model", language, model=model_to_use, default=f"Wiadomość ({model_to_use})"))
            
            credits_after = get_user_credits(user_id)
            
            usage_report = format_credit_usage_report(
                "Wiadomość AI", 
                credit_cost, 
                credits_before, 
                credits_after
            )
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=usage_report,
                parse_mode=ParseMode.MARKDOWN
            )
            
            if credits_after < 5:
                low_credits_warning = create_header("Niski stan kredytów", "warning")
                low_credits_warning += f"Pozostało Ci tylko *{credits_after}* kredytów. Rozważ zakup pakietu, aby kontynuować korzystanie z bota."
                
                keyboard = [[InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=low_credits_warning,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            
            tip = get_contextual_tip('chat', context, user_id)
            if tip:
                tip_message = f"💡 *Porada:* {tip}"
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=tip_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            increment_messages_used(user_id)
            
        except Exception as e:
            print(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
            await status_message.edit_text(
                create_header("Błąd odpowiedzi", "error") +
                get_text("response_error", language, error=str(e)),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "cancel_operation":
        await query.edit_message_text(
            create_header("Operacja anulowana", "info") +
            "Wysłanie wiadomości zostało anulowane.",
            parse_mode=ParseMode.MARKDOWN
        )