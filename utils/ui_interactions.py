import asyncio
import random
from logger import get_logger

logger = get_logger('UIInteractions')

class UIInteractions:
    
    def __init__(self, page, email, position, total_accounts):
        self.page = page
        self.email = email
        self.position = position
        self.total_accounts = total_accounts

    async def close_modal_overlay(self) -> bool:
        try:
            logger.info(f"Поиск и закрытие модальных окон", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(2)
            
            close_selectors = [
                'button:has-text("×")',
                'button[aria-label*="close"]',
                'button[aria-label*="Close"]',
                '.fixed.inset-0 button',
                '[class*="z-50"] button',
                'div[class*="fixed inset-0"] button',
                'svg.lucide-x',
                'button:has(svg[class*="lucide-x"])',
                'button.absolute'
            ]
            
            for selector in close_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        try:
                            is_visible = await element.is_visible()
                            if is_visible:
                                await element.click()
                                logger.success(f"Модальное окно закрыто через {selector}", 
                                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                                await asyncio.sleep(1)
                                return True
                        except:
                            continue
                except:
                    continue
            
            try:
                await self.page.keyboard.press('Escape')
                logger.info(f"Попытка закрыть модальное окно через Escape", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                await asyncio.sleep(1)
                return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.warning(f"Ошибка закрытия модального окна: {e}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def accept_terms(self) -> bool:
        try:
            logger.info(f"Поиск и принятие правил пользования", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(2, 4))
            
            current_url = self.page.url
            logger.info(f"Текущий URL при поиске Terms: {current_url}", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            # Если мы уже на странице логина, значит правила уже приняты
            if "/login" in current_url:
                logger.success(f"Уже на странице логина, правила видимо уже приняты", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            
            # Если мы на странице интро без правил, тоже продолжаем
            if "/intro" in current_url and "Terms and Conditions" not in await self.page.content():
                logger.success(f"На странице интро без правил, продолжаем", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            
            page_content = await self.page.content()
            logger.info(f"Проверяем наличие Terms and Conditions на странице", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if "Terms and Conditions" not in page_content:
                logger.warning(f"Текст Terms and Conditions НЕ найден на странице, пропускаем этот шаг", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            
            logger.info(f"Найден текст Terms and Conditions", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            checkbox_selectors = [
                'input[type="checkbox"]',
                'label:has-text("I agree with the") input[type="checkbox"]',
                'label:has-text("Terms and Conditions") input[type="checkbox"]',
                '[class*="checkbox"]',
                'input[name*="terms"]',
                'input[name*="agree"]'
            ]
            
            success = False
            for selector in checkbox_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        logger.info(f"Найден чекбокс через селектор: {selector}, количество: {len(elements)}", 
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
                        
                        for element in elements:
                            try:
                                is_visible = await element.is_visible()
                                logger.info(f"Элемент видимый: {is_visible}", 
                                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                                if is_visible:
                                    await element.click()
                                    logger.success(f"Чекбокс нажат через {selector}", 
                                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                                    await asyncio.sleep(random.uniform(0.5, 1))
                                    success = True
                                    break
                            except Exception as e:
                                logger.warning(f"Ошибка клика по чекбоксу: {e}")
                                continue
                        
                        if success:
                            break
                    else:
                        logger.info(f"Селектор {selector} не нашел элементов", 
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
                except Exception as e:
                    logger.warning(f"Ошибка с селектором {selector}: {e}")
                    continue
            
            if not success:
                all_inputs = await self.page.query_selector_all('input')
                logger.info(f"Поиск среди всех {len(all_inputs)} input элементов", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                for i, input_elem in enumerate(all_inputs):
                    try:
                        input_type = await input_elem.get_attribute('type')
                        if input_type == 'checkbox':
                            is_visible = await input_elem.is_visible()
                            logger.info(f"Найден checkbox input[{i}], видимый: {is_visible}", 
                                       email=self.email, position=f"{self.position}/{self.total_accounts}")
                            if is_visible:
                                await input_elem.click()
                                logger.success(f"Чекбокс найден как input[{i}] и нажат", 
                                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                                success = True
                                break
                    except Exception as e:
                        logger.warning(f"Ошибка с input[{i}]: {e}")
                        continue
            
            if success:
                await asyncio.sleep(random.uniform(0.3, 0.7))
                logger.success(f"Правила пользования приняты", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            else:
                logger.warning(f"Чекбокс согласия не найден, но страница не содержит Terms - пропускаем", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            
        except Exception as e:
            logger.error(f"Ошибка принятия правил: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def wait_for_element_and_click(self, selectors, element_name, timeout=10000):
        try:
            for selector in selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=timeout)
                    if element and await element.is_visible():
                        logger.success(f"Найден {element_name}: {selector}", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        await element.click()
                        return True
                except:
                    continue
            return False
        except Exception as e:
            logger.warning(f"Ошибка поиска {element_name}: {e}")
            return False

    async def click_get_started_button(self) -> bool:
        try:
            logger.info(f"Поиск и нажатие кнопки Get Started", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            get_started_selectors = [
                'button:has-text("Get Started")',
                'button.inline-flex.items-center.justify-center:has-text("Get Started")',
                'button[class*="bg-white"][class*="text-black"]:has-text("Get Started")',
                'button.cursor-pointer:has-text("Get Started")',
                'button.rounded-full:has-text("Get Started")'
            ]
            
            success = await self.wait_for_element_and_click(get_started_selectors, "Кнопка Get Started")
            if success:
                await self.page.wait_for_load_state("networkidle", timeout=35000)
                await asyncio.sleep(random.uniform(1, 2))
                logger.success(f"Кнопка Get Started нажата успешно", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка нажатия кнопки Get Started: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def click_continue_button(self) -> bool:
        try:
            logger.info(f"Поиск и нажатие кнопки Continue", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            continue_selectors = [
                'button[type="submit"][data-testid="submit_button"]',
                'button:has-text("Continue")',
                'button.button--brand-primary:has-text("Continue")',
                'button.login-with-email-form__button',
                '[data-testid="submit_button"]'
            ]
            
            success = await self.wait_for_element_and_click(continue_selectors, "Кнопка Continue")
            if success:
                await asyncio.sleep(random.uniform(1, 2))
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка нажатия кнопки Continue: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def click_terms_confirmation_button(self) -> bool:
        try:
            logger.info(f"Поиск и нажатие кнопки подтверждения правил", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(1, 2))
            
            confirmation_selectors = [
                'button:has-text("Continue")',
                'button:has-text("Accept")',
                'button:has-text("Agree")',
                'button:has-text("Next")',
                'button:has-text("Proceed")',
                'button[type="submit"]',
                'button.btn-primary',
                'button[class*="primary"]',
                'button[class*="continue"]',
                'button[class*="accept"]',
                'button[class*="agree"]',
                '[data-testid="continue"]',
                '[data-testid="accept"]',
                'button.inline-flex.items-center.justify-center'
            ]
            
            for attempt in range(3):
                logger.info(f"Попытка #{attempt + 1} поиска кнопки подтверждения правил", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                for selector in confirmation_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=3000)
                        if element and await element.is_visible():
                            element_text = await element.text_content()
                            logger.success(f"Найдена кнопка подтверждения: {selector}, текст: '{element_text}'", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await element.click()
                            logger.success(f"Кнопка подтверждения правил нажата", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await asyncio.sleep(random.uniform(1, 2))
                            
                            current_url = self.page.url
                            logger.info(f"После подтверждения правил URL: {current_url}", 
                                       email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            return True
                            
                    except Exception as e:
                        logger.warning(f"Селектор {selector} не сработал: {e}")
                        continue
                
                if attempt < 2:
                    await asyncio.sleep(2)
            
            logger.warning(f"Кнопка подтверждения правил не найдена, продолжаем без нее", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return True
            
        except Exception as e:
            logger.warning(f"Ошибка поиска кнопки подтверждения правил: {e}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return True