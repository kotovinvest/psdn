import asyncio
import json
import base64
import time
from typing import Optional
from logger import get_logger

logger = get_logger('TokenManager')

class TokenManager:
    
    def __init__(self, page, email, position, total_accounts):
        self.page = page
        self.email = email
        self.position = position
        self.total_accounts = total_accounts
        self.auth_token = None
        self.turnstile_token = None

    async def extract_auth_token_from_storage(self):
        try:
            js_code = '''
            (() => {
                try {
                    const allKeys = [];
                    for (let i = 0; i < localStorage.length; i++) {
                        allKeys.push(localStorage.key(i));
                    }
                    for (let i = 0; i < sessionStorage.length; i++) {
                        allKeys.push('session_' + sessionStorage.key(i));
                    }
                    
                    let authToken = localStorage.getItem('dynamic_authentication_token') || 
                                   sessionStorage.getItem('dynamic_authentication_token') ||
                                   localStorage.getItem('dynamic_min_authentication_token') ||
                                   sessionStorage.getItem('dynamic_min_authentication_token');
                    
                    if (!authToken) {
                        const possibleTokens = [
                            localStorage.getItem('authToken'),
                            sessionStorage.getItem('authToken'),
                            localStorage.getItem('jwt'), 
                            sessionStorage.getItem('jwt'),
                            localStorage.getItem('dynamic-session-token'),
                            sessionStorage.getItem('dynamic-session-token'),
                            localStorage.getItem('access_token'),
                            sessionStorage.getItem('access_token'),
                            localStorage.getItem('authentication_token'),
                            sessionStorage.getItem('authentication_token'),
                            localStorage.getItem('auth'),
                            sessionStorage.getItem('auth'),
                            localStorage.getItem('token'),
                            sessionStorage.getItem('token')
                        ].filter(Boolean);
                        
                        for (let token of possibleTokens) {
                            if (token && token.startsWith('eyJ')) {
                                authToken = token;
                                break;
                            }
                        }
                    }
                    
                    let turnstileToken = localStorage.getItem('cf.turnstile.u') ||
                                       sessionStorage.getItem('cf.turnstile.u');
                    
                    if (!turnstileToken) {
                        const debugKeys = [];
                        for (let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            if (key && (key.includes('turnstile') || key.includes('cf') || key.includes('CF'))) {
                                debugKeys.push({key: key, value: localStorage.getItem(key)?.substring(0, 50)});
                            }
                        }
                        console.log('Debug turnstile keys:', debugKeys);
                        
                        for (let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            if (key && (key.includes('turnstile') || key.includes('cf.') || key.includes('CF.'))) {
                                turnstileToken = localStorage.getItem(key);
                                if (turnstileToken) {
                                    console.log('Found turnstile token in key:', key);
                                    break;
                                }
                            }
                        }
                        
                        if (!turnstileToken) {
                            for (let i = 0; i < sessionStorage.length; i++) {
                                const key = sessionStorage.key(i);
                                if (key && (key.includes('turnstile') || key.includes('cf.') || key.includes('CF.'))) {
                                    turnstileToken = sessionStorage.getItem(key);
                                    if (turnstileToken) {
                                        console.log('Found turnstile token in sessionStorage key:', key);
                                        break;
                                    }
                                }
                            }
                        }
                    }
                    
                    const allStorageKeys = [];
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        allStorageKeys.push({
                            storage: 'localStorage',
                            key: key,
                            value: localStorage.getItem(key)?.substring(0, 100)
                        });
                    }
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        allStorageKeys.push({
                            storage: 'sessionStorage',
                            key: key,
                            value: sessionStorage.getItem(key)?.substring(0, 100)
                        });
                    }
                    
                    return {
                        authToken: authToken,
                        turnstileToken: turnstileToken,
                        allKeys: allKeys,
                        authTokenLength: authToken ? authToken.length : 0,
                        turnstileTokenLength: turnstileToken ? turnstileToken.length : 0,
                        allStorageKeys: allStorageKeys
                    };
                } catch (error) {
                    console.error('Error extracting tokens:', error);
                    return null;
                }
            })();
            '''
            
            result = await self.page.evaluate(js_code)
            
            if result:
                if result.get('authToken'):
                    token = result['authToken']
                    if token.startswith('"') and token.endswith('"'):
                        token = token[1:-1]
                    self.auth_token = token
                    logger.success(f"Auth token извлечен: {self.auth_token[:50]}... (длина: {result.get('authTokenLength')})", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    token_parts = self.auth_token.split('.')
                    logger.info(f"Количество частей JWT: {len(token_parts)}", 
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    if len(token_parts) >= 1:
                        logger.info(f"Первая часть токена (header): {token_parts[0][:50]}...", 
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    if len(self.auth_token) < 500:
                        logger.warning(f"Токен подозрительно короткий: {len(self.auth_token)} символов", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                if result.get('turnstileToken'):
                    self.turnstile_token = result['turnstileToken']
                    logger.success(f"Turnstile token извлечен: {self.turnstile_token[:50]}... (длина: {result.get('turnstileTokenLength')})", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                else:
                    logger.warning(f"Turnstile токен не найден! Проверяем все ключи storage", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    all_storage = result.get('allStorageKeys', [])
                    cf_keys = [item for item in all_storage if 'cf' in item['key'].lower() or 'turnstile' in item['key'].lower()]
                    
                    if cf_keys:
                        logger.info(f"Найдены CF/Turnstile ключи в storage:", 
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
                        for item in cf_keys:
                            logger.info(f"  {item['storage']} - {item['key']}: {item['value'][:50]}...", 
                                       email=self.email, position=f"{self.position}/{self.total_accounts}")
                    else:
                        logger.warning(f"Ключи с CF/Turnstile не найдены в storage", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        
                        logger.info(f"Все ключи в storage ({len(all_storage)} всего):", 
                                   email=self.email, position=f"{self.position}/{self.total_accounts}")
                        for i, item in enumerate(all_storage[:10]):
                            logger.info(f"  {item['storage']} - {item['key']}: {item['value'][:30]}...", 
                                       email=self.email, position=f"{self.position}/{self.total_accounts}")
                        if len(all_storage) > 10:
                            logger.info(f"  ... и еще {len(all_storage) - 10} ключей", 
                                       email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                logger.info(f"Поиск токенов завершен. Auth: {'Да' if result.get('authToken') else 'Нет'}, Turnstile: {'Да' if result.get('turnstileToken') else 'Нет'}", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                return bool(self.auth_token)
            else:
                logger.error(f"Токены не найдены", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка извлечения токенов: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    async def debug_token(self):
        try:
            if not self.page:
                logger.error(f"Page object is None в debug_token", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
                
            logger.info(f"Отладка токена", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            if not self.auth_token:
                logger.error(f"Токен отсутствует", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            token_parts = self.auth_token.split('.')
            if len(token_parts) != 3:
                logger.error(f"Неправильная структура JWT: {len(token_parts)} частей", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            try:
                header_b64 = token_parts[0]
                while len(header_b64) % 4:
                    header_b64 += '='
                
                header_decoded = base64.b64decode(header_b64)
                header_json = json.loads(header_decoded)
                logger.info(f"JWT Header: {header_json}", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
            except Exception as e:
                logger.error(f"Ошибка декодирования header: {e}", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            try:
                payload_b64 = token_parts[1]
                while len(payload_b64) % 4:
                    payload_b64 += '='
                
                payload_decoded = base64.b64decode(payload_b64)
                payload_json = json.loads(payload_decoded)
                
                current_time = int(time.time())
                exp_time = payload_json.get('exp', 0)
                
                logger.info(f"Токен истекает: {exp_time}, текущее время: {current_time}", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
                if exp_time < current_time:
                    logger.error(f"Токен истек!", 
                                email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return False
                
                logger.info(f"Токен валиден, осталось {exp_time - current_time} секунд", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
                
            except Exception as e:
                logger.error(f"Ошибка декодирования payload: {e}", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отладки токена: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return False

    def get_token(self) -> Optional[str]:
        return self.auth_token

    def get_turnstile_token(self) -> Optional[str]:
        return self.turnstile_token