# utils/credit_warnings.py
"""
Module for credit-related warnings and notifications
"""

def check_operation_cost(user_id, cost, current_credits, operation_name, context):
    """
    Checks if an operation cost is acceptable and returns appropriate warning level
    
    Args:
        user_id (int): User ID
        cost (int): Operation cost in credits
        current_credits (int): User's current credits
        operation_name (str): Name of the operation
        context: Bot context for storing warning levels
        
    Returns:
        dict: Warning information with keys:
            - level: 'none', 'info', 'warning', 'critical'
            - message: Warning message
            - require_confirmation: Whether to require confirmation
    """
    # Initialize user data if needed
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    # Calculate remaining credits after operation
    remaining = current_credits - cost
    
    # Determine warning level
    if cost > current_credits:
        level = 'critical'
        message = f"❌ Niewystarczające kredyty. Potrzebujesz jeszcze {cost - current_credits} kredytów, aby wykonać tę operację."
        require_confirmation = False  # No need for confirmation if operation can't proceed
    elif cost >= current_credits * 0.7:
        level = 'critical'
        message = f"⚠️ Ta operacja zużyje aż {cost} z {current_credits} dostępnych kredytów ({int(cost/current_credits*100)}%)."
        require_confirmation = True
    elif cost >= current_credits * 0.5:
        level = 'warning'
        message = f"⚠️ Ta operacja zużyje ponad połowę Twoich dostępnych kredytów ({cost} z {current_credits})."
        require_confirmation = True
    elif cost >= 5:
        level = 'info'
        message = f"ℹ️ Koszt operacji: {cost} kredytów. Pozostanie: {remaining} kredytów."
        # Check if we've shown info for this operation type recently
        last_warning = context.chat_data['user_data'][user_id].get('last_cost_warning', {})
        if last_warning.get('operation') == operation_name and last_warning.get('count', 0) > 2:
            require_confirmation = False  # Don't require confirmation if we've shown it multiple times
        else:
            require_confirmation = True
    else:
        level = 'none'
        message = f"Koszt operacji: {cost} kredytów"
        require_confirmation = False
    
    # Update last warning information
    if level != 'none':
        if 'last_cost_warning' not in context.chat_data['user_data'][user_id]:
            context.chat_data['user_data'][user_id]['last_cost_warning'] = {}
        
        last_warning = context.chat_data['user_data'][user_id]['last_cost_warning']
        if last_warning.get('operation') == operation_name:
            last_warning['count'] = last_warning.get('count', 0) + 1
        else:
            last_warning['operation'] = operation_name
            last_warning['count'] = 1
    
    return {
        'level': level,
        'message': message,
        'require_confirmation': require_confirmation
    }

def get_low_credits_notification(credits, threshold=10):
    """
    Returns a notification message for low credits if credits are below threshold
    
    Args:
        credits (int): Current credits
        threshold (int): Threshold for low credits warning
        
    Returns:
        str or None: Notification message or None if credits are above threshold
    """
    if credits <= 3:
        return "🔴 *Krytycznie niski stan kredytów!* Dodaj kredyty, aby kontynuować korzystanie z bota."
    elif credits <= threshold:
        return f"🟠 *Niski stan kredytów:* Masz tylko {credits} kredytów. Rozważ zakup pakietu, aby uniknąć przerwy w korzystaniu z bota."
    else:
        return None

def format_credit_usage_report(operation, cost, credits_before, credits_after):
    """
    Formats a credit usage report after an operation
    
    Args:
        operation (str): Operation description
        cost (int): Operation cost
        credits_before (int): Credits before operation
        credits_after (int): Credits after operation
        
    Returns:
        str: Formatted credit usage report
    """
    return f"*📊 Raport użycia kredytów:*\n\n▪️ Operacja: {operation}\n▪️ Koszt: {cost} kredytów\n▪️ Pozostało: {credits_after} kredytów"

def get_credit_recommendation(user_id, context):
    """
    Analyzes user's credit usage pattern and recommends a package
    
    Args:
        user_id (int): User ID
        context: Bot context
        
    Returns:
        dict or None: Recommendation with package_id and reason, or None if no recommendation
    """
    # Get credit usage history from context or database
    from database.credits_client import get_user_credit_stats
    stats = get_user_credit_stats(user_id)
    
    if not stats or not stats.get('usage_history'):
        return None
    
    # Calculate average daily usage over the last week or available period
    history = stats.get('usage_history', [])
    total_usage = sum(transaction['amount'] for transaction in history 
                     if transaction['type'] == 'deduct')
    
    if total_usage == 0:
        return None
    
    # Estimate days of data
    if len(history) >= 7:
        days = 7
    else:
        days = max(1, len(history) // 2)  # Rough estimate
    
    daily_usage = total_usage / days
    
    # Get available packages
    from config import CREDIT_PACKAGES
    
    # Find the best package based on usage
    monthly_usage = daily_usage * 30
    
    recommended_package = None
    for package in CREDIT_PACKAGES:
        if package['credits'] >= monthly_usage:
            if recommended_package is None or package['credits'] < recommended_package['credits']:
                recommended_package = package
    
    if recommended_package:
        days_coverage = recommended_package['credits'] / daily_usage
        return {
            'package_id': recommended_package['id'],
            'package_name': recommended_package['name'],
            'credits': recommended_package['credits'],
            'price': recommended_package['price'],
            'days_coverage': int(days_coverage),
            'reason': f"Na podstawie Twojego zużycia ({int(daily_usage)} kredytów dziennie), "
                      f"ten pakiet wystarczy na około {int(days_coverage)} dni."
        }
    
    return None