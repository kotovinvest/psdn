import asyncio
import time
import random
import os
import json
import re
from typing import Optional, Dict
from datetime import datetime
from utils.logger import get_logger
from utils.email_manager import EmailManager

logger = get_logger('EmailVerification')

class EmailVerification:
    
    def __init__(self, page, email, password, position, total_accounts):
        self.page = page
        self.email = email
        self.password = password
        self.position = position
        self.total_accounts = total_accounts
        self.email_send_time = None
        self.captured_requests = []
        self.captured_responses = []
        self.requests_dir = None
        self.requests_file = None
        self.session_id = None
        self.voice_phrase = None
        self.turnstile_tokens = []
        self.cf_token_for_headers = None

    def set_cf_token_for_headers(self, cf_token: str):
        """Установить CF токен для добавления в заголовки HTTP запросов"""
        try:
            self.cf_token_for_headers = cf_token
            logger.success(f"CF токен сохранен для использования в заголовках: {cf_token[:50]}...",
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
        except Exception as e:
            logger.error(f"Ошибка сохранения CF токена: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")

    def get_cf_token_for_headers(self) -> Optional[str]:
        """Получить сохраненный CF токен для заголовков"""
        return getattr(self, 'cf_token_for_headers', None)

    def setup_session_directory(self):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_email = self.email.replace('@', '_at_').replace('.', '_')
            self.session_id = f"{safe_email}_{timestamp}_{self.position}"
            
            self.requests_dir = os.path.join('captured_requests', self.session_id)
            os.makedirs(self.requests_dir, exist_ok=True)
            
            self.requests_file = os.path.join(self.requests_dir, 'requests_log.txt')
            
            logger.info(f"Создана директория сессии: {self.requests_dir}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
        except Exception as e:
            logger.error(f"Ошибка создания директории сессии: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")

    def extract_voice_phrase_from_response(self, response_text: str) -> Optional[str]:
        try:
            if 'voice_phrase' in response_text:
                data = json.loads(response_text)
                voice_phrase = data.get('voice_phrase', '')
                if voice_phrase:
                    logger.success(f"Извлечена voice_phrase: {voice_phrase}", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    self.voice_phrase = voice_phrase
                    
                    phrase_file = os.path.join(self.requests_dir, 'voice_phrase.txt')
                    with open(phrase_file, 'w', encoding='utf-8') as f:
                        f.write(f"Voice Phrase: {voice_phrase}\n")
                        f.write(f"Extracted at: {datetime.now().isoformat()}\n")
                    
                    return voice_phrase
        except Exception as e:
            logger.warning(f"Ошибка извлечения voice_phrase: {e}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
        return None

    def extract_turnstile_tokens(self, response_text: str, url: str):
        try:
            cf_patterns = [
                r'"cf-turnstile-token":\s*"([^"]+)"',
                r'cf-turnstile-response["\']?\s*:\s*["\']([^"\']+)["\']',
                r'turnstile["\']?\s*:\s*["\']([^"\']+)["\']',
                r'cf_turnstile["\']?\s*:\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in cf_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                for match in matches:
                    if len(match) > 50 and match not in self.turnstile_tokens:
                        self.turnstile_tokens.append(match)
                        logger.success(f"Найден CF токен: {match[:50]}... из {url}", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        
                        tokens_file = os.path.join(self.requests_dir, 'cf_tokens.txt')
                        with open(tokens_file, 'a', encoding='utf-8') as f:
                            f.write(f"{datetime.now().isoformat()} | {url} | {match}\n")
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения CF токенов: {e}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")

    def get_latest_cf_token(self) -> Optional[str]:
        if self.cf_token_for_headers:
            logger.info(f"Используем CF токен для заголовков: {self.cf_token_for_headers[:50]}...", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            return self.cf_token_for_headers
        
        if self.turnstile_tokens:
            latest_token = self.turnstile_tokens[-1]
            logger.info(f"Используем последний CF токен: {latest_token[:50]}...", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            return latest_token
        return None

    def save_request_data(self, request_data: Dict, request_id: int):
        try:
            request_file = os.path.join(self.requests_dir, f'request_{request_id:04d}.json')
            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Ошибка сохранения данных запроса: {e}")

    def save_response_data(self, response_data: Dict, request_id: int):
        try:
            response_file = os.path.join(self.requests_dir, f'response_{request_id:04d}.json')
            with open(response_file, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Ошибка сохранения данных ответа: {e}")

    async def enter_email(self) -> bool:
        try:
            logger.info(f"Ввод email адреса", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(2, 3))
            
            email_selectors = [
                '#email_field',
                'input[type="email"]',
                'input[placeholder*="Enter your email"]',
                'input[autocomplete="email"]',
                'input.input[type="email"]',
                'input[id*="email"]',
                'input[name*="email"]'
            ]
            
            for attempt in range(3):
                logger.info(f"Попытка ввода email #{attempt + 1}", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                for selector in email_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=3000)
                        if element:
                            is_visible = await element.is_visible()
                            is_enabled = await element.is_enabled()
                            
                            if is_visible and is_enabled:
                                logger.info(f"Найдено поле email: {selector}", 
                                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                                
                                try:
                                    await element.wait_for_element_state("stable", timeout=3000)
                                    
                                    box = await element.bounding_box()
                                    if box:
                                        center_x = box["x"] + box["width"] / 2
                                        center_y = box["y"] + box["height"] / 2
                                        await self.page.mouse.click(center_x, center_y)
                                        await asyncio.sleep(0.5)
                                    
                                    await element.fill('')
                                    await asyncio.sleep(0.2)
                                    
                                    await element.type(self.email, delay=50)
                                    await asyncio.sleep(0.5)
                                    
                                    current_value = await element.input_value()
                                    if current_value == self.email:
                                        logger.success(f"Email успешно введен через {selector}", 
                                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                                        return True
                                    else:
                                        logger.warning(f"Email не совпадает: введен '{current_value}', ожидался '{self.email}'", 
                                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                                        
                                except Exception as click_error:
                                    logger.warning(f"Ошибка клика по полю {selector}: {click_error}")
                                    continue
                                    
                    except Exception as selector_error:
                        logger.warning(f"Селектор {selector} не сработал: {selector_error}")
                        continue
                
                if attempt < 2:
                    await asyncio.sleep(2)
            
            logger.error(f"Поле email не найдено после всех попыток", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка ввода email: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def get_verification_code_from_email(self) -> Optional[str]:
        try:
            logger.info(f"Получение кода подтверждения из email", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not self.email_send_time:
                self.email_send_time = time.time()
            
            email_manager = EmailManager(self.email, self.password)
            verification_code = email_manager.get_verification_code(self.email_send_time, max_wait_time=120)
            
            if verification_code:
                logger.success(f"Получен код подтверждения: {verification_code}", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                try:
                    if self.requests_dir and os.path.exists(self.requests_dir):
                        code_file = os.path.join(self.requests_dir, 'verification_code.txt')
                        with open(code_file, 'w', encoding='utf-8') as f:
                            f.write(f"Verification Code: {verification_code}\n")
                            f.write(f"Received at: {datetime.now().isoformat()}\n")
                except Exception as save_error:
                    logger.warning(f"Не удалось сохранить код в файл: {save_error}")
                
                return verification_code
            else:
                logger.warning(f"Код подтверждения не найден", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения кода подтверждения: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    async def setup_request_interception(self):
        try:
            logger.info(f"Начинаем перехват HTTP запросов", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            self.setup_session_directory()
            
            async def capture_request(request):
                try:
                    request_id = len(self.captured_requests) + 1
                    
                    request_data = {
                        "id": request_id,
                        "timestamp": datetime.now().isoformat(),
                        "url": request.url,
                        "method": request.method,
                        "headers": dict(request.headers),
                        "post_data": request.post_data
                    }
                    
                    self.captured_requests.append(request_data)
                    self.save_request_data(request_data, request_id)
                    
                    with open(self.requests_file, "a", encoding="utf-8") as f:
                        f.write(f"\n--- ЗАПРОС {request_id} [{datetime.now().strftime('%H:%M:%S')}] ---\n")
                        f.write(f"URL: {request.url}\n")
                        f.write(f"Method: {request.method}\n")
                        f.write(f"Headers: {json.dumps(dict(request.headers), indent=2, ensure_ascii=False)}\n")
                        if request.post_data:
                            f.write(f"POST Data: {request.post_data}\n")
                        f.write("=" * 80 + "\n")
                        
                except Exception as e:
                    logger.warning(f"Ошибка перехвата запроса: {e}")
            
            async def capture_response(response):
                try:
                    response_text = ""
                    content_type = response.headers.get('content-type', '')
                    
                    try:
                        if 'json' in content_type.lower() or 'text' in content_type.lower():
                            response_text = await response.text()
                        else:
                            response_text = f"Binary content ({content_type})"
                    except:
                        response_text = "Не удалось получить текст ответа"
                    
                    response_id = len(self.captured_responses) + 1
                    
                    response_data = {
                        "id": response_id,
                        "timestamp": datetime.now().isoformat(),
                        "url": response.url,
                        "status": response.status,
                        "headers": dict(response.headers),
                        "content": response_text[:5000] if len(response_text) > 5000 else response_text
                    }
                    
                    self.captured_responses.append(response_data)
                    self.save_response_data(response_data, response_id)
                    
                    if 'poseidon' in response.url.lower() and response.status == 200:
                        self.extract_voice_phrase_from_response(response_text)
                        self.extract_turnstile_tokens(response_text, response.url)
                    
                    with open(self.requests_file, "a", encoding="utf-8") as f:
                        f.write(f"\n--- ОТВЕТ {response_id} [{datetime.now().strftime('%H:%M:%S')}] ---\n")
                        f.write(f"URL: {response.url}\n")
                        f.write(f"Status: {response.status}\n")
                        f.write(f"Headers: {json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}\n")
                        f.write(f"Response: {response_text[:1000]}{'...' if len(response_text) > 1000 else ''}\n")
                        f.write("=" * 80 + "\n")
                        
                except Exception as e:
                    logger.warning(f"Ошибка перехвата ответа: {e}")
            
            with open(self.requests_file, "w", encoding="utf-8") as f:
                f.write(f"ПЕРЕХВАТ ЗАПРОСОВ ДЛЯ {self.email}\n")
                f.write(f"Сессия: {self.session_id}\n")
                f.write(f"Начало: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n")
            
            self.page.on("request", capture_request)
            self.page.on("response", capture_response)
            
            logger.success(f"Перехват запросов настроен, сохранение в: {self.requests_dir}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            
        except Exception as e:
            logger.error(f"Ошибка настройки перехвата запросов: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")

    async def enter_verification_code(self, code: str) -> bool:
        try:
            logger.info(f"Ввод кода подтверждения: {code}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await self.setup_request_interception()
            
            await asyncio.sleep(random.uniform(1, 2))
            
            for i, digit in enumerate(code):
                try:
                    input_selector = f'input.pin-input__input[data-testid="{i}"]'
                    element = await self.page.wait_for_selector(input_selector, timeout=5000)
                    
                    if element:
                        await element.click()
                        await asyncio.sleep(0.1)
                        await element.type(digit, delay=100)
                        await asyncio.sleep(0.2)
                except Exception as e:
                    logger.warning(f"Ошибка ввода цифры {i}: {e}")
                    continue
            
            logger.success(f"Код подтверждения введен", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            logger.info(f"Перехват запросов активен, сохраняем в {self.requests_dir}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка ввода кода подтверждения: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    def set_email_send_time(self, timestamp):
        self.email_send_time = timestamp

    def get_voice_phrase(self) -> Optional[str]:
        return self.voice_phrase

    def get_session_directory(self) -> Optional[str]:
        return self.requests_dir

    def save_session_summary(self):
        try:
            if not self.requests_dir:
                return
                
            summary_file = os.path.join(self.requests_dir, 'session_summary.json')
            summary = {
                "email": self.email,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "requests_count": len(self.captured_requests),
                "responses_count": len(self.captured_responses),
                "voice_phrase": self.voice_phrase,
                "cf_tokens_count": len(self.turnstile_tokens),
                "cf_tokens": self.turnstile_tokens[-5:] if self.turnstile_tokens else [],
                "cf_token_for_headers": self.cf_token_for_headers[:50] + "..." if self.cf_token_for_headers else None
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Сохранена сводка сессии: {summary_file}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения сводки сессии: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")