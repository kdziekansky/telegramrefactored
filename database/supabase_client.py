from services.api_service import APIService
from services.repository_service import RepositoryService

# Utworzenie globalnych instancji
api_service = APIService()
repository_service = RepositoryService(api_service.supabase)

# Zmienne dla kompatybilności wstecznej
supabase = api_service.supabase.client  # Dla bezpośredniego dostępu, jeśli potrzebne

# Funkcje dla kompatybilności wstecznej
async def get_or_create_user(user_id, username=None, first_name=None, last_name=None, language_code=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.user_repository.get_or_create(user_id, username, first_name, last_name, language_code)

async def get_active_conversation(user_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.conversation_repository.get_active_conversation(user_id)