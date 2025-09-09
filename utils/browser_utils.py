import asyncio
import time
import random
from typing import Optional
from datetime import datetime
from camoufox.async_api import AsyncCamoufox

from logger import get_logger
from proxy_manager import proxy_manager
from microphone_handler import MicrophoneHandler
from utils import config

logger = get_logger('BrowserUtils')

class BrowserUtils:
    
    def __init__(self, email: str, db, position: int, total_accounts: int):
        self.email = email
        self.db = db
        self.position = position
        self.total_accounts = total_accounts
        self.browser = None
        self.page = None
    
    def get_proxy_config(self) -> Optional[dict]:
        try:
            if not config.USE_PROXIES:
                return None
                
            proxy_data = self.db.get_proxy(self.email)
            
            if proxy_data and config.USE_PROXIES:
                proxy_url = proxy_data.get('http', '')
                if proxy_url:
                    if "@" in proxy_url:
                        auth_part = proxy_url.split("://")[1].split("@")[0]
                        server_part = proxy_url.split("@")[1]
                        username, password = auth_part.split(":")
                        server, port = server_part.split(":")
                        
                        proxy_config = {
                            "server": f"http://{server}:{port}",
                            "username": username,
                            "password": password
                        }
                        
                        logger.info(f"Прокси настроен", 
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return proxy_config
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка настройки прокси: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    async def human_like_mouse_move_to_element(self, element):
        try:
            box = await element.bounding_box()
            if box:
                target_x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
                target_y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
                
                await self.page.mouse.move(target_x, target_y)
                await asyncio.sleep(random.uniform(0.1, 0.2))
        except Exception as e:
            logger.warning(f"Ошибка движения мыши к элементу: {e}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
    
    async def wait_for_element_and_click(self, selectors: list, action_name: str = "элемент") -> bool:
        try:
            start_time = time.time()
            max_wait_time = config.SELECTOR_WAIT_TIMEOUT / 1000
            
            while time.time() - start_time < max_wait_time:
                for selector in selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            is_visible = await element.is_visible()
                            is_enabled = await element.is_enabled()
                            
                            if is_visible and is_enabled:
                                is_disabled = await element.get_attribute("disabled")
                                if not is_disabled:
                                    await element.wait_for_element_state("stable", timeout=5000)
                                    await self.human_like_mouse_move_to_element(element)
                                    await element.click(timeout=10000)
                                    
                                    logger.success(f"{action_name} найден и нажат", 
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    return True
                    except:
                        continue
                
                await asyncio.sleep(config.SELECTOR_CHECK_INTERVAL / 1000)
            
            logger.error(f"{action_name} не найден за {max_wait_time}с", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка ожидания и нажатия {action_name}: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
    
    async def setup_browser(self):
        try:
            proxy_config = self.get_proxy_config()
            firefox_prefs = MicrophoneHandler.get_camoufox_microphone_preferences()
            
            camoufox_config = {
                "headless": config.HEADLESS_MODE,
                "humanize": True,
                "disable_coop": True,
                "i_know_what_im_doing": True,
                "firefox_user_prefs": firefox_prefs,
            }
            
            if getattr(config, 'USE_CAMOUFOX_PROFILES', False):
                os_options = ["windows", "macos", "linux"]
                selected_os = random.choice(os_options)
                
                camoufox_config.update({
                    "os": selected_os,
                })
                
                if proxy_config:
                    camoufox_config["proxy"] = proxy_config
                    camoufox_config["geoip"] = True
                else:
                    camoufox_config["geoip"] = False
            
            self.browser = AsyncCamoufox(**camoufox_config)
            await self.browser.__aenter__()
            self.page = await self.browser.browser.new_page()
            
            logger.success(f"Браузер настроен успешно", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            
        except Exception as e:
            logger.error(f"Ошибка настройки браузера: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            await self.cleanup_browser()
            raise
    
    async def cleanup_browser(self):
        try:
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.browser:
                await self.browser.__aexit__(None, None, None)
                self.browser = None
                
        except Exception as e:
            logger.warning(f"Ошибка при закрытии браузера: {e}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
    
    async def check_ip_address(self) -> bool:
        try:
            logger.info(f"Проверка IP адреса на {config.CHECK_IP_URL}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            response = await self.page.goto(
                config.CHECK_IP_URL, 
                wait_until="networkidle",
                timeout=config.REQUEST_TIMEOUT * 1000
            )
            
            if response and response.status == 200:
                await asyncio.sleep(config.IP_CHECK_WAIT_TIME)
                
                page_content = await self.page.content()
                
                import json
                import re
                ip_match = re.search(r'"origin":\s*"([^"]+)"', page_content)
                if ip_match:
                    ip_address = ip_match.group(1)
                    logger.success(f"IP: {ip_address}", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                else:
                    logger.warning(f"Не удалось извлечь IP из ответа", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                return True
            else:
                status = response.status if response else "No response"
                logger.error(f"Ошибка проверки IP, статус: {status}", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка проверки IP: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
    
    async def navigate_to_site(self) -> bool:
        try:
            logger.info(f"Переход на сайт {config.BASE_URL}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            try:
                response = await self.page.goto(
                    config.BASE_URL, 
                    wait_until="domcontentloaded",
                    timeout=45000
                )
            except Exception as first_error:
                logger.warning(f"Первая попытка неудачна, пробуем без ожидания: {first_error}", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                try:
                    response = await self.page.goto(
                        config.BASE_URL, 
                        timeout=30000
                    )
                except Exception as second_error:
                    logger.error(f"Вторая попытка неудачна: {second_error}", 
                                email=self.email, position=f"{self.position}/{self.total_accounts}")
                    raise second_error
            
            if response:
                status = response.status
                logger.info(f"Ответ сервера: {status}", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                if status in [200, 301, 302, 404]:
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    try:
                        await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except:
                        logger.warning(f"DOM не загрузился за 10с, продолжаем", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    current_url = self.page.url
                    logger.success(f"Страница загружена: {current_url}", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    await self.page.mouse.move(
                        random.randint(200, 800), 
                        random.randint(200, 600)
                    )
                    await asyncio.sleep(random.uniform(0.5, 1))
                    
                    return True
                else:
                    logger.error(f"Неожиданный статус ответа: {status}", 
                                email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return False
            else:
                logger.error(f"Нет ответа от сервера", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка навигации на сайт: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if "Timeout" in str(e):
                current_proxy = self.db.get_proxy(self.email)
                if current_proxy:
                    proxy_string = proxy_manager.get_proxy_string(current_proxy)
                    if proxy_string:
                        proxy_manager.mark_proxy_bad(
                            proxy_string, 
                            f"Timeout при загрузке: {str(e)}", 
                            self.email
                        )
            
            return False