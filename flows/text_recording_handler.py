import asyncio
import json
import random
import time
import hashlib
import requests
from typing import Optional, Dict, List
from utils.logger import get_logger
from utils.token_manager import TokenManager
from flows.campaign_manager import CampaignManager
from utils import config

logger = get_logger('TextRecordingHandler')

class TextRecordingHandler:
    
    def __init__(self, page, email, position, total_accounts, proxy=None, voice_config=None):
        self.page = page
        self.email = email
        self.position = position
        self.total_accounts = total_accounts
        self.proxy = proxy
        self.voice_config = voice_config or {}
        self.current_campaign_id = None
        self.current_language_code = None
        self.script_assignment_id = None
        self.script_content = None
        
        self.audio_generator = AudioGenerator(email, position, total_accounts, proxy, voice_config)
        self.token_manager = TokenManager(page, email, position, total_accounts)
        self.campaign_manager = CampaignManager(email, position, total_accounts)

    def update_proxy(self, proxy):
        self.proxy = proxy
        self.audio_generator.proxy = proxy

    def update_page(self, page):
        self.page = page
        self.token_manager.page = page

    def calculate_sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def upload_file_to_presigned_url(self, presigned_url: str, audio_data: bytes, content_type: str) -> bool:
        try:
            logger.info(f"Загрузка файла на presigned URL",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            headers = {
                'Content-Type': content_type
            }
            
            response = requests.put(presigned_url, data=audio_data, headers=headers, timeout=60)
            
            if response.status_code in [200, 204]:
                logger.success(f"Файл загружен успешно",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            else:
                logger.error(f"Ошибка загрузки файла: {response.status_code} - {response.text}",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def register_file_in_system(self, object_key: str, file_name: str, file_id: str, 
                               filesize: int, sha256_hash: str, content_type: str, turnstile_token: str = None) -> bool:
        try:
            logger.info(f"Регистрация файла в системе",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            dynamic_headers = await self.extract_dynamic_headers_from_browser()
            if not dynamic_headers:
                logger.error(f"Не удалось получить динамические заголовки",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            url = "https://poseidon-depin-server.storyapis.com/files"
            
            data = {
                "campaign_id": self.current_campaign_id,
                "content_type": content_type,
                "file_name": file_name,
                "filesize": filesize,
                "object_key": object_key,
                "sha256_hash": sha256_hash,
                "virtual_id": file_id
            }
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': dynamic_headers.get('Accept-Language', 'fi'),
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Content-Type': 'application/json',
                'Origin': 'https://app.psdn.ai',
                'Referer': 'https://app.psdn.ai/',
                'sec-ch-ua': dynamic_headers.get('sec-ch-ua', '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'),
                'sec-ch-ua-mobile': dynamic_headers.get('sec-ch-ua-mobile', '?0'),
                'sec-ch-ua-platform': dynamic_headers.get('sec-ch-ua-platform', '"Windows"'),
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'priority': 'u=1, i',
                'User-Agent': dynamic_headers.get('User-Agent', '')
            }
            
            auth_token = self.token_manager.get_token()
            if auth_token:
                headers['authorization'] = f'Bearer {auth_token}'
            
            if turnstile_token:
                headers['cf-turnstile-token'] = turnstile_token
                logger.info(f"Добавлен cf-turnstile-token в заголовки для регистрации файла",
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            response = await self.make_request_with_retry(url, headers, "POST", data)
            
            if response.status == 200:
                result = await response.json()
                points_awarded = result.get('points_awarded', 0)
                logger.success(f"Файл зарегистрирован! Получено {points_awarded} очков",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            else:
                response_text = await response.text()
                logger.error(f"Ошибка регистрации файла: {response.status} - {response_text[:200]}...",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка регистрации файла: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def make_request_with_retry(self, url: str, headers: dict, method: str = "GET", data: dict = None, max_retries: int = 3):
        try:
            for attempt in range(max_retries):
                try:
                    logger.info(f"Попытка {attempt + 1}/{max_retries}: {method} {url}",
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    if method.upper() == "GET":
                        response = await self.page.request.get(url, headers=headers, timeout=60000)
                    elif method.upper() == "POST":
                        response = await self.page.request.post(url, headers=headers, data=data, timeout=60000)
                    else:
                        raise ValueError(f"Неподдерживаемый метод: {method}")
                    
                    return response
                    
                except Exception as e:
                    if "timed out" in str(e).lower():
                        logger.warning(f"Таймаут на попытке {attempt + 1}: {e}",
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5
                            await asyncio.sleep(wait_time)
                            continue
                    else:
                        logger.error(f"Ошибка запроса на попытке {attempt + 1}: {e}",
                                    email=self.email, position=f"{self.position}/{self.total_accounts}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)
                            continue
                    
                    if attempt == max_retries - 1:
                        raise e
            
        except Exception as e:
            logger.error(f"Все попытки исчерпаны: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            raise e

    async def get_presigned_url(self, file_name: str, content_type: str, turnstile_token: str = None) -> Optional[Dict]:
        try:
            logger.info(f"Получение presigned URL для файла: {file_name}",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not self.script_assignment_id:
                logger.error(f"Нет assignment_id",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
            
            dynamic_headers = await self.extract_dynamic_headers_from_browser()
            if not dynamic_headers:
                logger.error(f"Не удалось получить динамические заголовки",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
            
            url = f"https://poseidon-depin-server.storyapis.com/files/uploads/{self.current_campaign_id}"
            
            data = {
                "content_type": content_type,
                "file_name": file_name,
                "script_assignment_id": self.script_assignment_id
            }
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': dynamic_headers.get('Accept-Language', 'fi'),
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Content-Type': 'application/json',
                'Origin': 'https://app.psdn.ai',
                'Referer': 'https://app.psdn.ai/',
                'sec-ch-ua': dynamic_headers.get('sec-ch-ua', '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'),
                'sec-ch-ua-mobile': dynamic_headers.get('sec-ch-ua-mobile', '?0'),
                'sec-ch-ua-platform': dynamic_headers.get('sec-ch-ua-platform', '"Windows"'),
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'priority': 'u=1, i',
                'User-Agent': dynamic_headers.get('User-Agent', '')
            }
            
            auth_token = self.token_manager.get_token()
            if auth_token:
                headers['authorization'] = f'Bearer {auth_token}'
            
            if turnstile_token:
                headers['cf-turnstile-token'] = turnstile_token
                logger.info(f"Добавлен cf-turnstile-token в заголовки",
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            else:
                logger.info(f"CF токен не найден, пробуем получение presigned URL БЕЗ CF токена",
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            response = await self.make_request_with_retry(url, headers, "POST", data)
            
            if response.status == 200:
                result = await response.json()
                logger.success(f"Получен presigned URL",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return result
            else:
                response_text = await response.text()
                logger.error(f"Ошибка получения presigned URL: {response.status} - {response_text[:200]}...",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения presigned URL: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    async def get_turnstile_token_from_page(self) -> Optional[str]:
        try:
            logger.info(f"Получение Turnstile токена с текущей страницы",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(3)
            
            turnstile_token = await self.page.evaluate('''
                () => {
                    try {
                        const turnstileInput = document.querySelector('input[name="cf-turnstile-response"]');
                        if (turnstileInput && turnstileInput.value) {
                            console.log('Found turnstile token in input:', turnstileInput.value.substring(0, 50));
                            return turnstileInput.value;
                        }
                        
                        if (window.turnstile && typeof window.turnstile.getResponse === 'function') {
                            const response = window.turnstile.getResponse();
                            if (response) {
                                console.log('Found turnstile token via API:', response.substring(0, 50));
                                return response;
                            }
                        }
                        
                        const turnstileWidgets = document.querySelectorAll('[data-sitekey]');
                        for (let widget of turnstileWidgets) {
                            const input = widget.querySelector('input[name="cf-turnstile-response"]');
                            if (input && input.value) {
                                console.log('Found turnstile token in widget:', input.value.substring(0, 50));
                                return input.value;
                            }
                        }
                        
                        if (window.cf && window.cf.turnstile) {
                            console.log('Found cf.turnstile object:', window.cf.turnstile);
                            return window.cf.turnstile;
                        }
                        
                        const iframes = document.querySelectorAll('iframe');
                        for (let iframe of iframes) {
                            try {
                                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                if (iframeDoc) {
                                    const input = iframeDoc.querySelector('input[name="cf-turnstile-response"]');
                                    if (input && input.value) {
                                        console.log('Found turnstile token in iframe:', input.value.substring(0, 50));
                                        return input.value;
                                    }
                                }
                            } catch (e) {
                            }
                        }
                        
                        console.log('No turnstile token found');
                        return null;
                    } catch (error) {
                        console.error('Error getting turnstile token:', error);
                        return null;
                    }
                }
            ''')
            
            if turnstile_token:
                logger.success(f"Turnstile токен получен с страницы: {turnstile_token[:50]}...",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return turnstile_token
            else:
                logger.warning(f"Turnstile токен не найден на странице",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения Turnstile токена: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    async def get_script_assignment_via_api(self) -> Optional[Dict]:
        try:
            logger.info(f"Получение задания через API",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            dynamic_headers = await self.extract_dynamic_headers_from_browser()
            if not dynamic_headers:
                logger.error(f"Не удалось получить динамические заголовки",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
            
            url = f"https://poseidon-depin-server.storyapis.com/scripts/next?language_code={self.current_language_code}&campaign_id={self.current_campaign_id}"
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': dynamic_headers.get('Accept-Language', 'fi'),
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Referer': 'https://app.psdn.ai/',
                'sec-ch-ua': dynamic_headers.get('sec-ch-ua', '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'),
                'sec-ch-ua-mobile': dynamic_headers.get('sec-ch-ua-mobile', '?0'),
                'sec-ch-ua-platform': dynamic_headers.get('sec-ch-ua-platform', '"Windows"'),
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'User-Agent': dynamic_headers.get('User-Agent', '')
            }
            
            auth_token = self.token_manager.get_token()
            if auth_token:
                headers['authorization'] = f'Bearer {auth_token}'
            
            response = await self.make_request_with_retry(url, headers, "GET")
            
            if response.status == 200:
                result = await response.json()
                assignment_id = result.get('assignment_id')
                script_content = result.get('script', {}).get('content')
                
                if assignment_id:
                    logger.success(f"Получен assignment_id: {assignment_id}",
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    self.script_assignment_id = assignment_id
                    
                    if script_content:
                        logger.success(f"Получен текст скрипта ({len(script_content)} символов): {script_content[:100]}...",
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        self.script_content = script_content
                    
                    return result
                else:
                    logger.error(f"assignment_id не найден в ответе API",
                                email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return None
            else:
                response_text = await response.text()
                logger.error(f"Ошибка получения задания: {response.status} - {response_text[:200]}...",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения задания через API: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    async def click_im_ready_button(self) -> bool:
        try:
            logger.info(f"Поиск кнопки I'm ready!",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(2, 4))
            
            im_ready_selectors = [
                'button:has-text("I\'m ready!")',
                'button.inline-flex.items-center.justify-center:has-text("I\'m ready!")',
                'button[class*="cursor-pointer"]:has-text("I\'m ready!")',
                'button.rounded-full:has-text("I\'m ready!")',
                'button:contains("I\'m ready!")',
                'button[type="button"]:has-text("I\'m ready!")',
                'button:has-text("I\'m ready")',
                'button.bg-\\[\\#ececec\\]:has-text("I\'m ready!")'
            ]
            
            for attempt in range(5):
                logger.info(f"Попытка #{attempt + 1} поиска I'm ready!",
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                for selector in im_ready_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=5000)
                        if element and await element.is_visible():
                            logger.success(f"Найдена кнопка I'm ready!: {selector}",
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await element.click()
                            
                            logger.success(f"I'm ready! нажата",
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await asyncio.sleep(random.uniform(2, 3))
                            return True
                            
                    except Exception as e:
                        continue
                
                try:
                    all_buttons = await self.page.query_selector_all('button')
                    for button in all_buttons:
                        try:
                            text = await button.text_content()
                            if text and ("I'm ready" in text or "I'm ready!" in text):
                                is_visible = await button.is_visible()
                                if is_visible:
                                    logger.success(f"Найдена I'm ready! в кнопке: {text}",
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    await button.click()
                                    logger.success(f"I'm ready! нажата",
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    await asyncio.sleep(random.uniform(2, 3))
                                    return True
                        except:
                            continue
                except:
                    pass
                
                if attempt < 4:
                    await asyncio.sleep(3)
            
            logger.error(f"I'm ready! не найдена",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка нажатия I'm ready!: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def handle_multiple_text_campaigns(self) -> bool:
        try:
            logger.info(f"Начало обработки текстовых кампаний",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            selected_campaigns = self.campaign_manager.select_random_campaigns()
            if not selected_campaigns:
                logger.error(f"Не удалось выбрать кампании",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            total_tasks = self.campaign_manager.get_total_tasks_count()
            logger.info(f"Общее количество задач: {total_tasks}",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            successful_tasks = 0
            failed_tasks = 0
            
            for campaign_index, campaign in enumerate(selected_campaigns):
                campaign_id = campaign["virtual_id"]
                language_code = campaign["language_code"]
                campaign_name = campaign["campaign_name"]
                tasks_count = self.campaign_manager.get_tasks_count_for_campaign(campaign_id)
                
                logger.info(f"Кампания {campaign_index + 1}/{len(selected_campaigns)}: {campaign_name} ({language_code})",
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                self.current_campaign_id = campaign_id
                self.current_language_code = language_code
                
                for task_index in range(tasks_count):
                    logger.info(f"Задача {task_index + 1}/{tasks_count} в кампании {campaign_name}",
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    if await self.handle_single_text_recording():
                        successful_tasks += 1
                        logger.success(f"Задача {task_index + 1} в кампании {campaign_name} выполнена",
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                    else:
                        failed_tasks += 1
                        logger.error(f"Задача {task_index + 1} в кампании {campaign_name} провалена",
                                    email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    if task_index < tasks_count - 1:
                        delay = random.uniform(config.DELAY_BETWEEN_TASKS["min"], config.DELAY_BETWEEN_TASKS["max"])
                        logger.info(f"Задержка {delay:.1f}s между задачами",
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
                        await asyncio.sleep(delay)
                
                if campaign_index < len(selected_campaigns) - 1:
                    delay = random.uniform(config.DELAY_BETWEEN_CAMPAIGNS["min"], config.DELAY_BETWEEN_CAMPAIGNS["max"])
                    logger.info(f"Задержка {delay:.1f}s между кампаниями",
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    await asyncio.sleep(delay)
            
            logger.success(f"Завершена обработка всех кампаний. Успешно: {successful_tasks}, Провалено: {failed_tasks}",
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            return successful_tasks > 0
            
        except Exception as e:
            import traceback
            logger.error(f"Ошибка обработки кампаний: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            logger.error(f"Traceback: {traceback.format_exc()}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def handle_text_recording_campaign(self) -> bool:
        return await self.handle_multiple_text_campaigns()

    async def handle_single_text_recording(self) -> bool:
        try:
            if not self.page:
                logger.error(f"Page object is None",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            self.token_manager.page = self.page
            
            if not await self.token_manager.extract_auth_token_from_storage():
                logger.error(f"auth_token не извлечен",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            upload_url = f"https://app.psdn.ai/campaigns/{self.current_campaign_id}/upload/audio"
            logger.info(f"Прямой переход на страницу загрузки: {upload_url}",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            response = await self.page.goto(upload_url, wait_until="domcontentloaded", timeout=30000)
            
            if not response or response.status != 200:
                logger.error(f"Ошибка перехода на страницу загрузки: {response.status if response else 'Нет ответа'}",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            logger.success(f"Успешный переход на страницу загрузки",
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not await self.click_im_ready_button():
                logger.error(f"Не удалось нажать I'm ready!",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            wait_time = random.uniform(10, 15)
            logger.info(f"Ожидание {wait_time:.1f} секунд после I'm ready!",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            await asyncio.sleep(wait_time)
            
            logger.info(f"Ожидание загрузки Cloudflare токенов...",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            await asyncio.sleep(random.uniform(8.0, 12.0))
            
            await self.page.mouse.move(random.randint(100, 400), random.randint(100, 300))
            await asyncio.sleep(1)
            await self.page.mouse.move(random.randint(200, 500), random.randint(150, 400))
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
            script_assignment = await self.get_script_assignment_via_api()
            if not script_assignment:
                logger.error(f"Не удалось получить задание",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            if not self.script_assignment_id or not self.script_content:
                logger.error(f"assignment_id или script_content отсутствуют",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            await asyncio.sleep(random.uniform(3.0, 7.0))
            
            audio_data = self.audio_generator.generate_voice_audio(self.script_content, self.current_language_code)
            if not audio_data:
                logger.error(f"audio_data пуст",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            timestamp = int(time.time() * 1000)
            file_name = f"audio_recording_{timestamp}.webm"
            content_type = "audio/webm"
            filesize = len(audio_data)
            sha256_hash = self.calculate_sha256(audio_data)
            
            await self.page.mouse.move(random.randint(300, 600), random.randint(200, 500))
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            turnstile_token = await self.get_turnstile_token_from_page()
            if not turnstile_token:
                logger.warning(f"Turnstile токен не найден, пробуем без него",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            presigned_data = await self.get_presigned_url(file_name, content_type, turnstile_token)
            if not presigned_data:
                logger.error(f"presigned_data пуст",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            presigned_url = presigned_data.get('presigned_url')
            object_key = presigned_data.get('object_key')
            file_id = presigned_data.get('file_id')
            
            if not all([presigned_url, object_key, file_id]):
                logger.error(f"Неполные данные presigned URL",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            await asyncio.sleep(random.uniform(15.0, 25.0))
            
            if not self.upload_file_to_presigned_url(presigned_url, audio_data, content_type):
                logger.error(f"Ошибка загрузки файла",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            await asyncio.sleep(random.uniform(8.0, 15.0))
            
            if not await self.register_file_in_system(object_key, file_name, file_id,
                                               filesize, sha256_hash, content_type, turnstile_token):
                logger.error(f"Ошибка регистрации файла",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            return True
            
        except Exception as e:
            import traceback
            logger.error(f"Ошибка обработки задачи: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            logger.error(f"Traceback: {traceback.format_exc()}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def extract_complete_browser_context(self) -> Optional[Dict]:
        try:
            browser_cookies = await self.page.context.cookies()
            
            js_data = await self.page.evaluate('''
                () => {
                    try {
                        const storage = {};
                        
                        for (let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            storage[key] = localStorage.getItem(key);
                        }
                        
                        for (let i = 0; i < sessionStorage.length; i++) {
                            const key = sessionStorage.key(i);
                            storage['session_' + key] = sessionStorage.getItem(key);
                        }
                        
                        return {
                            storage: storage,
                            cookies: document.cookie,
                            userAgent: navigator.userAgent,
                            url: window.location.href,
                            origin: window.location.origin,
                            referrer: document.referrer,
                            language: navigator.language,
                            platform: navigator.platform,
                            fingerprint: window.fingerprintRequestId || Date.now().toString()
                        };
                    } catch (error) {
                        console.error('Error in browser context extraction:', error);
                        return null;
                    }
                }
            ''')
            
            if not js_data:
                logger.error(f"js_data пуст",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
            
            logger.info(f"Контекст браузера извлечен",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            return {
                'browser_cookies': browser_cookies,
                'js_data': js_data
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения контекста браузера: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    async def extract_dynamic_headers_from_browser(self) -> Optional[Dict]:
        try:
            browser_info = await self.page.evaluate('''
                () => {
                    try {
                        return {
                            userAgent: navigator.userAgent,
                            platform: navigator.platform,
                            language: navigator.language,
                            languages: navigator.languages,
                            vendor: navigator.vendor,
                            cookieEnabled: navigator.cookieEnabled,
                            onLine: navigator.onLine,
                            hardwareConcurrency: navigator.hardwareConcurrency,
                            maxTouchPoints: navigator.maxTouchPoints
                        };
                    } catch (error) {
                        console.error('Error getting browser info:', error);
                        return null;
                    }
                }
            ''')
            
            if not browser_info:
                logger.error(f"browser_info вернул null из браузера",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
            
            user_agent = browser_info.get('userAgent', '')
            platform = browser_info.get('platform', 'Windows')
            language = browser_info.get('language', 'en-US')
            
            sec_ch_ua = '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'
            if 'Firefox' in user_agent:
                sec_ch_ua = '"Not/A)Brand";v="99", "Firefox";v="121"'
            elif 'Chrome' in user_agent:
                import re
                chrome_version = re.search(r'Chrome/(\d+)', user_agent)
                if chrome_version:
                    version = chrome_version.group(1)
                    sec_ch_ua = f'"Not/A)Brand";v="8", "Chromium";v="{version}", "Google Chrome";v="{version}"'
            
            if 'Win' in platform:
                sec_ch_ua_platform = '"Windows"'
            elif 'Mac' in platform:
                sec_ch_ua_platform = '"macOS"'
            elif 'Linux' in platform:
                sec_ch_ua_platform = '"Linux"'
            else:
                sec_ch_ua_platform = '"Windows"'
            
            sec_ch_ua_mobile = '?1' if browser_info.get('maxTouchPoints', 0) > 0 else '?0'
            
            logger.success(f"Динамические заголовки извлечены из реального браузера",
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            logger.info(f"User-Agent: {user_agent[:50]}...",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            logger.info(f"Platform: {platform}, Language: {language}",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            return {
                'User-Agent': user_agent,
                'sec-ch-ua': sec_ch_ua,
                'sec-ch-ua-mobile': sec_ch_ua_mobile,
                'sec-ch-ua-platform': sec_ch_ua_platform,
                'Accept-Language': language
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения динамических заголовков: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None