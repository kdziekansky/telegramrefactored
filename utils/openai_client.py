from services.api_service import APIService

# Utworzenie globalnej instancji
api_service = APIService()

# Funkcje kompatybilne ze starym kodem
async def chat_completion(messages, model=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await api_service.chat_completion_text(messages, model)

async def chat_completion_stream(messages, model=None):
    """Funkcja dla kompatybilności wstecznej"""
    async for chunk in api_service.chat_completion_stream(messages, model):
        yield chunk

async def generate_image_dall_e(prompt):
    """Funkcja dla kompatybilności wstecznej"""
    return await api_service.generate_image(prompt)