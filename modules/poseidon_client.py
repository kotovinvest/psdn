import asyncio
import time
import random
from typing import Dict
from datetime import datetime

from database import Database
from logger import get_logger
from auth_handler import AuthHandler
from browser_utils import BrowserUtils
import config

logger = get_logger('PoseidonClient')

class PoseidonClient:
    
    def __init__(self, email_line: str, db: Database, position: int, total_accounts: int):
        self.email_line = email_line
        self.db = db
        self.position = position
        self.total_accounts = total_accounts
        self.session_start_time = None
        
        try:
            if ":" in email_line:
                self.email, self.password = email_line.rsplit(":", 1)
                self.login = self.email.split("@")[0] if "@" in self.email else self.email
            else:
                raise ValueError("Неверный формат email строки")
        except Exception as e:
            logger.error(f"Ошибка парсинга email: {e}", email=email_line[:20])
            raise
        
        logger.info(f"Инициализация клиента для {self.email}", 
                   email=self.email, position=f"{position}/{total_accounts}")
        
        self.account_data = self.db.get_account_data(self.email)
        
        if not self.account_data.get("email"):
            self.db.update_account(self.email, {
                "email": self.email,
                "login": self.login, 
                "password": self.password
            })
        
        self.browser_utils = None
        self.auth_handler = None
        
        logger.success(f"Клиент инициализирован успешно", 
                      email=self.email, position=f"{position}/{total_accounts}")
    
    def _setup_handlers(self):
        self.browser_utils = BrowserUtils(self.email, self.db, self.position, self.total_accounts)
        self.auth_handler = AuthHandler(self.email, self.password, self.db, self.position, self.total_accounts)
    
    def _sync_browser_objects(self):
        for handler in [self.auth_handler]:
            handler.browser = self.browser_utils.browser
            handler.page = self.browser_utils.page
    
    async def _force_cleanup_browser(self):
        try:
            logger.info(f"Принудительное закрытие браузера", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if self.browser_utils and self.browser_utils.page:
                try:
                    await self.browser_utils.page.close()
                except Exception as e:
                    logger.warning(f"Ошибка закрытия страницы: {e}", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if self.browser_utils and self.browser_utils.browser:
                try:
                    await self.browser_utils.browser.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Ошибка закрытия браузера: {e}", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            self.browser_utils = None
            logger.success(f"Браузер принудительно закрыт", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                          
        except Exception as e:
            logger.error(f"Критическая ошибка принудительного закрытия браузера: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
    
    async def perform_full_process(self) -> bool:
        try:
            self._setup_handlers()
            await self.browser_utils.setup_browser()
            self._sync_browser_objects()
            
            ip_check_success = await self.browser_utils.check_ip_address()
            if not ip_check_success:
                logger.warning(f"Не удалось проверить IP, но продолжаем", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            navigation_success = await self.browser_utils.navigate_to_site()
            if not navigation_success:
                logger.error(f"Не удалось загрузить сайт", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            logger.info(f"КЛИЕНТ ЗАПУСКАЕТ РЕГИСТРАЦИЮ С ПРАВИЛАМИ И ТЕКСТОВУЮ КАМПАНИЮ", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            registration_success = await self.auth_handler.perform_registration()
            if not registration_success:
                logger.error(f"Не удалось выполнить полный процесс регистрации и текстовых кампаний", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            # Обновляем статистику в базе данных
            self.db.update_account(self.email, {
                "last_activity": datetime.now().isoformat(),
                "registration_completed": True,
                "text_campaign_completed": True
            })
            self.db.update_stats(self.email, "total_sessions")
            self.db.update_stats(self.email, "text_campaigns_completed")
            
            logger.success(f"АККАУНТ УСПЕШНО ОБРАБОТАН! Регистрация + текстовая кампания выполнены!", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки аккаунта: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            import traceback
            logger.error(f"Трейсбек: {traceback.format_exc()}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
        
        finally:
            await self._force_cleanup_browser()
    
    def process_account(self) -> bool:
        logger.info(f"Начало обработки аккаунта", 
                   email=self.email, position=f"{self.position}/{self.total_accounts}")
        
        async def _process():
            try:
                return await self.perform_full_process()
            finally:
                await self._force_cleanup_browser()
        
        try:
            return asyncio.run(_process())
        except Exception as e:
            logger.error(f"Критическая ошибка процесса: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
        finally:
            try:
                if self.browser_utils:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._force_cleanup_browser())
                    loop.close()
            except Exception as e:
                logger.warning(f"Ошибка финального закрытия браузера: {e}", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
    
    def get_account_summary(self) -> Dict:
        account_data = self.db.get_account_data(self.email)
        
        return {
            "email": self.email,
            "registered": account_data.get("registered", False),
            "registration_completed": account_data.get("registration_completed", False),
            "text_campaign_completed": account_data.get("text_campaign_completed", False),
            "voice_profile_completed": account_data.get("voice_profile_completed", False),
            "last_activity": account_data.get("last_activity", ""),
            "stats": account_data.get("stats", {}),
            "status": "завершено" if account_data.get("text_campaign_completed") else "частично"
        }