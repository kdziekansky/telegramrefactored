from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.ui_elements import credit_status_bar, info_card, section_divider
from utils.user_utils import get_user_language, mark_chat_initialized
from utils.translations import get_text
from database.supabase_client import create_new_conversation, get_active_conversation
from database.credits_client import get_user_credits, get_credit_packages
from config import BOT_NAME

async def handle_buy_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje przycisk zakupu kredytów"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Importuj funkcję buy_command
        from handlers.credit_handler import buy_command
        
        # Utwórz sztuczny obiekt update
        fake_update = type('obj', (object,), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_chat': query.message.chat
        })
        
        # Usuń oryginalną wiadomość z menu, aby nie powodować zamieszania
        await query.message.delete()
        
        # Wywołaj nowy interfejs zakupów (/buy)
        await buy_command(fake_update, context)
        
    except Exception as e:
        print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
        import traceback
        traceback.print_exc()

async def handle_unknown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje wszystkie nieznane callbacki"""
    query = update.callback_query
    await query.answer("Ta funkcja jest w trakcie implementacji")
    
    # Logowanie nieznanego callbacka
    print(f"Nieobsłużony callback: {query.data}")
    
    # Informacja dla użytkownika
    try:
        await query.edit_message_text(
            f"Funkcja '{query.data}' jest w trakcie implementacji.\n\nWróć do menu głównego i spróbuj innej opcji.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Powrót do menu", callback_data="menu_back_main")
            ]])
        )
    except Exception as e:
        print(f"Błąd przy edycji wiadomości: {e}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa zapytań zwrotnych (z przycisków)"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodaj logger
    print(f"Otrzymano callback: {query.data} od użytkownika {user_id}")
    
    # Najpierw odpowiedz, aby usunąć oczekiwanie
    await query.answer()
    
    # 10. Szybkie akcje
    if query.data == "quick_new_chat":
        try:
            # Utwórz nową konwersację
            conversation = create_new_conversation(user_id)
            mark_chat_initialized(context, user_id)
            
            await query.answer(get_text("new_chat_created", language))
            
            # Zamknij menu, aby użytkownik mógł zacząć pisać
            await query.message.delete()
            
            # Wyślij komunikat potwierdzający
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=get_text("new_chat_created_message", language)
            )
            return True
        except Exception as e:
            print(f"Błąd przy tworzeniu nowej rozmowy: {e}")
            import traceback
            traceback.print_exc()

    elif query.data == "quick_last_chat":
        try:
            # Pobierz aktywną konwersację
            conversation = get_active_conversation(user_id)
            
            if conversation:
                await query.answer(get_text("returning_to_last_chat", language))
                
                # Zamknij menu
                await query.message.delete()
            else:
                await query.answer(get_text("no_active_chat", language))
                
                # Utwórz nową konwersację
                create_new_conversation(user_id)
                
                # Zamknij menu
                await query.message.delete()
                
                # Wyślij komunikat
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=get_text("new_chat_created_message", language)
                )
            return True
        except Exception as e:
            print(f"Błąd przy obsłudze ostatniej rozmowy: {e}")
            import traceback
            traceback.print_exc()

    elif query.data == "quick_buy_credits":
        try:
            # Przekieruj do zakupu kredytów
            from handlers.payment_handler import payment_command
            
            # Utwórz sztuczny obiekt update
            fake_update = type('obj', (object,), {'effective_user': query.from_user, 'message': query.message})
            await payment_command(fake_update, context)
            return True
        except Exception as e:
            print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
            import traceback
            traceback.print_exc()
    
    elif query.data == "Kup":
        try:
            # Przekieruj do zakupu kredytów
            from handlers.credit_handler import buy_command
            
            # Utwórz sztuczny obiekt update
            fake_update = type('obj', (object,), {'effective_user': query.from_user, 'message': query.message})
            await buy_command(fake_update, context)
            return True
        except Exception as e:
            print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
            import traceback
            traceback.print_exc()

    # Obsługa nowych callbacków dla zdjęć
    elif query.data == "analyze_photo" or query.data == "translate_photo":
        # Pobierz ID zdjęcia z kontekstu
        if 'user_data' not in context.chat_data or user_id not in context.chat_data['user_data'] or 'last_photo_id' not in context.chat_data['user_data'][user_id]:
            await query.answer("Nie znaleziono zdjęcia. Wyślij je ponownie.")
            return
            
        photo_id = context.chat_data['user_data'][user_id]['last_photo_id']
        mode = "translate" if query.data == "translate_photo" else "analyze"
        
        # Pobierz koszt
        credit_cost = CREDIT_COSTS["photo"]
        if not check_user_credits(user_id, credit_cost):
            await query.answer(get_text("subscription_expired", language))
            return
        
        # Informuj o rozpoczęciu analizy
        message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=get_text("translating_image" if mode == "translate" else "analyzing_photo", language)
        )
        
        try:
            # Pobierz zdjęcie
            file = await context.bot.get_file(photo_id)
            file_bytes = await file.download_as_bytearray()
            
            # Analizuj zdjęcie
            result = await analyze_image(file_bytes, f"photo_{photo_id}.jpg", mode=mode)
            
            # Odejmij kredyty
            description = "Tłumaczenie tekstu ze zdjęcia" if mode == "translate" else "Analiza zdjęcia"
            deduct_user_credits(user_id, credit_cost, description)
            
            # Wyślij wynik
            header = "*Tłumaczenie tekstu ze zdjęcia:*\n\n" if mode == "translate" else "*Analiza zdjęcia:*\n\n"
            await message.edit_text(
                f"{header}{result}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Błąd przy analizie zdjęcia: {e}")
            await message.edit_text("Wystąpił błąd podczas analizy zdjęcia. Spróbuj ponownie.")

    elif query.data == "analyze_document" or query.data == "translate_document":
        # Pobierz ID dokumentu z kontekstu
        if ('user_data' not in context.chat_data or 
            user_id not in context.chat_data['user_data'] or 
            'last_document_id' not in context.chat_data['user_data'][user_id]):
            await query.answer("Nie znaleziono dokumentu. Wyślij go ponownie.")
            return
            
        document_id = context.chat_data['user_data'][user_id]['last_document_id']
        file_name = context.chat_data['user_data'][user_id].get('last_document_name', 'dokument')
        
        # Sprawdź czy to jest prośba o tłumaczenie PDF
        if query.data == "translate_document" and file_name.lower().endswith('.pdf'):
            # Zasymuluj aktualizację z oryginalnym plikiem PDF
            class MockDocument:
                def __init__(self, file_id, file_name):
                    self.file_id = file_id
                    self.file_name = file_name
            
            class MockMessage:
                def __init__(self, chat_id, document):
                    self.chat_id = chat_id
                    self.document = document
                    self.chat = type('obj', (object,), {'id': chat_id, 'send_action': lambda action: None})
                    
                async def reply_text(self, text):
                    return await context.bot.send_message(chat_id=self.chat_id, text=text)
            
            # Utwórz aktualizację z dokumentem
            mock_document = MockDocument(document_id, file_name)
            update.message = MockMessage(query.message.chat_id, mock_document)
            
            # Wywołaj handler PDF
            from handlers.pdf_handler import handle_pdf_translation
            await handle_pdf_translation(update, context)
            return
        
        # Obsługa standardowej analizy dokumentu
        # Pobierz koszt
        credit_cost = CREDIT_COSTS["document"]
        if not check_user_credits(user_id, credit_cost):
            await query.answer(get_text("subscription_expired", language))
            return
        
        # Informuj o rozpoczęciu analizy
        message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=get_text("analyzing_file", language)
        )
        
        try:
            # Pobierz dokument
            file = await context.bot.get_file(document_id)
            file_bytes = await file.download_as_bytearray()
            
            # Analizuj dokument
            result = await analyze_document(file_bytes, file_name)
            
            # Odejmij kredyty
            deduct_user_credits(user_id, credit_cost, f"Analiza dokumentu: {file_name}")
            
            # Wyślij wynik
            await message.edit_text(
                f"*{get_text('file_analysis', language)}:* {file_name}\n\n{result}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Błąd przy analizie dokumentu: {e}")
            await message.edit_text("Wystąpił błąd podczas analizy dokumentu. Spróbuj ponownie.")
    
    # Fallback dla nieobsłużonych callbacków
    print(f"Nieobsłużony callback: {query.data}")
    try:
        keyboard = [[InlineKeyboardButton("⬅️ Menu główne", callback_data="menu_back_main")]]
        await query.edit_message_text(
            f"Nieznany przycisk. Spróbuj ponownie później.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(f"Błąd przy wyświetlaniu komunikatu o nieobsłużonym callbacku: {e}")