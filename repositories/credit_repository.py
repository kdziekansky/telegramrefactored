# repositories/credit_repository.py
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import pytz
from api.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class CreditRepository:
    """Repozytorium dla operacji na kredytach użytkownika"""
    
    def __init__(self, client: SupabaseClient):
        self.client = client
        self.credits_table = "user_credits"
        self.transactions_table = "credit_transactions"
        self.packages_table = "credit_packages"
    
    async def get_user_credits(self, user_id: int) -> int:
        """Pobiera bieżący stan kredytów użytkownika"""
        try:
            result = await self.client.query(
                self.credits_table, 
                query_type="select",
                columns="credits_amount", 
                filters={"user_id": user_id}
            )
            
            if result:
                return result[0].get('credits_amount', 0)
            
            await self.init_user_credits(user_id)
            return 0
        except Exception as e:
            logger.error(f"Błąd pobierania kredytów dla użytkownika {user_id}: {e}")
            return 0
    
    async def init_user_credits(self, user_id: int) -> bool:
        """Inicjalizuje kredyty użytkownika z wartością 0"""
        try:
            credit_data = {
                'user_id': user_id,
                'credits_amount': 0,
                'total_credits_purchased': 0,
                'total_spent': 0
            }
            
            result = await self.client.query(
                self.credits_table,
                query_type="insert",
                data=credit_data
            )
            
            return bool(result)
        except Exception as e:
            logger.error(f"Błąd inicjalizacji kredytów użytkownika {user_id}: {e}")
            return False
    
    async def add_user_credits(self, user_id: int, amount: int, description: Optional[str] = None) -> bool:
        """Dodaje kredyty użytkownikowi"""
        try:
            now = datetime.now(pytz.UTC).isoformat()
            
            # Pobierz aktualną liczbę kredytów
            result = await self.client.query(
                self.credits_table,
                query_type="select", 
                columns="credits_amount",
                filters={"user_id": user_id}
            )
            
            if result:
                current_credits = result[0].get('credits_amount', 0)
                
                # Aktualizuj istniejący rekord
                await self.client.query(
                    self.credits_table,
                    query_type="update",
                    filters={"user_id": user_id},
                    data={
                        'credits_amount': current_credits + amount,
                        'total_credits_purchased': self.client.client.raw(f'total_credits_purchased + {amount}'),
                        'last_purchase_date': now
                    }
                )
            else:
                # Utwórz nowy rekord
                current_credits = 0
                await self.init_user_credits(user_id)
                await self.client.query(
                    self.credits_table,
                    query_type="update",
                    filters={"user_id": user_id},
                    data={
                        'credits_amount': amount,
                        'total_credits_purchased': amount,
                        'last_purchase_date': now
                    }
                )
            
            # Zapisz transakcję
            if amount != 0:
                await self.client.query(
                    self.transactions_table,
                    query_type="insert",
                    data={
                        'user_id': user_id,
                        'transaction_type': 'add',
                        'amount': amount,
                        'credits_before': current_credits,
                        'credits_after': current_credits + amount,
                        'description': description,
                        'created_at': now
                    }
                )
            
            return True
        except Exception as e:
            logger.error(f"Błąd dodawania kredytów użytkownikowi {user_id}: {e}")
            return False
    
    async def deduct_user_credits(self, user_id: int, amount: int, description: Optional[str] = None) -> bool:
        """Odejmuje kredyty użytkownikowi"""
        try:
            # Pobierz aktualną liczbę kredytów
            result = await self.client.query(
                self.credits_table,
                query_type="select", 
                columns="credits_amount",
                filters={"user_id": user_id}
            )
            
            if not result:
                return False
            
            current_credits = result[0].get('credits_amount', 0)
            
            # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
            if current_credits < amount:
                return False
            
            # Odejmij kredyty
            await self.client.query(
                self.credits_table,
                query_type="update",
                filters={"user_id": user_id},
                data={'credits_amount': current_credits - amount}
            )
            
            # Zapisz transakcję
            now = datetime.now(pytz.UTC).isoformat()
            await self.client.query(
                self.transactions_table,
                query_type="insert",
                data={
                    'user_id': user_id,
                    'transaction_type': 'deduct',
                    'amount': amount,
                    'credits_before': current_credits,
                    'credits_after': current_credits - amount,
                    'description': description,
                    'created_at': now
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Błąd odejmowania kredytów użytkownikowi {user_id}: {e}")
            return False
    
    async def check_user_credits(self, user_id: int, amount_needed: int) -> bool:
        """Sprawdza, czy użytkownik ma wystarczającą liczbę kredytów"""
        current_credits = await self.get_user_credits(user_id)
        return current_credits >= amount_needed
    
    async def get_credit_packages(self) -> List[Dict[str, Any]]:
        """Pobiera dostępne pakiety kredytów"""
        try:
            result = await self.client.query(
                self.packages_table,
                query_type="select",
                filters={"is_active": True},
                order_by="credits"
            )
            
            return result
        except Exception as e:
            logger.error(f"Błąd pobierania pakietów kredytów: {e}")
            return []
    
    async def get_package_by_id(self, package_id: int) -> Optional[Dict[str, Any]]:
        """Pobiera informacje o pakiecie kredytów"""
        try:
            result = await self.client.query(
                self.packages_table,
                query_type="select",
                filters={"id": package_id, "is_active": True}
            )
            
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Błąd pobierania pakietu kredytów {package_id}: {e}")
            return None
    
    async def purchase_credits(self, user_id: int, package_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Dokonuje zakupu kredytów"""
        try:
            # Pobierz informacje o pakiecie
            package = await self.get_package_by_id(package_id)
            if not package:
                return False, None
            
            # Dodaj kredyty użytkownikowi
            now = datetime.now(pytz.UTC).isoformat()
            description = f"Zakup pakietu {package['name']}"
            
            # Pobierz aktualny stan kredytów
            result = await self.client.query(
                self.credits_table,
                query_type="select", 
                columns="credits_amount",
                filters={"user_id": user_id}
            )
            
            if result:
                current_credits = result[0].get('credits_amount', 0)
                
                # Aktualizuj rekord użytkownika
                await self.client.query(
                    self.credits_table,
                    query_type="update",
                    filters={"user_id": user_id},
                    data={
                        'credits_amount': current_credits + package['credits'],
                        'total_credits_purchased': self.client.client.raw(f'total_credits_purchased + {package["credits"]}'),
                        'last_purchase_date': now,
                        'total_spent': self.client.client.raw(f'total_spent + {package["price"]}')
                    }
                )
            else:
                # Jeśli rekord nie istnieje, utwórz go
                current_credits = 0
                await self.init_user_credits(user_id)
                await self.client.query(
                    self.credits_table,
                    query_type="update",
                    filters={"user_id": user_id},
                    data={
                        'credits_amount': package['credits'],
                        'total_credits_purchased': package['credits'],
                        'last_purchase_date': now,
                        'total_spent': package['price']
                    }
                )
            
            # Zapisz transakcję
            await self.client.query(
                self.transactions_table,
                query_type="insert",
                data={
                    'user_id': user_id,
                    'transaction_type': 'purchase',
                    'amount': package['credits'],
                    'credits_before': current_credits,
                    'credits_after': current_credits + package['credits'],
                    'description': description,
                    'created_at': now
                }
            )
            
            return True, package
        except Exception as e:
            logger.error(f"Błąd zakupu kredytów: {e}")
            return False, None