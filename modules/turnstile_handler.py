import asyncio
import requests
import time
import json
from typing import Optional, Dict, Any
from logger import get_logger
import config

logger = get_logger('CloudflareSolver')

class CloudflareSolver:
    
    def __init__(self, email: str, position: int, total_accounts: int):
        self.email = email
        self.position = position
        self.total_accounts = total_accounts
        self.api_key = config.TWOCAPTCHA_API_KEY
        self.base_url = "https://2captcha.com"
        
    def solve_turnstile_simple(self, website_url: str, website_key: str, proxy: dict = None) -> Optional[str]:
        try:
            logger.info(f"Быстрое решение Turnstile: {website_url}",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not self.api_key:
                logger.error(f"2captcha API ключ не настроен",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
            
            submit_url = f"{self.base_url}/in.php"
            submit_data = {
                "key": self.api_key,
                "method": "turnstile",
                "sitekey": website_key,
                "pageurl": website_url,
                "json": 1
            }
            
            if proxy and proxy.get("http"):
                proxy_url = proxy.get("http", "")
                if "@" in proxy_url:
                    import re
                    match = re.match(r"http://(.+):(.+)@(.+):(\d+)", proxy_url)
                    if match:
                        username, password, host, port = match.groups()
                        submit_data.update({
                            "proxy": f"{host}:{port}",
                            "proxytype": "HTTP",
                            "proxylogin": username,
                            "proxypassword": password
                        })
                        logger.info(f"Используем прокси для 2captcha: {host}:{port}",
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            logger.info(f"Отправка задачи в 2captcha (простой метод)",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            response = requests.post(submit_url, data=submit_data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("status") == 1:
                captcha_id = result.get("request")
                logger.success(f"Задача принята 2captcha, ID: {captcha_id}",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                return self._get_simple_result(captcha_id, max_wait_time=60)
            else:
                error = result.get("request", "Unknown error")
                logger.error(f"Ошибка отправки в 2captcha: {error}",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка решения Turnstile: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None
    
    def _get_simple_result(self, captcha_id: str, max_wait_time: int = 60) -> Optional[str]:
        try:
            result_url = f"{self.base_url}/res.php"
            start_time = time.time()
            
            logger.info(f"Ожидание решения задачи {captcha_id} (макс. {max_wait_time}s)",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            while time.time() - start_time < max_wait_time:
                params = {
                    "key": self.api_key,
                    "action": "get",
                    "id": captcha_id,
                    "json": 1
                }
                
                try:
                    response = requests.get(result_url, params=params, timeout=15)
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    if result.get("status") == 1:
                        token = result.get("request")
                        if token and len(token) > 50:
                            elapsed = int(time.time() - start_time)
                            logger.success(f"CF токен получен за {elapsed}s: {token[:50]}...",
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            return token
                    
                    elif result.get("request") == "CAPCHA_NOT_READY":
                        elapsed = int(time.time() - start_time)
                        if elapsed % 10 == 0:
                            logger.info(f"Решение обрабатывается... ({elapsed}s/{max_wait_time}s)",
                                       email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    else:
                        error = result.get("request", "Unknown")
                        logger.error(f"Ошибка от 2captcha: {error}",
                                    email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return None
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Временная ошибка запроса к 2captcha: {e}",
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                time.sleep(3)
            
            elapsed = int(time.time() - start_time)
            logger.error(f"Таймаут решения Turnstile ({elapsed}s), отменяем задачу",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            try:
                cancel_url = f"{self.base_url}/res.php"
                cancel_params = {
                    "key": self.api_key,
                    "action": "reportbad",
                    "id": captcha_id
                }
                requests.get(cancel_url, params=cancel_params, timeout=10)
                logger.info(f"Задача {captcha_id} отменена",
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            except:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения результата: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None
    
    def get_balance(self) -> Optional[float]:
        try:
            url = f"{self.base_url}/res.php"
            params = {
                "key": self.api_key,
                "action": "getbalance",
                "json": 1
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("status") == 1:
                balance = float(result.get("request", 0))
                logger.info(f"Баланс 2captcha: ${balance}",
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                return balance
            else:
                error = result.get("request", "Unknown")
                logger.error(f"Ошибка получения баланса: {error}",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка проверки баланса: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None


class TurnstileHandler:
    
    def __init__(self, page, email: str, position: int, total_accounts: int):
        self.page = page
        self.email = email
        self.position = position
        self.total_accounts = total_accounts
        self.cf_solver = CloudflareSolver(email, position, total_accounts)
        
    async def get_cf_token_for_headers(self, proxy: dict = None) -> Optional[str]:
        try:
            logger.info(f"Получение CF токена для HTTP заголовков",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            website_url = config.TURNSTILE_CONFIG.get("website_url", "https://app.psdn.ai/login")
            website_key = config.TURNSTILE_CONFIG.get("website_key", "0x4AAAAAAAg8cKWGcfDpVOT2")
            
            logger.info(f"Параметры Turnstile: URL={website_url}, sitekey={website_key}",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            token = self.cf_solver.solve_turnstile_simple(
                website_url=website_url,
                website_key=website_key,
                proxy=proxy
            )
            
            if token:
                logger.success(f"CF токен получен для заголовков: {token[:50]}...",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return token
            else:
                logger.error(f"Не удалось получить CF токен",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения CF токена: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None
    
    async def detect_turnstile(self, timeout: int = 10) -> bool:
        try:
            logger.info(f"Быстрая проверка наличия Turnstile виджета",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            turnstile_selectors = [
                'iframe[src*="cloudflare"]',
                'iframe[src*="turnstile"]',
                '.cf-turnstile',
                '[data-sitekey]'
            ]
            
            for selector in turnstile_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=timeout * 1000)
                    if element and await element.is_visible():
                        logger.success(f"Turnstile найден: {selector}",
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return True
                except:
                    continue
            
            logger.info(f"Turnstile виджет не обнаружен",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка поиска Turnstile: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
    
    async def get_turnstile_params(self) -> Dict[str, str]:
        try:
            logger.info(f"Извлечение параметров Turnstile со страницы",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            js_code = """
            () => {
                try {
                    const elements = document.querySelectorAll('.cf-turnstile, [data-sitekey]');
                    for (let el of elements) {
                        const sitekey = el.getAttribute('data-sitekey') || el.getAttribute('sitekey');
                        if (sitekey) {
                            return {
                                sitekey: sitekey,
                                url: window.location.href,
                                action: el.getAttribute('data-action') || '',
                                cdata: el.getAttribute('data-cdata') || ''
                            };
                        }
                    }
                    
                    const iframes = document.querySelectorAll('iframe[src*="cloudflare"], iframe[src*="turnstile"]');
                    for (let iframe of iframes) {
                        const src = iframe.src;
                        const params = new URLSearchParams(src.split('?')[1] || '');
                        const sitekey = params.get('sitekey') || params.get('k');
                        if (sitekey) {
                            return {
                                sitekey: sitekey,
                                url: window.location.href,
                                action: params.get('action') || ''
                            };
                        }
                    }
                    
                    return null;
                } catch (error) {
                    return null;
                }
            }
            """
            
            params = await self.page.evaluate(js_code)
            
            if params and params.get('sitekey'):
                logger.success(f"Параметры извлечены: sitekey={params['sitekey'][:20]}...",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return params
            else:
                logger.warning(f"Не удалось извлечь параметры со страницы",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return {}
                
        except Exception as e:
            logger.error(f"Ошибка извлечения параметров: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return {}
    
    async def solve_turnstile_with_2captcha(self, proxy: dict = None) -> Optional[str]:
        try:
            logger.info(f"Решение Turnstile виджета на странице",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            params = await self.get_turnstile_params()
            if not params or not params.get('sitekey'):
                logger.error(f"Параметры Turnstile не найдены на странице",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
            
            website_url = params.get('url', self.page.url)
            website_key = params.get('sitekey')
            
            logger.info(f"Решение с параметрами страницы: {website_key[:20]}...",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            token = self.cf_solver.solve_turnstile_simple(
                website_url=website_url,
                website_key=website_key,
                proxy=proxy
            )
            
            if token:
                logger.success(f"Turnstile решен: {token[:50]}...",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return token
            else:
                logger.error(f"Не удалось решить Turnstile виджет",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка решения Turnstile: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None
    
    async def inject_turnstile_token(self, token: str) -> bool:
        try:
            logger.info(f"Внедрение Turnstile токена",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            js_code = f"""
            (token) => {{
                try {{
                    window.turnstileToken = token;
                    
                    const inputs = document.querySelectorAll('input[name*="turnstile"], input[name*="cf-turnstile"]');
                    inputs.forEach(input => {{
                        input.value = token;
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }});
                    
                    if (typeof window.turnstileCallback === 'function') {{
                        window.turnstileCallback(token);
                    }}
                    
                    const event = new CustomEvent('turnstile-success', {{ detail: {{ token }} }});
                    document.dispatchEvent(event);
                    
                    return true;
                }} catch (error) {{
                    console.error('Ошибка внедрения токена:', error);
                    return false;
                }}
            }}
            """
            
            result = await self.page.evaluate(js_code, token)
            
            if result:
                logger.success(f"Токен успешно внедрен",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            else:
                logger.warning(f"Не удалось внедрить токен",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка внедрения токена: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
    
    async def wait_for_turnstile_and_solve(self, timeout: int = 10, proxy: dict = None) -> bool:
        try:
            logger.info(f"Проверка и решение Turnstile виджета",
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not await self.detect_turnstile(timeout):
                logger.info(f"Turnstile не найден, пропускаем",
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            
            token = await self.solve_turnstile_with_2captcha(proxy)
            if not token:
                logger.error(f"Не удалось получить токен для виджета",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            if await self.inject_turnstile_token(token):
                logger.success(f"Turnstile решен и токен внедрен",
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                await asyncio.sleep(1)
                return True
            else:
                logger.error(f"Токен получен, но не удалось внедрить",
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка обработки Turnstile: {e}",
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False