from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.credits_client import (
    get_user_credits, get_credit_packages
)
from database.payment_client import (
    get_available_payment_methods, create_payment_url, 
    get_user_subscriptions, cancel_subscription,
    get_payment_transactions
)
from handlers.menu_handler import get_user_language
from utils.translations import get_text
import logging

logger = logging.getLogger(__name__)

async def payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje komendę /payment
    Wyświetla opcje płatności dla użytkownika
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz dostępne metody płatności
    payment_methods = get_available_payment_methods(language)
    
    if not payment_methods:
        await update.message.reply_text(
            get_text("payment_methods_unavailable", language, default="Obecnie brak dostępnych metod płatności. Spróbuj ponownie później.")
        )
        return
    
    # Utwórz przyciski dla każdej metody płatności
    keyboard = []
    for method in payment_methods:
        keyboard.append([
            InlineKeyboardButton(
                method["name"], 
                callback_data=f"payment_method_{method['code']}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(
            get_text("back", language), 
            callback_data="menu_section_credits"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_text("select_payment_method", language, default="Wybierz metodę płatności:"),
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje komendę /subscription
    Wyświetla aktywne subskrypcje użytkownika
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz aktywne subskrypcje
    subscriptions = get_user_subscriptions(user_id)
    
    if not subscriptions:
        await update.message.reply_text(
            get_text("no_active_subscriptions", language, default="Nie masz aktywnych subskrypcji.")
        )
        return
    
    # Utwórz listę aktywnych subskrypcji
    message = get_text("active_subscriptions", language, default="*Aktywne subskrypcje:*\n\n")
    
    # Pobierz dane pakietów
    packages = {p['id']: p for p in get_credit_packages()}
    
    # Dodaj informacje o każdej subskrypcji
    for i, sub in enumerate(subscriptions, 1):
        package_id = sub['credit_package_id']
        package_name = packages.get(package_id, {}).get('name', 'Nieznany pakiet')
        package_credits = packages.get(package_id, {}).get('credits', 0)
        next_billing = sub['next_billing_date'].split('T')[0] if sub['next_billing_date'] else 'Nieznana'
        
        message += f"{i}. *{package_name}* - {package_credits} kredytów miesięcznie\n"
        message += f"   Następne odnowienie: {next_billing}\n\n"
    
    # Dodaj przyciski do zarządzania subskrypcjami
    keyboard = []
    for i, sub in enumerate(subscriptions, 1):
        keyboard.append([
            InlineKeyboardButton(
                get_text("cancel_subscription", language, default="Anuluj subskrypcję") + f" #{i}",
                callback_data=f"cancel_subscription_{sub['id']}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(
            get_text("back", language), 
            callback_data="payment_back_to_credits"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje callbacki związane z płatnościami
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    # Obsługa powrotu do menu głównego
    if query.data == "menu_back_main":
        from handlers.menu_handler import handle_back_to_main
        return await handle_back_to_main(update, context)
    
    # Obsługa powrotu do menu kredytów
    if query.data == "menu_section_credits":
        from handlers.menu_handler import handle_credits_section
        return await handle_credits_section(update, context)
    
    # Obsługa wyboru metody płatności
    if query.data.startswith("payment_method_"):
        payment_method_code = query.data[15:]  # Usunięcie prefiksu "payment_method_"
        
        # Sprawdź czy to subskrypcja
        is_subscription = payment_method_code == "stripe_subscription"
        
        # Pobierz pakiety kredytów
        packages = get_credit_packages()
        if not packages:
            await query.edit_message_text(
                get_text("packages_unavailable", language, default="Aktualnie brak dostępnych pakietów kredytów. Spróbuj ponownie później."),
                parse_mode=ParseMode.MARKDOWN
            )
            return True
        
        # Utwórz przyciski dla każdego pakietu
        keyboard = []
        for package in packages:
            # Dostosuj tekst przycisku w zależności od tego, czy to subskrypcja
            if is_subscription:
                button_text = f"{package['name']} - {package['credits']} {get_text('credits_monthly', language, default='kredytów miesięcznie')} ({package['price']} PLN/mies.)"
            else:
                button_text = f"{package['name']} - {package['credits']} {get_text('credits', language)} ({package['price']} PLN)"
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"buy_package_{payment_method_code}_{package['id']}"
                )
            ])
        
        # Dodaj przycisk powrotu
        keyboard.append([
            InlineKeyboardButton(
                get_text("back", language),
                callback_data="payment_command"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Dostosuj tekst wiadomości w zależności od metody płatności
        if payment_method_code in ["allegro", "russia_payment"]:
            message = get_text(f"payment_info_{payment_method_code}", language, 
                               default="Wybierz pakiet kredytów, który chcesz zakupić przez zewnętrzną metodę płatności:")
        elif is_subscription:
            message = get_text("payment_subscription_info", language, 
                              default="Wybierz pakiet kredytów, który chcesz ustawić jako miesięczną subskrypcję:")
        else:
            message = get_text("payment_package_selection", language, 
                              default="Wybierz pakiet kredytów, który chcesz zakupić:")
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # Obsługa wyboru pakietu z określoną metodą płatności
    elif query.data.startswith("buy_package_"):
        parts = query.data.split("_")
        if len(parts) >= 4:
            payment_method_code = parts[2]
            package_id = int(parts[3])
            
            # Sprawdź czy to jest subskrypcja
            is_subscription = payment_method_code == "stripe_subscription"
            
            # Utwórz URL płatności
            success, payment_url = create_payment_url(
                user_id, package_id, payment_method_code, is_subscription
            )
            
            if success and payment_url:
                # Utwórz przycisk do przejścia do płatności
                keyboard = [[
                    InlineKeyboardButton(
                        get_text("proceed_to_payment", language, default="Przejdź do płatności"),
                        url=payment_url
                    )
                ]]
                
                # Dodaj przycisk powrotu
                keyboard.append([
                    InlineKeyboardButton(
                        get_text("back", language),
                        callback_data="payment_command"
                    )
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Dostosuj wiadomość w zależności od metody płatności
                if payment_method_code in ["allegro", "russia_payment"]:
                    message = get_text(f"external_payment_instructions_{payment_method_code}", language, 
                                      default="Kliknij przycisk poniżej, aby przejść do płatności zewnętrznej. Po zakupie otrzymasz kod, który możesz aktywować za pomocą komendy /code [twój_kod].")
                elif is_subscription:
                    message = get_text("subscription_payment_instructions", language, 
                                      default="Kliknij przycisk poniżej, aby ustawić miesięczną subskrypcję. Kredyty będą dodawane automatycznie co miesiąc po pobraniu opłaty.")
                else:
                    message = get_text("payment_instructions", language, 
                                      default="Kliknij przycisk poniżej, aby przejść do płatności. Po zakończeniu transakcji kredyty zostaną automatycznie dodane do Twojego konta.")
                
                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Wyświetl błąd, jeśli nie udało się utworzyć URL płatności
                await query.edit_message_text(
                    get_text("payment_creation_error", language, default="Wystąpił błąd podczas tworzenia płatności. Spróbuj ponownie później."),
                    parse_mode=ParseMode.MARKDOWN
                )
            return True
    
    # Obsługa anulowania subskrypcji
    elif query.data.startswith("cancel_subscription_"):
        subscription_id = int(query.data.split("_")[2])
        
        # Potwierdzenie anulowania
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text("yes", language),
                    callback_data=f"confirm_cancel_sub_{subscription_id}"
                ),
                InlineKeyboardButton(
                    get_text("no", language),
                    callback_data="subscription_command"
                )
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            get_text("cancel_subscription_confirm", language, default="Czy na pewno chcesz anulować tę subskrypcję? Nie zostaniesz już obciążony opłatą w kolejnym miesiącu, ale bieżący okres rozliczeniowy pozostanie aktywny."),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # Obsługa potwierdzenia anulowania subskrypcji
    elif query.data.startswith("confirm_cancel_sub_"):
        subscription_id = int(query.data.split("_")[3])
        
        # Anuluj subskrypcję
        success = cancel_subscription(subscription_id)
        
        if success:
            await query.edit_message_text(
                get_text("subscription_cancelled", language, default="✅ Subskrypcja została anulowana. Nie będzie już automatycznie odnawiana."),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                get_text("subscription_cancel_error", language, default="❌ Wystąpił błąd podczas anulowania subskrypcji. Spróbuj ponownie później."),
                parse_mode=ParseMode.MARKDOWN
            )
        return True
    
    # Obsługa komendy powrotu do listy metod płatności
    elif query.data == "payment_command":
        # Pobierz dostępne metody płatności
        payment_methods = get_available_payment_methods(language)
        
        if not payment_methods:
            await query.edit_message_text(
                get_text("payment_methods_unavailable", language, default="Obecnie brak dostępnych metod płatności. Spróbuj ponownie później.")
            )
            return True
        
        # Utwórz przyciski dla każdej metody płatności
        keyboard = []
        for method in payment_methods:
            keyboard.append([
                InlineKeyboardButton(
                    method["name"], 
                    callback_data=f"payment_method_{method['code']}"
                )
            ])
        
        # Dodaj przycisk powrotu
        keyboard.append([
            InlineKeyboardButton(
                get_text("back", language), 
                callback_data="payment_back_to_credits"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            get_text("select_payment_method", language, default="Wybierz metodę płatności:"),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # Obsługa komendy powrotu do listy subskrypcji
    elif query.data == "subscription_command":
        # Wywołaj bezpośrednio funkcję komendy subscription
        subscriptions = get_user_subscriptions(user_id)
        
        if not subscriptions:
            await query.edit_message_text(
                get_text("no_active_subscriptions", language, default="Nie masz aktywnych subskrypcji.")
            )
            return True
        
        # Utwórz listę aktywnych subskrypcji
        message = get_text("active_subscriptions", language, default="*Aktywne subskrypcje:*\n\n")
        
        # Pobierz dane pakietów
        packages = {p['id']: p for p in get_credit_packages()}
        
        # Dodaj informacje o każdej subskrypcji
        for i, sub in enumerate(subscriptions, 1):
            package_id = sub['credit_package_id']
            package_name = packages.get(package_id, {}).get('name', 'Nieznany pakiet')
            package_credits = packages.get(package_id, {}).get('credits', 0)
            next_billing = sub['next_billing_date'].split('T')[0] if sub['next_billing_date'] else 'Nieznana'
            
            message += f"{i}. *{package_name}* - {package_credits} kredytów miesięcznie\n"
            message += f"   Następne odnowienie: {next_billing}\n\n"
        
        # Dodaj przyciski do zarządzania subskrypcjami
        keyboard = []
        for i, sub in enumerate(subscriptions, 1):
            keyboard.append([
                InlineKeyboardButton(
                    get_text("cancel_subscription", language, default="Anuluj subskrypcję") + f" #{i}",
                    callback_data=f"cancel_subscription_{sub['id']}"
                )
            ])
        
        # Dodaj przycisk powrotu
        keyboard.append([
            InlineKeyboardButton(
                get_text("back", language), 
                callback_data="payment_back_to_credits"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    return False  # Jeśli callback nie został obsłużony

async def transactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje komendę /transactions
    Wyświetla historię transakcji płatności
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz historię transakcji
    transactions = get_payment_transactions(user_id)
    
    if not transactions:
        await update.message.reply_text(
            get_text("no_payment_transactions", language, default="Nie masz żadnych transakcji płatności.")
        )
        return
    
    # Utwórz wiadomość z historią transakcji
    message = get_text("payment_transactions_history", language, default="*Historia transakcji płatności:*\n\n")
    
    for i, transaction in enumerate(transactions, 1):
        status_text = {
            'pending': get_text("transaction_status_pending", language, default="Oczekująca"),
            'completed': get_text("transaction_status_completed", language, default="Zakończona"),
            'failed': get_text("transaction_status_failed", language, default="Nieudana"),
            'cancelled': get_text("transaction_status_cancelled", language, default="Anulowana")
        }.get(transaction['status'], transaction['status'])
        
        date = transaction['created_at'].split('T')[0]
        
        message += f"{i}. *{transaction['package_name']}* - {transaction['package_credits']} {get_text('credits', language)}\n"
        message += f"   {transaction['payment_method_name']} - {transaction['amount']} PLN\n"
        message += f"   {get_text('status', language, default='Status')}: {status_text}, {get_text('date', language, default='Data')}: {date}\n\n"
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(
            get_text("back", language), 
            callback_data="payment_back_to_credits"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )