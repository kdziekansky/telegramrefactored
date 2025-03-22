from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.ui_elements import credit_status_bar, info_card, section_divider, feature_badge, progress_bar
from utils.message_formatter_enhanced import format_credit_info, format_transaction_report
from utils.visual_styles import style_message, create_header, create_section, create_status_indicator
from utils.tips import get_random_tip, should_show_tip
from utils.credit_warnings import get_low_credits_notification, get_credit_recommendation
from config import BOT_NAME
from utils.user_utils import get_user_language
from utils.translations import get_text
from database.credits_client import (
    get_user_credits, add_user_credits, deduct_user_credits, 
    get_credit_packages, get_package_by_id, purchase_credits,
    get_user_credit_stats
)
from utils.credit_analytics import (
    generate_credit_usage_chart, generate_usage_breakdown_chart, 
    get_credit_usage_breakdown, predict_credit_depletion
)
import matplotlib
matplotlib.use('Agg')  # Required for operation without a graphical interface

from database.credits_client import add_stars_payment_option, get_stars_conversion_rate

async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /credits command with enhanced visual presentation
    Display information about user's credits
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    credits = get_user_credits(user_id)
    
    # Create styled header
    message = create_header("Stan kredytów", "credits")
    
    # Add credits status with visual indicators
    message += credit_status_bar(credits)
    
    # Get credit usage stats
    from database.credits_client import get_user_credit_stats
    stats = get_user_credit_stats(user_id)
    
    # Add basic stats section
    if stats:
        message += "\n\n" + create_section("Statystyki", 
            f"▪️ Łącznie zakupiono: {stats.get('total_purchased', 0)} kredytów\n"
            f"▪️ Średnie dzienne zużycie: {int(stats.get('avg_daily_usage', 0))} kredytów\n"
            f"▪️ Najdroższa operacja: {stats.get('most_expensive_operation', 'brak danych')}")
    
    # Check for credit recommendation
    recommendation = get_credit_recommendation(user_id, context)
    if recommendation:
        message += "\n\n" + create_section("Rekomendowany pakiet", 
            f"▪️ {recommendation['package_name']} - {recommendation['credits']} kredytów\n"
            f"▪️ Cena: {recommendation['price']} PLN\n"
            f"▪️ {recommendation['reason']}")
    
    # Add a tip about saving credits if appropriate
    if should_show_tip(user_id, context):
        tip = get_random_tip('credits')
        message += f"\n\n{section_divider('Porada')}\n💡 *Porada:* {tip}"
    
    # Check for low credits and add warning if needed
    low_credits_warning = get_low_credits_notification(credits)
    if low_credits_warning:
        message += f"\n\n{section_divider('Uwaga')}\n{low_credits_warning}"
    
    # Create enhanced buttons for credits
    keyboard = [
        [
            InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")
        ],
        [
            InlineKeyboardButton("💰 " + get_text("payment_methods", language, default="Metody płatności"), callback_data="payment_command"),
            InlineKeyboardButton("🔄 " + get_text("subscription_manage", language, default="Subskrypcje"), callback_data="subscription_command")
        ],
        [
            InlineKeyboardButton("📜 " + get_text("transaction_history", language, default="Historia transakcji"), callback_data="transactions_command")
        ],
        [
            InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_back_main")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /buy command with enhanced visual presentation
    Directs users to payment options
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Check if stars option is specified
    if context.args and len(context.args) > 0 and context.args[0].lower() == "stars":
        await show_stars_purchase_options(update, context)
        return
    
    # Create styled header for payment options
    message = create_header("Zakup kredytów", "credits")
    
    # Add descriptive text with visual formatting
    message += (
        "Wybierz jedną z dostępnych metod płatności, aby kupić pakiet kredytów. "
        "Kredyty są używane do wszystkich operacji w bocie, takich jak:\n\n"
        "▪️ Rozmowy z różnymi modelami AI\n"
        "▪️ Generowanie obrazów\n"
        "▪️ Analizowanie dokumentów i zdjęć\n"
        "▪️ Tłumaczenie tekstów\n\n"
        "Dostępne są różne metody płatności."
    )
    
    # Add section about subscription benefits
    message += "\n\n" + create_section("Korzyści z subskrypcji", 
        "▪️ Automatyczne odnowienie kredytów co miesiąc\n"
        "▪️ Niższy koszt kredytów\n"
        "▪️ Priorytetowa obsługa\n"
        "▪️ Dodatkowe funkcje premium")
    
    # Create enhanced buttons for payment options
    keyboard = [
        [
            InlineKeyboardButton("💳 " + get_text("credit_card", language, default="Karta płatnicza"), callback_data="payment_method_stripe"),
            InlineKeyboardButton("🔄 " + get_text("subscription", language, default="Subskrypcja"), callback_data="payment_method_stripe_subscription")
        ],
        [
            InlineKeyboardButton("⭐ " + get_text("telegram_stars", language, default="Gwiazdki Telegram"), callback_data="show_stars_options"),
            InlineKeyboardButton("🛒 " + get_text("other_methods", language, default="Inne metody"), callback_data="payment_command")
        ],
        [
            InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_back_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def handle_credit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle buttons related to credits
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    # Route to payment handler if it's a payment-related command
    if query.data == "payment_command" or query.data.startswith("payment_method_") or \
       query.data.startswith("buy_package_") or query.data == "subscription_command" or \
       query.data.startswith("cancel_subscription_") or query.data.startswith("confirm_cancel_sub_") or \
       query.data == "transactions_command":
        try:
            from handlers.payment_handler import handle_payment_callback
            result = await handle_payment_callback(update, context)
            if result:
                return True
        except Exception as e:
            print(f"Error routing to payment handler: {e}")
            import traceback
            traceback.print_exc()
    
    # Handle credits check
    if query.data == "credits_check" or query.data == "menu_credits_check":
        # Get current credit data
        credits = get_user_credits(user_id)
        credit_stats = get_user_credit_stats(user_id)
        
        # Prepare message text
        message = f"""
*{get_text('credits_management', language)}*

{get_text('current_balance', language)}: *{credits}* {get_text('credits', language)}

{get_text('total_purchased', language)}: *{credit_stats.get('total_purchased', 0)}* {get_text('credits', language)}
{get_text('total_spent', language)}: *{credit_stats.get('total_spent', 0):.2f}* PLN
{get_text('last_purchase', language)}: *{credit_stats.get('last_purchase', get_text('no_transactions', language))}*

*{get_text('credit_history', language)} ({get_text('last_10', language, default='last 10')}):*
"""
        
        if credit_stats.get('usage_history'):
            for i, transaction in enumerate(credit_stats['usage_history'], 1):
                date = transaction['date'].split('T')[0]
                if transaction['type'] in ["add", "purchase", "subscription", "subscription_renewal"]:
                    message += f"\n{i}. ➕ +{transaction['amount']} {get_text('credits', language)} ({date})"
                else:
                    message += f"\n{i}. ➖ -{transaction['amount']} {get_text('credits', language)} ({date})"
                if transaction.get('description'):
                    message += f" - {transaction['description']}"
        else:
            message += f"\n{get_text('no_transactions', language)}"
        
        # Create keyboard
        keyboard = [
            [InlineKeyboardButton(get_text("buy_more_credits", language), callback_data="menu_credits_buy")],
            [InlineKeyboardButton(get_text("back", language), callback_data="menu_section_credits")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update message
        try:
            # Check if message has caption (is a photo or other media type)
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            print(f"Error updating message: {e}")
            # Try without markdown formatting
            try:
                plain_message = message.replace("*", "")
                if hasattr(query.message, 'caption'):
                    await query.edit_message_caption(
                        caption=plain_message,
                        reply_markup=reply_markup
                    )
                else:
                    await query.edit_message_text(
                        text=plain_message,
                        reply_markup=reply_markup
                    )
            except Exception as e2:
                print(f"Second error updating message: {e2}")
        return True
    
    # Handle credit purchase options - ZMODYFIKOWANE
    if query.data == "credits_buy" or query.data == "menu_credits_buy" or query.data == "Kup":
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
            await query.message.delete()
            
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
    
    # Handle advanced credit analytics
    if query.data == "credits_stats" or query.data == "credit_advanced_analytics":
        user_id = query.from_user.id
        language = get_user_language(context, user_id)
        
        # Inform user that analysis is starting
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption="⏳ Analyzing credit usage data..."
            )
        else:
            await query.edit_message_text(
                text="⏳ Analyzing credit usage data..."
            )
        
        # Default number of days for analysis
        days = 30
        
        # Get credit depletion forecast
        depletion_info = predict_credit_depletion(user_id, days)
        
        if not depletion_info:
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption="You don't have enough credit usage history to perform analysis. Try again after performing several operations."
                )
            else:
                await query.edit_message_text(
                    text="You don't have enough credit usage history to perform analysis. Try again after performing several operations."
                )
            return True
        
        # Prepare analysis message
        message = f"📊 *{get_text('credit_analytics', language, default='Analiza wykorzystania kredytów')}*\n\n"
        message += f"{get_text('current_balance', language)}: *{depletion_info['current_balance']}* {get_text('credits', language)}\n"
        message += f"{get_text('average_daily_usage', language, default='Średnie dzienne zużycie')}: *{depletion_info['average_daily_usage']}* {get_text('credits', language)}\n"
        
        if depletion_info['days_left']:
            message += f"{get_text('predicted_depletion', language, default='Przewidywane wyczerpanie kredytów')}: {get_text('in_days', language, default='za')} *{depletion_info['days_left']}* {get_text('days', language, default='dni')} "
            message += f"({depletion_info['depletion_date']})\n\n"
        else:
            message += f"{get_text('not_enough_data', language, default='Za mało danych, aby przewidzieć wyczerpanie kredytów.')}.\n\n"
        
        # Get credit usage breakdown
        usage_breakdown = get_credit_usage_breakdown(user_id, days)
        
        if usage_breakdown:
            message += f"*{get_text('usage_breakdown', language, default='Rozkład zużycia kredytów')}:*\n"
            for category, amount in usage_breakdown.items():
                percentage = amount / sum(usage_breakdown.values()) * 100
                message += f"- {category}: *{amount}* {get_text('credits', language)} ({percentage:.1f}%)\n"
        
        # Update message with analysis
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption=message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Generate and send charts
        # Usage history chart
        usage_chart = generate_credit_usage_chart(user_id, days)
        if usage_chart:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=usage_chart,
                caption=f"📈 {get_text('usage_history_chart', language, default=f'Historia wykorzystania kredytów z ostatnich {days} dni')}"
            )
        
        # Usage breakdown chart
        breakdown_chart = generate_usage_breakdown_chart(user_id, days)
        if breakdown_chart:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=breakdown_chart,
                caption=f"📊 {get_text('usage_breakdown_chart', language, default=f'Rozkład wykorzystania kredytów z ostatnich {days} dni')}"
            )
        
        # Add back button
        keyboard = [[InlineKeyboardButton(get_text("back", language), callback_data="menu_credits_check")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update message with back button
        try:
            if hasattr(query.message, 'caption'):
                await query.edit_message_reply_markup(reply_markup=reply_markup)
            else:
                await query.message.edit_reply_markup(reply_markup=reply_markup)
        except Exception as e:
            print(f"Error updating keyboard: {e}")
        
        return True

    # Handle Telegram stars purchase options
    if query.data == "show_stars_options":
        # Get star exchange rates
        conversion_rates = get_stars_conversion_rate()
        
        # Create keyboard
        keyboard = []
        for stars, credits in conversion_rates.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"⭐ {stars} {get_text('stars', language, default='gwiazdek')} = {credits} {get_text('credits', language)}", 
                    callback_data=f"buy_stars_{stars}"
                )
            ])
        
        # Add back button - zmienione, żeby wracało do nowego interfejsu
        keyboard.append([
            InlineKeyboardButton(get_text("back", language), callback_data="menu_credits_buy")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            get_text("stars_purchase_info", language),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return True
    
    # Handle stars purchase
    if query.data.startswith("buy_stars_"):
        stars_amount = int(query.data.split("_")[2])
        
        # Get star exchange rates
        conversion_rates = get_stars_conversion_rate()
        
        # Check if this stars amount is supported
        if stars_amount not in conversion_rates:
            await query.edit_message_text(
                get_text("stars_invalid_amount", language, default="Wystąpił błąd. Nieprawidłowa liczba gwiazdek."),
                parse_mode=ParseMode.MARKDOWN
            )
            return True
        
        credits_amount = conversion_rates[stars_amount]
        
        # Add credits to user's account
        success = add_stars_payment_option(user_id, stars_amount, credits_amount)
        
        if success:
            current_credits = get_user_credits(user_id)
            await query.edit_message_text(
                get_text("stars_purchase_success", language, default=f"✅ *Zakup zakończony sukcesem!*\n\nWymieniono *{stars_amount}* gwiazdek na *{credits_amount}* kredytów\n\nAktualny stan kredytów: *{current_credits}*\n\nDziękujemy za zakup! 🎉"),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                get_text("purchase_error", language, default="Wystąpił błąd podczas realizacji płatności. Spróbuj ponownie później."),
                parse_mode=ParseMode.MARKDOWN
            )
        return True
    
    return False  # If callback not handled

async def credit_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /creditstats command with enhanced visual presentation
    Display detailed statistics on user's credits
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Show loading message
    loading_message = await update.message.reply_text(
        create_status_indicator('loading', "Analizowanie danych o kredytach...")
    )
    
    # Get user stats
    stats = get_user_credit_stats(user_id)
    
    # Create styled header
    message = create_header("Analiza kredytów", "credits")
    
    # Add current credit status with visual bar
    message += credit_status_bar(stats['credits'])
    
    # Format the date of last purchase
    last_purchase = get_text("none", language, default="Brak") 
    if stats['last_purchase']:
        if isinstance(stats['last_purchase'], str) and 'T' in stats['last_purchase']:
            last_purchase = stats['last_purchase'].split('T')[0]
        else:
            last_purchase = str(stats['last_purchase'])
    
    # Add key statistics with visual formatting
    message += "\n\n" + create_section("Kluczowe statystyki", 
        f"▪️ Łącznie zakupiono: *{stats['total_purchased']}* kredytów\n"
        f"▪️ Wydano łącznie: *{stats['total_spent']}* PLN\n"
        f"▪️ Ostatni zakup: *{last_purchase}*\n"
        f"▪️ Średnie dzienne zużycie: *{int(stats.get('avg_daily_usage', 0))}* kredytów")
    
    # Add transaction history
    if stats['usage_history']:
        message += "\n\n" + create_section("Historia transakcji", "Ostatnie operacje:")
        
        # Show last 5 transactions with categorized formatting
        for i, transaction in enumerate(stats['usage_history'][:5]):
            date = transaction['date'].split('T')[0] if isinstance(transaction['date'], str) else str(transaction['date'])
            
            if transaction['type'] in ["add", "purchase", "subscription", "subscription_renewal"]:
                message += f"\n🟢 +{transaction['amount']} kr. ({date})"
                if transaction['description']:
                    message += f" - {transaction['description']}"
            else:
                message += f"\n🔴 -{transaction['amount']} kr. ({date})"
                if transaction['description']:
                    message += f" - {transaction['description']}"
    else:
        message += "\n\n" + create_section("Historia transakcji", "Brak historii transakcji.")
    
    # Generate and send charts
    try:
        from utils.credit_analytics import generate_credit_usage_chart, generate_usage_breakdown_chart, predict_credit_depletion
        
        # Get depletion prediction
        depletion_info = predict_credit_depletion(user_id)
        if depletion_info and depletion_info['days_left']:
            message += "\n\n" + create_section("Prognoza", 
                f"▪️ Tempo zużycia: *{depletion_info['average_daily_usage']}* kredytów dziennie\n"
                f"▪️ Wyczerpanie kredytów: za *{depletion_info['days_left']}* dni\n"
                f"▪️ Przybliżona data: *{depletion_info['depletion_date']}*")
    except Exception as e:
        print(f"Error generating credit prediction: {e}")
    
    # Delete loading message
    await loading_message.delete()
    
    # Add buttons to buy credits and view payment history
    keyboard = [
        [InlineKeyboardButton("💰 " + get_text("buy_more_credits", language), callback_data="menu_credits_buy")],
        [InlineKeyboardButton("📊 " + get_text("detailed_analytics", language, default="Szczegółowa analiza"), callback_data="credit_advanced_analytics")],
        [InlineKeyboardButton("📜 " + get_text("view_payment_history", language, default="Historia płatności"), callback_data="transactions_command")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    # Generate and send visual charts in separate messages
    try:
        usage_chart = generate_credit_usage_chart(user_id)
        if usage_chart:
            chart_caption = create_header("Wykres zużycia kredytów", "credits") + \
                            "Wykres przedstawia historię salda kredytów oraz transakcje w ostatnim okresie."
            
            await update.message.reply_photo(
                photo=usage_chart,
                caption=chart_caption,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Add small delay to ensure messages are sent in correct order
        await asyncio.sleep(0.5)
        
        breakdown_chart = generate_usage_breakdown_chart(user_id)
        if breakdown_chart:
            chart_caption = create_header("Rozkład wykorzystania kredytów", "credits") + \
                            "Wykres przedstawia podział zużycia kredytów według kategorii operacji."
            
            await update.message.reply_photo(
                photo=breakdown_chart,
                caption=chart_caption,
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        print(f"Error generating credit charts: {e}")
        
async def credit_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display credit usage analysis
    Usage: /creditstats [days]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Check if number of days is specified
    days = 30  # Default 30 days
    if context.args and len(context.args) > 0:
        try:
            days = int(context.args[0])
            # Limit range
            if days < 1:
                days = 1
            elif days > 365:
                days = 365
        except ValueError:
            pass
    
    # Inform user that analysis is starting
    status_message = await update.message.reply_text(
        get_text("analyzing_credit_usage", language, default="⏳ Analizuję dane wykorzystania kredytów...")
    )
    
    # Get credit depletion forecast
    depletion_info = predict_credit_depletion(user_id, days)
    
    if not depletion_info:
        await status_message.edit_text(
            get_text("not_enough_credit_history", language, default="Nie masz wystarczającej historii użycia kredytów, aby przeprowadzić analizę. Spróbuj ponownie po wykonaniu kilku operacji."),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Prepare analysis message
    message = f"📊 *{get_text('credit_analytics', language, default='Analiza wykorzystania kredytów')}*\n\n"
    message += f"{get_text('current_balance', language)}: *{depletion_info['current_balance']}* {get_text('credits', language)}\n"
    message += f"{get_text('average_daily_usage', language, default='Średnie dzienne zużycie')}: *{depletion_info['average_daily_usage']}* {get_text('credits', language)}\n"
    
    if depletion_info['days_left']:
        message += f"{get_text('predicted_depletion', language, default='Przewidywane wyczerpanie kredytów')}: {get_text('in_days', language, default='za')} *{depletion_info['days_left']}* {get_text('days', language, default='dni')} "
        message += f"({depletion_info['depletion_date']})\n\n"
    else:
        message += f"{get_text('not_enough_data', language, default='Za mało danych, aby przewidzieć wyczerpanie kredytów.')}.\n\n"
    
    # Get credit usage breakdown
    usage_breakdown = get_credit_usage_breakdown(user_id, days)
    
    if usage_breakdown and sum(usage_breakdown.values()) > 0:
        for category, amount in usage_breakdown.items():
            percentage = amount / sum(usage_breakdown.values()) * 100
            message += f"- {category}: *{amount}* {get_text('credits', language)} ({percentage:.1f}%)\n"
    else:
        message += f"- {get_text('no_data', language, default='Brak dostępnych danych o użyciu.')}\n"
    
    # Send analysis message
    await status_message.edit_text(
        message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Generate and send usage history chart
    usage_chart = generate_credit_usage_chart(user_id, days)
    
    if usage_chart:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=usage_chart,
            caption=f"📈 {get_text('usage_history_chart', language, default=f'Historia wykorzystania kredytów z ostatnich {days} dni')}"
        )
    
    # Generate and send usage breakdown chart
    breakdown_chart = generate_usage_breakdown_chart(user_id, days)
    
    if breakdown_chart:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=breakdown_chart,
            caption=f"📊 {get_text('usage_breakdown_chart', language, default=f'Rozkład wykorzystania kredytów z ostatnich {days} dni')}"
        )

async def show_stars_purchase_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show options to purchase credits using Telegram stars
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Get conversion rate
    conversion_rates = get_stars_conversion_rate()
    
    # Create buttons for different star purchase options
    keyboard = []
    for stars, credits in conversion_rates.items():
        keyboard.append([
            InlineKeyboardButton(
                f"⭐ {stars} {get_text('stars', language, default='gwiazdek')} = {credits} {get_text('credits', language)}", 
                callback_data=f"buy_stars_{stars}"
            )
        ])
    
    # Add return button
    keyboard.append([
        InlineKeyboardButton(get_text("back_to_purchase_options", language, default="🔙 Powrót do opcji zakupu"), callback_data="buy_credits")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_text("stars_purchase_info", language, default="🌟 *Zakup kredytów za Telegram Stars* 🌟\n\nWybierz jedną z opcji poniżej, aby wymienić gwiazdki Telegram na kredyty.\nIm więcej gwiazdek wymienisz jednorazowo, tym lepszy bonus otrzymasz!\n\n⚠️ *Uwaga:* Aby dokonać zakupu gwiazdkami, wymagane jest konto Telegram Premium."),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )