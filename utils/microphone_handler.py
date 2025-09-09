import asyncio
import random
from logger import get_logger

logger = get_logger('MicrophoneHandler')

class MicrophoneHandler:
    
    def __init__(self, page, email, position, total_accounts):
        self.page = page
        self.email = email
        self.position = position
        self.total_accounts = total_accounts

    @staticmethod
    def get_camoufox_microphone_preferences():
        """Возвращает настройки Firefox для автоматического разрешения микрофона в Camoufox"""
        return {
            # Отключить запросы разрешений микрофона полностью
            'media.navigator.permission.disabled': True,
            
            # Разрешения по умолчанию (1 = разрешить, 2 = запретить)  
            'permissions.default.microphone': 1,
            'permissions.default.camera': 1,
            
            # Использовать фиктивные устройства для медиа
            'media.navigator.streams.fake': True,
            'media.gmp-manager.updateEnabled': False,
            
            # Дополнительные настройки медиа
            'media.autoplay.default': 0,  # 0 = разрешить автовоспроизведение
            'media.autoplay.blocking_policy': 0,
            
            # Отключить уведомления о доступе к микрофону
            'privacy.webrtc.legacyGlobalIndicator': False,
            'privacy.webrtc.hideGlobalIndicator': True,
            
            # Настройки WebRTC
            'media.peerconnection.enabled': True,
            'media.peerconnection.use_document_iceservers': True,
        }

    async def setup_microphone_permissions(self):
        try:
            logger.info(f"Настройка разрешений для микрофона через JavaScript", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            js_code = """
            // Переопределяем permissions API для автоматического разрешения
            if (navigator.permissions && navigator.permissions.query) {
                const originalQuery = navigator.permissions.query;
                navigator.permissions.query = function(permissionDesc) {
                    if (permissionDesc.name === 'microphone' || permissionDesc.name === 'camera') {
                        return Promise.resolve({ state: 'granted', onchange: null });
                    }
                    return originalQuery.call(this, permissionDesc);
                };
            }
            
            // Переопределяем getUserMedia для автоматического предоставления потока
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
                navigator.mediaDevices.getUserMedia = function(constraints) {
                    console.log('getUserMedia вызван с ограничениями:', constraints);
                    
                    if (constraints && (constraints.audio || constraints.video)) {
                        // Создаем фиктивный MediaStream
                        const stream = {
                            getTracks: () => {
                                const tracks = [];
                                if (constraints.audio) {
                                    tracks.push({ 
                                        kind: 'audio', 
                                        label: 'Virtual Microphone', 
                                        enabled: true,
                                        stop: () => console.log('Audio track stopped'),
                                        getSettings: () => ({ deviceId: 'virtual-mic' })
                                    });
                                }
                                if (constraints.video) {
                                    tracks.push({ 
                                        kind: 'video', 
                                        label: 'Virtual Camera', 
                                        enabled: true,
                                        stop: () => console.log('Video track stopped'),
                                        getSettings: () => ({ deviceId: 'virtual-cam' })
                                    });
                                }
                                return tracks;
                            },
                            getAudioTracks: () => constraints.audio ? [{ 
                                kind: 'audio', 
                                label: 'Virtual Microphone', 
                                enabled: true,
                                stop: () => {},
                                getSettings: () => ({ deviceId: 'virtual-mic' })
                            }] : [],
                            getVideoTracks: () => constraints.video ? [{ 
                                kind: 'video', 
                                label: 'Virtual Camera', 
                                enabled: true,
                                stop: () => {},
                                getSettings: () => ({ deviceId: 'virtual-cam' })
                            }] : [],
                            stop: () => console.log('Virtual MediaStream stopped'),
                            addTrack: () => {},
                            removeTrack: () => {},
                            addEventListener: () => {},
                            removeEventListener: () => {},
                            active: true,
                            id: 'virtual-stream-' + Math.random()
                        };
                        
                        console.log('Возвращаем фиктивный MediaStream');
                        return Promise.resolve(stream);
                    }
                    
                    return originalGetUserMedia ? originalGetUserMedia.call(this, constraints) : 
                           Promise.reject(new Error('getUserMedia not supported'));
                };
            }
            
            // Переопределяем enumerateDevices для показа виртуальных устройств
            if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
                const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
                navigator.mediaDevices.enumerateDevices = function() {
                    return Promise.resolve([
                        {
                            deviceId: 'virtual-mic',
                            kind: 'audioinput',
                            label: 'Virtual Microphone',
                            groupId: 'virtual-group'
                        },
                        {
                            deviceId: 'virtual-cam', 
                            kind: 'videoinput',
                            label: 'Virtual Camera',
                            groupId: 'virtual-group'
                        }
                    ]);
                };
            }
            
            console.log('Все медиа API переопределены для автоматического разрешения');
            """
            
            await self.page.evaluate(js_code)
            logger.success(f"JavaScript разрешения на микрофон настроены", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return True
            
        except Exception as e:
            logger.warning(f"Ошибка настройки JavaScript разрешений микрофона: {e}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def handle_microphone_dialog(self):
        try:
            logger.info(f"Настройка обработчика диалогов для микрофона", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            async def handle_dialog(dialog):
                try:
                    dialog_message = dialog.message
                    logger.info(f"Получен диалог: {dialog_message}", 
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    await dialog.accept()
                    logger.success(f"Диалог автоматически принят", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                except Exception as e:
                    logger.warning(f"Ошибка обработки диалога: {e}")
            
            self.page.on("dialog", handle_dialog)
            logger.info(f"Обработчик диалогов установлен", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            return True
            
        except Exception as e:
            logger.warning(f"Ошибка установки обработчика диалогов: {e}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def handle_browser_microphone_permission(self) -> bool:
        try:
            logger.info(f"Обработка разрешения микрофона в браузере", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            # С правильными Firefox preferences браузерный диалог вообще не должен появляться
            logger.info(f"Ожидание автоматического разрешения микрофона через Firefox preferences", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            # Ждем изменения на странице
            for wait_attempt in range(30):
                await asyncio.sleep(1)
                
                page_content = await self.page.content()
                current_url = self.page.url
                
                # Если появилась кнопка I'm ready - успех
                if "I'm ready" in page_content:
                    logger.success(f"Кнопка I'm ready появилась - разрешение получено!", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return True
                
                # Если исчез текст запроса доступа и мы не на логине - тоже успех  
                if "Requesting access" not in page_content and "/login" not in current_url:
                    logger.success(f"Запрос доступа исчез, микрофон разрешен", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return True
                
                # Если попали на логин - провал
                if "/login" in current_url:
                    logger.error(f"Попали на страницу логина - разрешение не получено", 
                                email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return False
                
                logger.info(f"Ожидание #{wait_attempt + 1}/30...", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            logger.error(f"Не удалось получить разрешение микрофона за 30 секунд", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Критическая ошибка обработки разрешения микрофона: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def click_allow_microphone_button(self) -> bool:
        try:
            logger.info(f"Поиск и нажатие кнопки Allow microphone", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await self.setup_microphone_permissions()
            await self.handle_microphone_dialog()
            
            microphone_selectors = [
                'button:has-text("Allow microphone")',
                'button.inline-flex.items-center.justify-center:has-text("Allow microphone")',
                'button[class*="cursor-pointer"]:has-text("Allow microphone")',
                'button.rounded-full:has-text("Allow microphone")',
                '[class*="button"]:has-text("Allow microphone")'
            ]
            
            for attempt in range(3):
                logger.info(f"Попытка #{attempt + 1} поиска кнопки Allow microphone", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                for selector in microphone_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=5000)
                        if element and await element.is_visible():
                            logger.success(f"Найдена кнопка Allow microphone: {selector}", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await element.click()
                            
                            logger.success(f"Кнопка Allow microphone нажата", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            # С Firefox preferences диалог не должен появиться
                            permission_result = await self.handle_browser_microphone_permission()
                            
                            if not permission_result:
                                logger.error(f"Не удалось получить разрешение микрофона", 
                                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                                continue
                            
                            current_url = self.page.url
                            logger.info(f"После Allow microphone URL: {current_url}", 
                                       email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            return True
                            
                    except Exception as e:
                        logger.warning(f"Селектор {selector} не сработал: {e}")
                        continue
                
                if attempt < 2:
                    await asyncio.sleep(3)
            
            logger.error(f"Кнопка Allow microphone не найдена после всех попыток", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка нажатия кнопки Allow microphone: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def click_im_ready_button(self) -> bool:
        try:
            logger.info(f"Поиск и нажатие кнопки I'm ready", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(2, 4))
            
            im_ready_selectors = [
                'button:has-text("I\'m ready!")',
                'button.inline-flex.items-center.justify-center:has-text("I\'m ready!")',
                'button[class*="cursor-pointer"]:has-text("I\'m ready!")',
                'button.rounded-full:has-text("I\'m ready!")',
                'button[class*="bg-white"][class*="text-black"]:has-text("I\'m ready!")',
                'button[class*="border-white"]:has-text("I\'m ready!")'
            ]
            
            for attempt in range(3):
                logger.info(f"Попытка #{attempt + 1} поиска кнопки I'm ready", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                for selector in im_ready_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=5000)
                        if element and await element.is_visible():
                            logger.success(f"Найдена кнопка I'm ready: {selector}", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await element.click()
                            
                            logger.success(f"Кнопка I'm ready нажата", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            await asyncio.sleep(30)
                            
                            current_url = self.page.url
                            logger.info(f"После I'm ready и ожидания 30 секунд URL: {current_url}", 
                                       email=self.email, position=f"{self.position}/{self.total_accounts}")
                            
                            return True
                            
                    except Exception as e:
                        logger.warning(f"Селектор {selector} не сработал: {e}")
                        continue
                
                if attempt < 2:
                    await asyncio.sleep(3)
            
            logger.error(f"Кнопка I'm ready не найдена после всех попыток", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка нажатия кнопки I'm ready: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def wait_for_microphone_page_and_proceed(self) -> bool:
        try:
            logger.info(f"Ожидание и обработка страницы с микрофоном", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            await asyncio.sleep(random.uniform(2, 4))
            
            page_content = await self.page.content()
            if "microphone" in page_content.lower() or "allow microphone" in page_content.lower():
                logger.info(f"Обнаружена страница с запросом микрофона", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                if await self.click_allow_microphone_button():
                    logger.success(f"Разрешение микрофона успешно обработано", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    if await self.click_im_ready_button():
                        logger.success(f"Кнопка I'm ready успешно нажата и выждано 30 секунд", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return True
                    else:
                        logger.warning(f"Не удалось нажать кнопку I'm ready", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return False
                else:
                    logger.warning(f"Не удалось нажать кнопку Allow microphone", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return False
            else:
                logger.info(f"Страница с микрофоном не обнаружена, проверяем наличие I'm ready", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                if "I'm ready" in page_content or "ready" in page_content.lower():
                    if await self.click_im_ready_button():
                        logger.success(f"Кнопка I'm ready найдена и нажата", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return True
                
                logger.info(f"Страница с микрофоном и I'm ready не обнаружена, продолжаем", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                return True
                
        except Exception as e:
            logger.warning(f"Ошибка обработки страницы с микрофоном: {e}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")
            return True