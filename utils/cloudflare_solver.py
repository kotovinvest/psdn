import asyncio
import time
import random
import requests
from utils.logger import get_logger
from utils import config

logger = get_logger('CloudflareSolver')

class CloudflareSolver:
    def __init__(self, email, position, total_accounts):
        self.email = email
        self.position = position
        self.total_accounts = total_accounts
        self.api_key = config.TWOCAPTCHA_API_KEY
        self.site_key = config.CLOUDFLARE_SITE_KEY
        self.page_url = config.CLOUDFLARE_PAGE_URL

    def get_balance(self):
        try:
            url = f"http://2captcha.com/res.php?key={self.api_key}&action=getbalance"
            response = requests.get(url)
            if response.text.startswith("OK|"):
                balance = float(response.text.split("|")[1])
                logger.info(f"Баланс 2Captcha: ${balance}", email=self.email, position=f"{self.position}/{self.total_accounts}")
                return balance
            else:
                logger.error(f"Ошибка получения баланса 2Captcha: {response.text}", email=self.email, position=f"{self.position}/{self.total_accounts}")
                return None
        except Exception as e:
            logger.error(f"Исключение при получении баланса 2Captcha: {e}", email=self.email, position=f"{self.position}/{self.total_accounts}")
            return None

    async def solve_cloudflare_challenge(self) -> str:
        try:
            logger.info(f"Начинаем решение Cloudflare Turnstile", email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not self.api_key:
                logger.error(f"2Captcha API ключ не установлен в config.py", email=self.email, position=f"{self.position}/{self.total_accounts}")
                return ""
            
            if not self.site_key:
                logger.error(f"Cloudflare Site Key не установлен в config.py", email=self.email, position=f"{self.position}/{self.total_accounts}")
                return ""
            
            if not self.page_url:
                logger.error(f"Cloudflare Page URL не установлен в config.py", email=self.email, position=f"{self.position}/{self.total_accounts}")
                return ""

            # Отправка запроса на решение капчи
            submit_url = f"http://2captcha.com/in.php?key={self.api_key}&method=turnstile&sitekey={self.site_key}&pageurl={self.page_url}"
            response = requests.get(submit_url)
            
            if response.text.startswith("OK|"):
                request_id = response.text.split("|")[1]
                logger.info(f"Капча отправлена, ID запроса: {request_id}", email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                # Ожидание результата
                for _ in range(config.CAPTCHA_MAX_RETRIES):
                    await asyncio.sleep(config.CAPTCHA_POLL_INTERVAL)
                    result_url = f"http://2captcha.com/res.php?key={self.api_key}&action=get&id={request_id}"
                    result_response = requests.get(result_url)
                    
                    if result_response.text == "CAPCHA_NOT_READY":
                        logger.info(f"Капча еще не готова, ждем...", email=self.email, position=f"{self.position}/{self.total_accounts}")
                        continue
                    elif result_response.text.startswith("OK|"):
                        token = result_response.text.split("|")[1]
                        logger.success(f"Капча успешно решена", email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return token
                    else:
                        logger.error(f"Ошибка при получении результата капчи: {result_response.text}", email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return ""
                logger.error(f"Не удалось решить капчу за отведенное время", email=self.email, position=f"{self.position}/{self.total_accounts}")
                return ""
            else:
                logger.error(f"Ошибка при отправке капчи: {response.text}", email=self.email, position=f"{self.position}/{self.total_accounts}")
                return ""
        except Exception as e:
            logger.error(f"Исключение при решении Cloudflare Turnstile: {e}", email=self.email, position=f"{self.position}/{self.total_accounts}")
            return ""

