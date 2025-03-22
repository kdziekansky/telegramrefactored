# utils/ui_elements.py
"""
Module for creating UI elements for better visual representation in bot messages
"""

def color_category_marker(category, text):
    """
    Adds a color category marker to a message
    
    Args:
        category (str): Category name ('chat', 'image', 'document', 'credits', 'settings')
        text (str): Message text
        
    Returns:
        str: Formatted text with color category marker
    """
    # Define category emojis and symbols
    category_symbols = {
        'chat': '💬',
        'image': '🖼️',
        'document': '📄',
        'credits': '💰',
        'settings': '⚙️',
        'help': '❓',
        'translation': '🔤',
        'analysis': '🔍',
        'history': '📚',
        'onboarding': '🚀',
        'warning': '⚠️',
        'error': '❌',
        'success': '✅',
        'tip': '💡',
    }
    
    symbol = category_symbols.get(category.lower(), '•')
    
    # Format: Symbol Category_name: Text
    formatted_text = f"{symbol} *{category.title()}*\n\n{text}"
    
    return formatted_text

def progress_bar(value, max_value, width=10, filled_char='█', empty_char='░'):
    """
    Creates a text-based progress bar
    
    Args:
        value (int/float): Current value
        max_value (int/float): Maximum value
        width (int): Width of the progress bar in characters
        filled_char (str): Character for filled section
        empty_char (str): Character for empty section
        
    Returns:
        str: Progress bar as string
    """
    if max_value <= 0:
        return empty_char * width
        
    ratio = min(1.0, value / max_value)
    filled_width = int(width * ratio)
    empty_width = width - filled_width
    
    # Create bar
    bar = filled_char * filled_width + empty_char * empty_width
    
    # Add percentage
    percentage = int(ratio * 100)
    
    return f"{bar} {percentage}%"

def credit_status_bar(credits, warning_threshold=20, critical_threshold=5):
    """
    Creates a visual representation of credit status
    
    Args:
        credits (int): Number of credits
        warning_threshold (int): Threshold for warning status
        critical_threshold (int): Threshold for critical status
        
    Returns:
        str: Formatted credit status with color indicator
    """
    if credits <= critical_threshold:
        status = "❗ *Krytycznie niski*"
        emoji = "🔴"
    elif credits <= warning_threshold:
        status = "⚠️ *Niski*"
        emoji = "🟠"
    else:
        status = "✅ *Dobry*"
        emoji = "🟢"
    
    # Max credits for display purposes
    max_display = max(100, credits * 2)
    
    bar = progress_bar(credits, max_display)
    
    return f"{emoji} *Stan kredytów:* {credits}\n{status}\n{bar}"

def info_card(title, content, category=None):
    """
    Creates a card-style information display
    
    Args:
        title (str): Card title
        content (str): Card content
        category (str, optional): Category for color coding
        
    Returns:
        str: Formatted card text
    """
    symbol = ""
    if category:
        # Define category emojis and symbols
        category_symbols = {
            'chat': '💬',
            'image': '🖼️',
            'document': '📄',
            'credits': '💰',
            'settings': '⚙️',
            'help': '❓',
            'translation': '🔤',
            'analysis': '🔍',
            'history': '📚',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅',
            'tip': '💡',
        }
        symbol = category_symbols.get(category.lower(), '')
    
    # Format: ┌─── Symbol Title ───┐
    #         │                    │
    #         │       Content      │
    #         │                    │
    #         └────────────────────┘
    
    # Using unicode box-drawing characters
    header = f"┌─── {symbol} *{title}* ───┐"
    footer = "└" + "─" * (len(header) - 2) + "┘"
    
    # Process content with proper indentation
    formatted_content = ""
    for line in content.split('\n'):
        formatted_content += f"│ {line}\n"
    
    return f"{header}\n{formatted_content}{footer}"

def cost_warning(cost, current_credits, operation_name):
    """
    Creates a warning message for credit costs
    
    Args:
        cost (int): Operation cost in credits
        current_credits (int): User's current credits
        operation_name (str): Name of the operation
        
    Returns:
        str: Formatted warning message
    """
    remaining = current_credits - cost
    
    if cost > current_credits:
        status = "❌ *Niewystarczające środki*"
        message = f"Potrzebujesz jeszcze {cost - current_credits} kredytów, aby wykonać tę operację."
    elif cost > current_credits * 0.5:
        status = "⚠️ *Wysokie zużycie*"
        message = f"Ta operacja zużyje ponad połowę Twoich dostępnych kredytów."
    else:
        status = "ℹ️ *Informacja o koszcie*"
        message = f"Po wykonaniu tej operacji pozostanie Ci {remaining} kredytów."
    
    return f"{status}\n\n*Operacja:* {operation_name}\n*Koszt:* {cost} kredytów\n*Aktualny stan:* {current_credits} kredytów\n\n{message}"

def feature_badge(feature_name, is_premium=False, cost=None):
    """
    Creates a feature badge with optional premium indicator and cost
    
    Args:
        feature_name (str): Name of the feature
        is_premium (bool): Whether this is a premium feature
        cost (int, optional): Cost in credits
        
    Returns:
        str: Formatted feature badge
    """
    premium_marker = "⭐ " if is_premium else ""
    cost_info = f" ({cost} kr.)" if cost is not None else ""
    
    return f"{premium_marker}{feature_name}{cost_info}"

def section_divider(title=None):
    """
    Creates a section divider for long messages
    
    Args:
        title (str, optional): Section title
        
    Returns:
        str: Formatted section divider
    """
    if title:
        return f"\n\n● *{title}* ●\n{'─' * (len(title) + 4)}\n"
    else:
        return "\n\n" + "─" * 20 + "\n\n"

def animated_loading(step):
    """
    Returns a frame of an animated loading indicator
    
    Args:
        step (int): Current animation step (0-3)
        
    Returns:
        str: A frame of loading animation
    """
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    return frames[step % len(frames)]

def usage_tip(tip_text):
    """
    Formats a usage tip
    
    Args:
        tip_text (str): Tip content
        
    Returns:
        str: Formatted tip
    """
    return f"💡 *Porada:* {tip_text}"