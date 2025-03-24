from services.api_service import APIService
from services.repository_service import RepositoryService

# Utworzenie globalnych instancji
api_service = APIService()
repository_service = RepositoryService(api_service.supabase)

# Funkcje dla kompatybilności wstecznej
async def get_user_credits(user_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.credit_repository.get_user_credits(user_id)

async def add_user_credits(user_id, amount, description=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.credit_repository.add_user_credits(user_id, amount, description)

async def deduct_user_credits(user_id, amount, description=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.credit_repository.deduct_user_credits(user_id, amount, description)