import asyncio
import time
import random
from typing import Optional
from datetime import datetime

from logger import get_logger
from browser_utils import BrowserUtils
from microphone_handler import MicrophoneHandler
from ui_interactions import UIInteractions
from email_verification import EmailVerification
from registration_flow import RegistrationFlow
from text_recording_handler import TextRecordingHandler
from turnstile_handler import TurnstileHandler
import config

logger = get_logger('AuthHandler')

class AuthHandler(BrowserUtils):
    
    def __init__(self, email: str, password: str, db, position: int, total_accounts: int):
        super().__init__(email, db, position, total_accounts)
        self.password = password
        
        account_proxy = db.get_proxy(email)
        account_voice_config = db.get_voice_config(email)
        
        logger.info(f"Прокси для аккаунта из БД: {str(account_proxy)[:40] if account_proxy else 'Нет'}...", 
                   email=email, position=f"{position}/{total_accounts}")
        
        voice_info = f"{account_voice_config.get('voice_name', 'Unknown')} ({account_voice_config.get('voice_gender', 'Unknown')})"
        logger.info(f"Voice config для аккаунта: {voice_info}", 
                   email=email, position=f"{position}/{total_accounts}")
        
        self.microphone_handler = MicrophoneHandler(None, email, position, total_accounts)
        self.ui_interactions = UIInteractions(None, email, position, total_accounts)
        self.email_verification = EmailVerification(None, email, password, position, total_accounts)
        self.registration_flow = RegistrationFlow(None, email, position, total_accounts, db)
        self.text_recording_handler = TextRecordingHandler(None, email, position, total_accounts, account_proxy, account_voice_config)
        self.turnstile_handler = TurnstileHandler(None, email, position, total_accounts)

    def _update_page_references(self):
        self.microphone_handler.page = self.page
        self.ui_interactions.page = self.page
        self.email_verification.page = self.page
        self.registration_flow.page = self.page
        self.text_recording_handler.page = self.page
        self.turnstile_handler.page = self.page

    async def check_dashboard_and_proceed_to_text_campaign(self) -> bool:
        try:
            logger.info(f"Проверка dashboard и переход к текстовой кампании", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            current_url = self.page.url
            page_content = await self.page.content()
            
            if "/dashboard" in current_url or "dashboard" in page_content.lower():
                logger.success(f"Находимся на dashboard, переходим к текстовой кампании", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                if await self.text_recording_handler.handle_text_recording_campaign():
                    logger.success(f"Текстовая кампания выполнена успешно", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return True
                else:
                    logger.warning(f"Ошибка выполнения текстовой кампании", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return False
            else:
                logger.info(f"Не на dashboard (URL: {current_url}), пропускаем текстовую кампанию", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка проверки dashboard и выполнения текстовой кампании: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def perform_registration(self) -> bool:
        try:
            self._update_page_references()
            
            logger.info(f"ШАГ 0: Начало процесса регистрации", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if config.TWOCAPTCHA_CONFIG.get("balance_check", False) and config.TWOCAPTCHA_API_KEY:
                balance = self.turnstile_handler.cf_solver.get_balance()
                if balance is not None and balance < 1.0:
                    logger.warning(f"Низкий баланс 2captcha: ${balance}", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            logger.info(f"ШАГ 1: Закрытие модальных окон", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            await self.ui_interactions.close_modal_overlay()
            
            logger.info(f"ШАГ 2: Принятие правил пользования", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            if not await self.ui_interactions.accept_terms():
                logger.error(f"ОШИБКА НА ШАГЕ 2: Не удалось принять правила пользования", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False

            logger.info(f"ШАГ 3: Нажатие кнопки Get Started", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            if not await self.ui_interactions.click_get_started_button():
                logger.error(f"ОШИБКА НА ШАГЕ 3: Не удалось нажать кнопку Get Started", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
            await asyncio.sleep(random.uniform(2, 4))
            
            current_url = self.page.url
            logger.info(f"ШАГ 4: После Get Started попали на: {current_url}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            logger.info(f"ШАГ 5: Ввод email адреса", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            if not await self.email_verification.enter_email():
                logger.error(f"ОШИБКА НА ШАГЕ 5: Не удалось ввести email", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False

            logger.info(f"ШАГ 6: Нажатие кнопки Continue", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            if not await self.ui_interactions.click_continue_button():
                logger.error(f"ОШИБКА НА ШАГЕ 6: Не удалось нажать кнопку Continue", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            send_time = time.time()
            self.email_verification.set_email_send_time(send_time)
            send_time_str = datetime.fromtimestamp(send_time).strftime('%H:%M:%S')
            logger.info(f"Continue нажат в {send_time_str}, код отправлен (timestamp: {send_time:.0f})", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")

            logger.info(f"ШАГ 7: Получение кода из email", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            verification_code = await self.email_verification.get_verification_code_from_email()
            if not verification_code:
                logger.error(f"ОШИБКА НА ШАГЕ 7: Не удалось получить код подтверждения", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False

            logger.info(f"ШАГ 8: Ввод кода подтверждения", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            if not await self.email_verification.enter_verification_code(verification_code):
                logger.error(f"ОШИБКА НА ШАГЕ 8: Не удалось ввести код подтверждения", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False

            logger.info(f"ШАГ 9: Ожидание завершения регистрации и обработка voice profile", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            self.registration_flow.set_turnstile_handler(self.turnstile_handler)
            
            captured_requests = getattr(self.email_verification, 'captured_requests', [])
            requests_file = getattr(self.email_verification, 'requests_file', f"requests_{self.email.replace('@', '_at_').replace('.', '_')}.txt")
            
            if await self.registration_flow.wait_for_registration_completion(captured_requests, requests_file):
                logger.success(f"ВСЕ ШАГИ ВЫПОЛНЕНЫ: Регистрация выполнена успешно", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                self.db.update_account(self.email, {
                    "registered": True,
                    "last_activity": datetime.now().isoformat(),
                    "voice_profile_completed": True
                })
                
                logger.info(f"ШАГ 10: Проверка dashboard и выполнение текстовой кампании", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                if await self.check_dashboard_and_proceed_to_text_campaign():
                    logger.success(f"ВСЕ ЗАДАЧИ ВЫПОЛНЕНЫ: Регистрация и текстовая кампания завершены", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    self.db.update_account(self.email, {
                        "text_campaign_completed": True,
                        "last_activity": datetime.now().isoformat()
                    })
                    
                    return True
                else:
                    logger.warning(f"Регистрация завершена, но текстовая кампания не выполнена", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return True
                
            else:
                logger.error(f"ОШИБКА НА ШАГЕ 9: Не удалось завершить регистрацию", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Критическая ошибка регистрации: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False