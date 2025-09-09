import asyncio
import json
import random
import tempfile
import os
import time
import requests
from typing import Optional
from utils.logger import get_logger
from utils.audio_generator import AudioGenerator
from utils.token_manager import TokenManager
from utils.turnstile_handler import TurnstileHandler
from utils import config

logger = get_logger('VoiceHandler')

class VoiceHandler:
    
    def __init__(self, page, email, position, total_accounts, proxy=None, email_verification=None):
        self.page = page
        self.email = email
        self.position = position
        self.total_accounts = total_accounts
        self.proxy = proxy
        self.email_verification = email_verification
        self.voice_phrase = None
        self.generated_audio = None
        
        self.audio_generator = AudioGenerator(email, position, total_accounts, proxy)
        self.token_manager = TokenManager(page, email, position, total_accounts)
        self.turnstile_handler = TurnstileHandler(page, email, position, total_accounts)

    def update_page(self, page):
        self.page = page
        self.token_manager.page = page
        self.turnstile_handler.page = page

    def update_proxy(self, proxy):
        self.proxy = proxy
        self.audio_generator.proxy = proxy

    def set_email_verification_handler(self, email_verification):
        self.email_verification = email_verification

    def extract_voice_phrase_from_response(self, response_text: str) -> Optional[str]:
        try:
            data = json.loads(response_text)
            voice_phrase = data.get('voice_phrase', '')
            if voice_phrase:
                logger.info(f"Извлечена voice_phrase: {voice_phrase}", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                self.voice_phrase = voice_phrase
                return voice_phrase
        except Exception as e:
            logger.error(f"Ошибка извлечения voice_phrase: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
        return None

    def get_voice_phrase_from_captured_data(self) -> Optional[str]:
        try:
            if self.email_verification and hasattr(self.email_verification, 'voice_phrase') and self.email_verification.voice_phrase:
                self.voice_phrase = self.email_verification.voice_phrase
                logger.success(f"Получена voice_phrase из перехваченных данных: {self.voice_phrase}", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return self.voice_phrase
            
            if self.email_verification and hasattr(self.email_verification, 'requests_dir') and self.email_verification.requests_dir:
                phrase_file = os.path.join(self.email_verification.requests_dir, 'voice_phrase.txt')
                if os.path.exists(phrase_file):
                    with open(phrase_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for line in content.split('\n'):
                            if line.startswith('Voice Phrase:'):
                                phrase = line.replace('Voice Phrase:', '').strip()
                                if phrase:
                                    self.voice_phrase = phrase
                                    logger.success(f"Загружена voice_phrase из файла: {phrase}", 
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    return phrase
            
            logger.warning(f"Voice phrase не найдена в перехваченных данных", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения voice_phrase из перехваченных данных: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    def get_latest_cf_token_from_captured_data(self) -> Optional[str]:
        try:
            if self.email_verification and hasattr(self.email_verification, 'get_latest_cf_token'):
                token = self.email_verification.get_latest_cf_token()
                if token:
                    logger.success(f"Получен CF токен из перехваченных данных: {token[:50]}...", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return token
            
            if self.email_verification and hasattr(self.email_verification, 'requests_dir') and self.email_verification.requests_dir:
                tokens_file = os.path.join(self.email_verification.requests_dir, 'cf_tokens.txt')
                if os.path.exists(tokens_file):
                    with open(tokens_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            last_line = lines[-1].strip()
                            if '|' in last_line:
                                token = last_line.split('|')[-1].strip()
                                if token and len(token) > 50:
                                    logger.success(f"Загружен CF токен из файла: {token[:50]}...", 
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    return token
            
            logger.warning(f"CF токен не найден в перехваченных данных", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения CF токена: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    def generate_voice_audio(self, text: str) -> bytes:
        try:
            logger.info(f"Генерация voice profile аудио: {text[:50]}...", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            audio_data = self.audio_generator.generate_voice_audio(text, "en")
            
            if audio_data:
                logger.success(f"Voice profile аудио сгенерировано: {len(audio_data)} байт", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                self.generated_audio = audio_data
                return audio_data
            else:
                logger.error(f"AudioGenerator вернул пустое аудио", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return b''
            
        except Exception as e:
            logger.error(f"Ошибка генерации voice profile аудио: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return b''

    async def extract_dynamic_headers_from_browser(self) -> Optional[dict]:
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
            
            logger.success(f"Динамические заголовки извлечены", 
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

    async def setup_request_interception(self):
        try:
            logger.info(f"Настройка перехвата запросов для VoiceHandler", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not self.email_verification:
                from email_verification import EmailVerification
                self.email_verification = EmailVerification(self.page, self.email, "", self.position, self.total_accounts)
            
            await self.email_verification.setup_request_interception()
            
            logger.success(f"Перехват запросов настроен для VoiceHandler", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            
        except Exception as e:
            logger.error(f"Ошибка настройки перехвата запросов: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")

    async def get_voice_phrase_from_page(self) -> Optional[str]:
        try:
            logger.info(f"Получение voice phrase со страницы", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await self.setup_request_interception()
            
            voice_phrase_selectors = [
                'p.text-lg.text-center.font-bold',
                'div[data-testid="voice-phrase"]',
                '.voice-phrase',
                'p:contains("logout")',
                'p:contains("spell")',
                'div.text-center p',
                'h2 + p',
                'div.font-bold'
            ]
            
            for selector in voice_phrase_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element and await element.is_visible():
                        text = await element.text_content()
                        if text and len(text.split()) > 8:
                            self.voice_phrase = text.strip()
                            
                            if self.email_verification:
                                self.email_verification.voice_phrase = self.voice_phrase
                                
                            logger.success(f"Voice phrase найдена: {self.voice_phrase}", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            return self.voice_phrase
                except Exception:
                    continue
            
            try:
                js_phrase = await self.page.evaluate('''
                    () => {
                        const elements = document.querySelectorAll('p, div, span');
                        for (let el of elements) {
                            const text = el.textContent || el.innerText;
                            if (text && text.split(' ').length > 8 && 
                                (text.includes('logout') || text.includes('spell') || 
                                 text.includes('various') || text.includes('sunset'))) {
                                return text.trim();
                            }
                        }
                        return null;
                    }
                ''')
                
                if js_phrase:
                    self.voice_phrase = js_phrase
                    if self.email_verification:
                        self.email_verification.voice_phrase = self.voice_phrase
                    logger.success(f"Voice phrase найдена через JS: {self.voice_phrase}", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return self.voice_phrase
            except Exception as e:
                logger.warning(f"Ошибка JS поиска: {e}")
            
            logger.error(f"Voice phrase не найдена на странице", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения voice phrase со страницы: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    async def upload_voice_recording_to_api(self, voice_phrase: str) -> bool:
        try:
            logger.info(f"Начало загрузки voice recording через API", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            audio_data = self.generate_voice_audio(voice_phrase)
            if not audio_data:
                logger.error(f"Не удалось сгенерировать аудио для voice recording", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            dynamic_headers = await self.extract_dynamic_headers_from_browser()
            if not dynamic_headers:
                logger.error(f"Не удалось получить динамические заголовки", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            if not await self.token_manager.extract_auth_token_from_storage():
                logger.error(f"auth_token не извлечен", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            auth_token = self.token_manager.get_token()
            if not auth_token:
                logger.error(f"auth_token пустой", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            url = "https://poseidon-depin-server.storyapis.com/users/me/voice-phrase/recording"
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': dynamic_headers.get('Accept-Language', 'fi'),
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Origin': 'https://app.psdn.ai',
                'Referer': 'https://app.psdn.ai/',
                'sec-ch-ua': dynamic_headers.get('sec-ch-ua', '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'),
                'sec-ch-ua-mobile': dynamic_headers.get('sec-ch-ua-mobile', '?0'),
                'sec-ch-ua-platform': dynamic_headers.get('sec-ch-ua-platform', '"Windows"'),
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'priority': 'u=1, i',
                'User-Agent': dynamic_headers.get('User-Agent', ''),
                'authorization': f'Bearer {auth_token}'
            }
            
            cf_token = None
            
            if config.TWOCAPTCHA_CONFIG.get("use_for_registration", False):
                logger.info(f"Получение Turnstile токена через 2captcha для voice recording", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                cf_token = await self.turnstile_handler.solve_turnstile_with_2captcha(proxy=self.proxy)
                
                if not cf_token:
                    cf_token = self.get_latest_cf_token_from_captured_data()
            else:
                cf_token = self.get_latest_cf_token_from_captured_data()
            
            if cf_token:
                headers['cf-turnstile-token'] = cf_token
                logger.info(f"Добавлен CF токен в заголовки", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            else:
                logger.info(f"CF токен не найден, пробуем запрос БЕЗ CF токена", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            timestamp = str(int(time.time() * 1000))
            filename = f"voice_recording_{timestamp}.webm"
            
            files = {
                'file': (filename, audio_data, 'audio/webm')
            }
            
            logger.info(f"Отправка voice recording: файл={filename}, размер={len(audio_data)} байт, CF токен: {'Да' if cf_token else 'НЕТ'}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            response = await self.make_request_with_retry(url, headers, files)
            
            if response and response.status_code == 200:
                result = response.json()
                logger.success(f"Voice recording успешно загружена! Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            else:
                status = response.status_code if response else "No response"
                response_text = response.text if response else "No text"
                logger.error(f"Ошибка загрузки voice recording: {status} - {response_text[:200]}...", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка загрузки voice recording через API: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def upload_voice_recording_directly(self, voice_phrase: str = None) -> bool:
        try:
            if not voice_phrase:
                voice_phrase = await self.get_voice_phrase_from_page()
                if not voice_phrase:
                    voice_phrase = self.get_voice_phrase_from_captured_data()
                    if not voice_phrase:
                        logger.error(f"Voice phrase не найдена", 
                                    email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return False
            
            logger.info(f"Прямая загрузка voice recording без UI: {voice_phrase}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(5, 8))
            
            if await self.upload_voice_recording_to_api(voice_phrase):
                logger.success(f"Voice recording загружена успешно", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                await asyncio.sleep(random.uniform(2, 4))
                
                if await self.complete_intro_process():
                    logger.success(f"Voice recording и complete-intro завершены успешно", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return True
                else:
                    logger.warning(f"Voice recording загружена, но complete-intro не удался", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return False
            else:
                logger.error(f"Не удалось загрузить voice recording напрямую", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка прямой загрузки voice recording: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def handle_voice_recording_process(self, voice_phrase: str = None) -> bool:
        try:
            if not voice_phrase:
                voice_phrase = self.get_voice_phrase_from_captured_data()
            
            if not voice_phrase:
                logger.error(f"Voice phrase не найдена для обработки", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            logger.info(f"Начало процесса voice recording с реальной загрузкой: {voice_phrase}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not await self.click_start_recording():
                logger.error(f"Не удалось нажать Start Recording", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            recording_time = random.uniform(8, 12)
            logger.info(f"Имитация записи {recording_time:.1f} секунд", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            await asyncio.sleep(recording_time)
            
            if not await self.click_stop_recording():
                logger.warning(f"Не удалось нажать Stop Recording, продолжаем", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(2, 4))
            
            if await self.upload_voice_recording_to_api(voice_phrase):
                logger.success(f"Voice recording процесс завершен успешно", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            else:
                logger.error(f"Не удалось загрузить voice recording через API", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка процесса voice recording: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def complete_intro_process(self) -> bool:
        try:
            logger.info(f"Завершение intro процесса через /complete-intro", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            dynamic_headers = await self.extract_dynamic_headers_from_browser()
            if not dynamic_headers:
                logger.error(f"Не удалось получить динамические заголовки для complete-intro", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            auth_token = self.token_manager.get_token()
            if not auth_token:
                logger.error(f"auth_token отсутствует для complete-intro", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            url = "https://poseidon-depin-server.storyapis.com/users/me/complete-intro"
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': dynamic_headers.get('Accept-Language', 'fi'),
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Origin': 'https://app.psdn.ai',
                'Referer': 'https://app.psdn.ai/',
                'sec-ch-ua': dynamic_headers.get('sec-ch-ua', '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'),
                'sec-ch-ua-mobile': dynamic_headers.get('sec-ch-ua-mobile', '?0'),
                'sec-ch-ua-platform': dynamic_headers.get('sec-ch-ua-platform', '"Windows"'),
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'priority': 'u=1, i',
                'User-Agent': dynamic_headers.get('User-Agent', ''),
                'authorization': f'Bearer {auth_token}'
            }
            
            cf_token = None
            
            if config.TWOCAPTCHA_CONFIG.get("use_for_registration", False):
                cf_token = await self.turnstile_handler.solve_turnstile_with_2captcha(proxy=self.proxy)
                
                if not cf_token:
                    cf_token = self.get_latest_cf_token_from_captured_data()
            else:
                cf_token = self.get_latest_cf_token_from_captured_data()
            
            if cf_token:
                headers['cf-turnstile-token'] = cf_token
                logger.info(f"Добавлен CF токен для complete-intro", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            else:
                logger.info(f"CF токен не найден, пробуем complete-intro БЕЗ CF токена", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            empty_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\xdb\xdb\xa5\x00\x00\x00\x00IEND\xaeB`\x82'
            
            files = {
                'avatar': ('avatar.png', empty_png, 'image/png'),
                'avatar_nft': ('avatar_nft.png', empty_png, 'image/png')
            }
            
            logger.info(f"Отправка complete-intro запроса, CF токен: {'Да' if cf_token else 'НЕТ'}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            response = await self.make_request_with_retry(url, headers, files)
            
            if response and response.status_code == 200:
                result = response.json()
                logger.success(f"Complete-intro успешно завершен! Ответ: {str(result)[:200]}...", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            else:
                status = response.status_code if response else "No response"
                response_text = response.text if response else "No text"
                logger.error(f"Ошибка complete-intro: {status} - {response_text[:200]}...", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка завершения intro процесса: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def make_request_with_retry(self, url: str, headers: dict, files: dict, max_retries: int = 3):
        try:
            for attempt in range(max_retries):
                try:
                    logger.info(f"Попытка {attempt + 1}/{max_retries}: POST {url}", 
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    import requests
                    
                    proxies = None
                    if self.proxy:
                        proxies = self.proxy
                        logger.info(f"Используем прокси: {str(proxies.get('http', ''))[:40]}...", 
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    response = requests.post(
                        url, 
                        headers=headers, 
                        files=files,
                        proxies=proxies,
                        timeout=60,
                        allow_redirects=False
                    )
                    
                    logger.info(f"Статус ответа: {response.status_code}", 
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    return response
                    
                except Exception as e:
                    if "timed out" in str(e).lower():
                        logger.warning(f"Таймаут на попытке {attempt + 1}: {e}", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5
                            logger.info(f"Ожидание {wait_time} секунд перед повтором", 
                                       email=self.email, position=f"{self.position}/{self.total_accounts}")
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

    async def click_start_recording(self) -> bool:
        try:
            if not self.page:
                logger.error(f"Page object is None", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
            logger.info(f"Поиск Start Recording", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(1, 2))
            
            start_recording_selectors = [
                'button:has-text("Start Recording")',
                'button.inline-flex.items-center.justify-center:has-text("Start Recording")', 
                'button[class*="cursor-pointer"]:has-text("Start Recording")',
                'button.rounded-full:has-text("Start Recording")',
                'button:contains("Start Recording")',
                'button[type="button"]:has-text("Start Recording")',
                '[role="button"]:has-text("Start Recording")',
                'div:has-text("Start Recording")',
                'span:has-text("Start Recording")'
            ]
            
            for attempt in range(5):
                logger.info(f"Попытка #{attempt + 1} поиска Start Recording", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                for selector in start_recording_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=3000)
                        if element and await element.is_visible():
                            logger.success(f"Найдена Start Recording: {selector}", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await element.click()
                            
                            logger.success(f"Start Recording нажата", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await asyncio.sleep(1)
                            return True
                            
                    except Exception as e:
                        continue
                
                try:
                    all_buttons = await self.page.query_selector_all('button')
                    for button in all_buttons:
                        try:
                            text = await button.text_content()
                            if text and "Start Recording" in text:
                                is_visible = await button.is_visible()
                                if is_visible:
                                    logger.success(f"Найдена Start Recording в кнопке: {text}", 
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    await button.click()
                                    logger.success(f"Start Recording нажата", 
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    await asyncio.sleep(1)
                                    return True
                        except:
                            continue
                except:
                    pass
                
                if attempt < 4:
                    await asyncio.sleep(2)
            
            logger.error(f"Start Recording не найдена", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка нажатия Start Recording: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def click_stop_recording(self) -> bool:
        try:
            logger.info(f"Поиск Stop Recording", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(1, 2))
            
            stop_recording_selectors = [
                'button:has-text("Stop Recording")',
                'button:has-text("Stop")',
                'button.inline-flex.items-center.justify-center:has-text("Stop")',
                'button[class*="cursor-pointer"]:has-text("Stop")',
                'button.rounded-full:has-text("Stop")',
                'button[aria-label*="stop"]',
                'button[aria-label*="Stop"]'
            ]
            
            for attempt in range(5):
                logger.info(f"Попытка #{attempt + 1} поиска Stop Recording", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                for selector in stop_recording_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=3000)
                        if element and await element.is_visible():
                            logger.success(f"Найдена Stop Recording: {selector}", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await element.click()
                            
                            logger.success(f"Stop Recording нажата", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await asyncio.sleep(1)
                            return True
                            
                    except Exception:
                        continue
                
                try:
                    all_buttons = await self.page.query_selector_all('button')
                    for button in all_buttons:
                        try:
                            text = await button.text_content()
                            if text and ("Stop" in text or "stop" in text.lower()):
                                is_visible = await button.is_visible()
                                if is_visible:
                                    logger.success(f"Найдена Stop в кнопке: {text}", 
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    await button.click()
                                    logger.success(f"Stop Recording нажата", 
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    await asyncio.sleep(1)
                                    return True
                        except:
                            continue
                except:
                    pass
                
                if attempt < 4:
                    await asyncio.sleep(2)
            
            logger.warning(f"Stop Recording не найдена", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка нажатия Stop Recording: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return True