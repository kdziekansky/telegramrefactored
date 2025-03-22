# utils/tips.py
"""
Module for managing usage tips and contextual help
"""
import random

# Define categories of tips
GENERAL_TIPS = [
    "Krótsze pytania zazwyczaj zużywają mniej kredytów niż długie opisy.",
    "Używaj trybu GPT-3.5 dla prostych pytań, a GPT-4 tylko dla złożonych zadań.",
    "Możesz zaoszczędzić kredyty używając /mode aby wybrać tańszy model.",
    "Pamiętaj, że możesz wrócić do poprzedniej konwersacji klikając 'Ostatnia rozmowa'.",
    "Dokładne i konkretne pytania pozwalają uzyskać lepsze odpowiedzi."
]

CREDITS_TIPS = [
    "Zaproś znajomych przez program referencyjny, aby otrzymać darmowe kredyty.",
    "Kupując większe pakiety kredytów, otrzymasz lepszy stosunek wartości do ceny.",
    "Aktywuj powiadomienia o niskim stanie kredytów, aby uniknąć niespodzianek.",
    "GPT-3.5 jest 5 razy tańszy niż GPT-4 - używaj go do prostszych zadań.",
    "Ustaw miesięczną subskrypcję, aby automatycznie doładowywać kredyty."
]

IMAGE_TIPS = [
    "Dodanie słów 'wysokiej jakości', 'fotorealistyczny' do opisu obrazu może poprawić wyniki.",
    "Im bardziej szczegółowy opis, tym lepszy obraz zostanie wygenerowany.",
    "Podaj styl artystyczny (np. 'w stylu impresjonistycznym'), aby uzyskać określony wygląd.",
    "Opisz oświetlenie i kompozycję dla bardziej profesjonalnych obrazów.",
    "Unikaj generowania wielu wariantów tego samego obrazu, aby oszczędzać kredyty."
]

DOCUMENT_TIPS = [
    "Zdjęcia z wyraźnym tekstem dają lepsze wyniki przy tłumaczeniu.",
    "Dla tłumaczenia wielu stron warto rozważyć podział dokumentu na mniejsze części.",
    "Pliki PDF są łatwiejsze do analizy niż zdjęcia tekstu.",
    "Upewnij się, że dokument jest wyraźny i dobrze zeskanowany dla najlepszych wyników.",
    "Analizowanie konkretnych stron dokumentu zamiast całości może zaoszczędzić kredyty."
]

# Tips displayed in sequence for new users
ONBOARDING_TIPS = [
    "Witaj! Zacznij od wybrania trybu czatu, który najlepiej pasuje do Twoich potrzeb.",
    "Pamiętaj, że możesz zmienić tryb czatu w dowolnym momencie używając komendy /mode.",
    "Dokumenty i zdjęcia można przesyłać bezpośrednio do analizy lub tłumaczenia.",
    "Aby wygenerować obraz, użyj komendy /image wraz z opisem obrazu.",
    "Sprawdzaj stan kredytów regularnie za pomocą /credits lub w menu głównym."
]

# Collection of all tips
ALL_TIPS = GENERAL_TIPS + CREDITS_TIPS + IMAGE_TIPS + DOCUMENT_TIPS

def get_random_tip(category=None):
    """
    Returns a random tip, optionally from a specific category
    
    Args:
        category (str, optional): Category of tips ('general', 'credits', 'image', 'document')
        
    Returns:
        str: Random tip
    """
    if category == 'general':
        return random.choice(GENERAL_TIPS)
    elif category == 'credits':
        return random.choice(CREDITS_TIPS)
    elif category == 'image':
        return random.choice(IMAGE_TIPS)
    elif category == 'document':
        return random.choice(DOCUMENT_TIPS)
    elif category == 'onboarding':
        return random.choice(ONBOARDING_TIPS)
    else:
        return random.choice(ALL_TIPS)

def should_show_tip(user_id, context, frequency=5):
    """
    Determines if a tip should be shown based on user's interaction count
    
    Args:
        user_id (int): User's ID
        context: Bot context
        frequency (int): How often to show tips (every X interactions)
        
    Returns:
        bool: Whether to show a tip
    """
    # Initialize if needed
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    if 'interaction_count' not in context.chat_data['user_data'][user_id]:
        context.chat_data['user_data'][user_id]['interaction_count'] = 0
        context.chat_data['user_data'][user_id]['tips_enabled'] = True
    
    # Increment interaction count
    context.chat_data['user_data'][user_id]['interaction_count'] += 1
    
    # Check if tips are enabled and if it's time to show one
    return (context.chat_data['user_data'][user_id]['tips_enabled'] and 
            context.chat_data['user_data'][user_id]['interaction_count'] % frequency == 0)

def toggle_tips(user_id, context, enabled=None):
    """
    Toggles or sets the tips display setting for a user
    
    Args:
        user_id (int): User's ID
        context: Bot context
        enabled (bool, optional): If provided, sets to this value; otherwise toggles
        
    Returns:
        bool: New setting value
    """
    # Initialize if needed
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    if 'tips_enabled' not in context.chat_data['user_data'][user_id]:
        context.chat_data['user_data'][user_id]['tips_enabled'] = True
    
    # Set or toggle
    if enabled is not None:
        context.chat_data['user_data'][user_id]['tips_enabled'] = enabled
    else:
        context.chat_data['user_data'][user_id]['tips_enabled'] = not context.chat_data['user_data'][user_id]['tips_enabled']
    
    return context.chat_data['user_data'][user_id]['tips_enabled']

def get_contextual_tip(category, context, user_id):
    """
    Gets a contextual tip based on user's current activity
    
    Args:
        category (str): Category of current activity
        context: Bot context
        user_id (int): User's ID
        
    Returns:
        str: Tip text or None if no tip should be shown
    """
    # Check if we should show a tip
    if not should_show_tip(user_id, context):
        return None
    
    # Get a tip from the relevant category
    if category in ['chat', 'message']:
        return get_random_tip('general')
    elif category in ['credits', 'buy']:
        return get_random_tip('credits')
    elif category == 'image':
        return get_random_tip('image')
    elif category in ['document', 'pdf', 'translation']:
        return get_random_tip('document')
    else:
        return get_random_tip()