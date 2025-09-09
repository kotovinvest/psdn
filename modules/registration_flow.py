import asyncio
import random
import time
from typing import List, Dict
from logger import get_logger
from voice_handler import VoiceHandler

logger = get_logger('RegistrationFlow')

class RegistrationFlow:
    
    def __init__(self, page, email, position, total_accounts, db=None, email_verification=None):
        self.page = page
        self.email = email
        self.position = position
        self.total_accounts = total_accounts
        self.db = db
        self.email_verification = email_verification
        
        account_proxy = None
        if db:
            account_proxy = db.get_proxy(email)
            logger.info(f"Прокси для voice handler: {str(account_proxy)[:40] if account_proxy else 'Нет'}...", 
                       email=email, position=f"{position}/{total_accounts}")
        
        self.voice_handler = VoiceHandler(page, email, position, total_accounts, account_proxy, email_verification)

    def update_page_references(self):
        self.voice_handler.update_page(self.page)

    async def wait_for_registration_completion(self, captured_requests: List[Dict], requests_file: str):
        try:
            logger.info(f"Ожидание завершения регистрации", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            max_wait_time = 180
            start_time = time.time()
            
            await asyncio.sleep(random.uniform(3, 5))
            
            while time.time() - start_time < max_wait_time:
                try:
                    current_url = self.page.url
                    page_content = await self.page.content()
                    
                    logger.info(f"Проверяем URL: {current_url}", 
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    if "/intro" in current_url and ("Turn your voice into valuable AI training data" in page_content or "Next" in page_content):
                        logger.success(f"Попали на intro страницу", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        
                        if await self.handle_intro_steps():
                            logger.success(f"Intro шаги обработаны", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            return True
                        else:
                            logger.warning(f"Ошибка обработки intro", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                        break
                    
                    elif "Let's create your voice profile" in page_content or "Read this aloud" in page_content:
                        logger.success(f"Попали на voice profile", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        
                        if await self.handle_voice_profile_page():
                            logger.success(f"Voice profile обработан", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            return True
                        else:
                            logger.warning(f"Ошибка voice profile", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                        break
                    
                    elif "/dashboard" in current_url or "dashboard" in page_content.lower():
                        logger.success(f"Попали на dashboard", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return True
                    
                    elif "/login" in current_url:
                        logger.warning(f"Вернулись на login, ждем еще", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        await asyncio.sleep(random.uniform(5, 10))
                        continue
                    
                    else:
                        logger.info(f"Ждем перенаправления... URL: {current_url[:50]}...", 
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    await asyncio.sleep(random.uniform(3, 5))
                    
                except Exception as e:
                    logger.warning(f"Ошибка проверки: {e}")
                    await asyncio.sleep(random.uniform(3, 5))
                    continue
            
            logger.warning(f"Время ожидания истекло", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка ожидания регистрации: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def handle_intro_steps(self) -> bool:
        try:
            logger.info(f"Начинаем intro шаги", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(2, 4))
            
            for i in range(3):
                logger.info(f"Нажимаем Next #{i+1}/3", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                if await self.click_next_button():
                    logger.success(f"Next #{i+1} нажат", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    await asyncio.sleep(random.uniform(2, 4))
                else:
                    logger.warning(f"Не удалось нажать Next #{i+1}", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    break
            
            logger.info(f"Обрабатываем микрофон", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            from microphone_handler import MicrophoneHandler
            mic_handler = MicrophoneHandler(self.page, self.email, self.position, self.total_accounts)
            
            if not await mic_handler.click_allow_microphone_button():
                logger.warning(f"Не удалось нажать Allow microphone", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(3, 5))
            
            if not await mic_handler.click_im_ready_button():
                logger.warning(f"Не удалось нажать I'm ready", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(3, 5))
            page_content = await self.page.content()
            current_url = self.page.url
            
            if "Let's create your voice profile" in page_content or "Read this aloud" in page_content:
                logger.success(f"Дошли до voice profile после микрофона", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return await self.handle_voice_profile_page()
            elif "/dashboard" in current_url or "dashboard" in page_content.lower():
                logger.success(f"Попали на dashboard", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            else:
                logger.info(f"Завершили intro шаги", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            
        except Exception as e:
            logger.error(f"Ошибка intro шагов: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def click_next_button(self) -> bool:
        try:
            next_selectors = [
                'button:has-text("Next")',
                'button.inline-flex.items-center.justify-center:has-text("Next")',
                'button[class*="cursor-pointer"]:has-text("Next")',
                'button.rounded-full:has-text("Next")',
                '[class*="button"]:has-text("Next")',
                'button[type="submit"]',
                'button[aria-label*="next"]',
                'button[aria-label*="Next"]'
            ]
            
            for selector in next_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element and await element.is_visible():
                        await element.click()
                        logger.success(f"Next найден: {selector}", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return True
                except Exception as e:
                    logger.warning(f"Селектор {selector} не сработал: {e}")
                    continue
            
            logger.warning(f"Next кнопка не найдена", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка поиска Next: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def get_voice_phrase_from_page(self) -> str:
        try:
            logger.info(f"Извлечение voice phrase со страницы", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            js_code = """
            () => {
                try {
                    const wordElements = document.querySelectorAll('span, div, p, button, [class*="word"], [class*="phrase"]');
                    const words = [];
                    
                    for (let element of wordElements) {
                        const text = element.textContent?.trim();
                        if (text && text.length > 2 && text.length < 20 && /^[a-z]+$/i.test(text)) {
                            words.push(text.toLowerCase());
                        }
                    }
                    
                    const uniqueWords = [...new Set(words)];
                    const filteredWords = uniqueWords.filter(word => 
                        !['read', 'this', 'aloud', 'please', 'the', 'phrase', 'clearly', 'and', 'naturally', 'into', 'your', 'microphone', 'you', 'can', 'always', 'redo', 'it', 'before', 'submitting', 'start', 'recording', 'stop', 'processing', 'next', 'back', 'continue', 'submit'].includes(word) &&
                        word.length > 2
                    );
                    
                    console.log('Найденные слова:', filteredWords);
                    
                    if (filteredWords.length >= 10 && filteredWords.length <= 15) {
                        return filteredWords.slice(0, 12).join(' ');
                    }
                    
                    return null;
                } catch (error) {
                    console.error('Error extracting voice phrase from page:', error);
                    return null;
                }
            }
            """
            
            voice_phrase = await self.page.evaluate(js_code)
            
            if voice_phrase:
                logger.success(f"Voice phrase извлечена со страницы: {voice_phrase}", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return voice_phrase
            else:
                logger.warning(f"Voice phrase не найдена в DOM элементах", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return ""
                
        except Exception as e:
            logger.error(f"Ошибка извлечения voice phrase со страницы: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return ""

    async def get_voice_phrase_from_page_or_api(self) -> str:
        try:
            logger.info(f"Получение voice phrase", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            voice_phrase = await self.get_voice_phrase_from_page()
            if voice_phrase:
                return voice_phrase
            
            voice_phrase = await self.fetch_user_data_and_extract_voice_phrase()
            if voice_phrase:
                return voice_phrase
            
            if self.email_verification and hasattr(self.email_verification, 'voice_phrase') and self.email_verification.voice_phrase:
                logger.success(f"Используем voice phrase из перехваченных данных: {self.email_verification.voice_phrase}", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return self.email_verification.voice_phrase
            
            logger.error(f"НЕ УДАЛОСЬ ПОЛУЧИТЬ VOICE PHRASE - НИ СО СТРАНИЦЫ, НИ ЧЕРЕЗ API, НИ ИЗ ПЕРЕХВАЧЕННЫХ ДАННЫХ", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return ""
            
        except Exception as e:
            logger.error(f"Ошибка получения voice phrase: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return ""

    async def fetch_user_data_and_extract_voice_phrase(self) -> str:
        try:
            logger.info(f"Получение данных пользователя", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            js_code = """
            async function fetchUserData() {
                try {
                    const token = localStorage.getItem('dynamic_authentication_token') || 
                                 sessionStorage.getItem('dynamic_authentication_token') ||
                                 localStorage.getItem('dynamic_min_authentication_token') ||
                                 sessionStorage.getItem('dynamic_min_authentication_token') ||
                                 localStorage.getItem('authToken') || 
                                 sessionStorage.getItem('authToken') || 
                                 localStorage.getItem('jwt') || 
                                 sessionStorage.getItem('jwt');
                    
                    if (!token) {
                        console.log('No auth token found');
                        return null;
                    }
                    
                    const response = await fetch('https://poseidon-depin-server.storyapis.com/users/me', {
                        method: 'GET',
                        headers: {
                            'Authorization': 'Bearer ' + token,
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log('User data fetched successfully');
                        return data;
                    } else {
                        console.error('Failed to fetch user data:', response.status);
                        return null;
                    }
                } catch (error) {
                    console.error('Error fetching user data:', error);
                    return null;
                }
            }
            
            return await fetchUserData();
            """
            
            user_data = await self.page.evaluate(js_code)
            
            if user_data and isinstance(user_data, dict):
                voice_phrase = user_data.get('voice_phrase', '')
                if voice_phrase:
                    logger.success(f"Voice phrase получена через API: {voice_phrase}", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return voice_phrase
                else:
                    logger.warning(f"Voice phrase не найдена в данных API", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
            else:
                logger.warning(f"Не удалось получить данные пользователя через API", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            return ""
            
        except Exception as e:
            logger.error(f"Ошибка получения voice_phrase через API: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return ""

    async def handle_voice_profile_page(self) -> bool:
        try:
            logger.info(f"Обработка voice profile", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            self.update_page_references()
            
            await asyncio.sleep(random.uniform(5, 8))
            
            page_content = await self.page.content()
            if not ("Let's create your voice profile" in page_content or "Read this aloud" in page_content):
                logger.warning(f"Не на voice profile странице", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            
            logger.info(f"Подтверждено: на voice profile", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            voice_phrase = await self.get_voice_phrase_from_page_or_api()
            
            if not voice_phrase:
                max_attempts = 5
                for attempt in range(max_attempts):
                    logger.info(f"Попытка #{attempt + 1} получения voice_phrase", 
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    await asyncio.sleep(3)
                    voice_phrase = await self.get_voice_phrase_from_page_or_api()
                    if voice_phrase:
                        logger.success(f"Voice phrase получена на попытке #{attempt + 1}: {voice_phrase}", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        break
                    else:
                        logger.warning(f"Voice phrase не получена на попытке #{attempt + 1}, ждем", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not voice_phrase:
                logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить voice_phrase - прерываем процесс", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            if await self.voice_handler.upload_voice_recording_directly(voice_phrase):
                logger.success(f"Voice recording загружена напрямую", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                await asyncio.sleep(random.uniform(5, 8))
                
                if await self.check_for_completion():
                    logger.success(f"Регистрация завершена", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return True
                else:
                    logger.warning(f"Регистрация не завершена", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return False
            else:
                logger.error(f"Не удалось загрузить voice recording", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка voice profile: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def check_for_completion(self) -> bool:
        try:
            logger.info(f"Проверка завершения регистрации", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            max_wait_time = 120
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    current_url = self.page.url
                    page_content = await self.page.content()
                    
                    if "/dashboard" in current_url or "dashboard" in page_content.lower():
                        logger.success(f"Попали на dashboard", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return True
                    
                    if "complete" in page_content.lower() or "success" in page_content.lower():
                        logger.success(f"Найдены признаки завершения", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return True
                    
                    if "/login" in current_url:
                        logger.warning(f"Попали обратно на login, ждем еще", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        await asyncio.sleep(random.uniform(5, 10))
                        continue
                    
                    await asyncio.sleep(random.uniform(3, 5))
                    
                except Exception as e:
                    logger.warning(f"Ошибка проверки завершения: {e}")
                    await asyncio.sleep(random.uniform(3, 5))
                    continue
            
            logger.info(f"Время ожидания истекло, считаем успешным", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки завершения: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return True