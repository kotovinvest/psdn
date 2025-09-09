import imaplib
import email
import time
import re
from datetime import datetime, timezone
from typing import Optional

from logger import get_logger
from utils import config

logger = get_logger('EmailManager')

class EmailManager:
    
    def __init__(self, email_address: str, password: str):
        self.email_address = email_address
        self.password = password
        
        logger.info(f"Email менеджер инициализирован для {email_address}", email=email_address)
    
    def _extract_code_from_email(self, email_message) -> Optional[str]:
        try:
            body = ""
            subject = email_message.get('Subject', '')
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    elif part.get_content_type() == "text/html":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                else:
                    body = ""
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            full_text = f"{subject} {body}"
            
            patterns = [
                r'(\d{6}) is your verification code',
                r'verification code:\s*(\d{6})',
                r'code:\s*(\d{6})',
                r'Your code is:\s*(\d{6})',
                r'>(\d{6})<',
                r'\b(\d{6})\b'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    code = match.group(1)
                    if len(code) == 6 and code.isdigit():
                        return code
            
            all_codes = re.findall(r'\b(\d{6})\b', full_text)
            if all_codes:
                return all_codes[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка извлечения кода: {e}", email=self.email_address)
            return None
    
    def get_verification_code(self, after_time: float, max_wait_time: int = 120) -> Optional[str]:
        logger.info(f"Поиск кода подтверждения после {datetime.fromtimestamp(after_time).strftime('%H:%M:%S')}", 
                   email=self.email_address)
        
        # Добавляем задержку 10 секунд после отправки, чтобы дать время письму дойти
        logger.info("Ожидание 10 секунд для доставки письма...", email=self.email_address)
        time.sleep(10)
        
        mail = None
        start_time = time.time()
        
        try:
            mail = imaplib.IMAP4_SSL('imap.gmx.com', 993)
            mail.login(self.email_address, self.password)
            mail.select('inbox')
            
            processed_messages = set()
            
            while time.time() - start_time < max_wait_time:
                try:
                    status, messages = mail.search(None, 'ALL')
                    
                    if status == 'OK' and messages[0]:
                        message_ids = messages[0].split()
                        
                        for msg_id in reversed(message_ids[-10:]):
                            msg_id_str = msg_id.decode('utf-8')
                            
                            if msg_id_str in processed_messages:
                                continue
                            
                            try:
                                status, msg_data = mail.fetch(msg_id, '(RFC822)')
                                if status == 'OK':
                                    email_message = email.message_from_bytes(msg_data[0][1])
                                    
                                    date_header = email_message.get('Date')
                                    if date_header:
                                        try:
                                            msg_time = email.utils.parsedate_to_datetime(date_header)
                                            
                                            # Преобразуем время письма в UTC timestamp
                                            if msg_time.tzinfo is not None:
                                                # Если есть информация о часовом поясе, используем её
                                                msg_timestamp = msg_time.timestamp()
                                            else:
                                                # Если нет информации о часовом поясе, предполагаем UTC
                                                msg_time_utc = msg_time.replace(tzinfo=timezone.utc)
                                                msg_timestamp = msg_time_utc.timestamp()
                                            
                                            # Добавляем более мягкое условие проверки времени
                                            # Учитываем возможные расхождения в часовых поясах (до 12 часов)
                                            # и добавляем буфер в 5 минут назад от времени отправки
                                            time_buffer = 5 * 60  # 5 минут в секундах
                                            timezone_buffer = 12 * 60 * 60  # 12 часов в секундах
                                            
                                            # Письмо считается подходящим если:
                                            # 1. Оно пришло после (after_time - time_buffer - timezone_buffer)
                                            # 2. Или оно пришло после (after_time - time_buffer + timezone_buffer) для обратного смещения
                                            min_time_1 = after_time - time_buffer - timezone_buffer
                                            min_time_2 = after_time - time_buffer + timezone_buffer
                                            min_time_3 = after_time - time_buffer  # без учета часовых поясов
                                            
                                            msg_time_local = datetime.fromtimestamp(msg_timestamp)
                                            after_time_local = datetime.fromtimestamp(after_time)
                                            
                                            if (msg_timestamp < min_time_1 and 
                                                msg_timestamp < min_time_2 and 
                                                msg_timestamp < min_time_3):
                                                logger.info(f"Письмо от {msg_time_local.strftime('%H:%M:%S')} слишком старое "
                                                           f"(отправка была в {after_time_local.strftime('%H:%M:%S')}), пропускаем", 
                                                           email=self.email_address)
                                                processed_messages.add(msg_id_str)
                                                continue
                                            
                                            logger.info(f"Проверяем письмо от {msg_time_local.strftime('%H:%M:%S')} "
                                                       f"(отправка была в {after_time_local.strftime('%H:%M:%S')})", 
                                                       email=self.email_address)
                                                
                                        except Exception as e:
                                            logger.warning(f"Ошибка парсинга даты письма: {e}", email=self.email_address)
                                            # Если не можем определить время, проверяем письмо
                                            logger.info("Не удалось определить время письма, проверяем его", 
                                                       email=self.email_address)
                                    
                                    sender = email_message.get('From', 'Unknown Sender')
                                    subject = email_message.get('Subject', 'No Subject')
                                    
                                    if any(keyword in subject.lower() for keyword in ['dynamic', 'verification', 'code', 'psdn']):
                                        code = self._extract_code_from_email(email_message)
                                        processed_messages.add(msg_id_str)
                                        
                                        if code:
                                            logger.success(f"Найден код: {code} | От: {sender} | Тема: {subject}", 
                                                          email=self.email_address)
                                            return code
                                        else:
                                            logger.info(f"Релевантное письмо без кода от {sender}: {subject[:50]}...", 
                                                       email=self.email_address)
                                    else:
                                        processed_messages.add(msg_id_str)
                            
                            except Exception as e:
                                logger.warning(f"Ошибка обработки сообщения {msg_id_str}: {e}", 
                                              email=self.email_address)
                                continue
                    
                    elapsed = time.time() - start_time
                    remaining = max_wait_time - elapsed
                    
                    if remaining > 0:
                        logger.info(f"Ожидание кода... Осталось: {remaining:.0f}s", 
                                   email=self.email_address)
                        time.sleep(5)
                    else:
                        break
                        
                except Exception as e:
                    logger.error(f"Ошибка проверки почты: {e}", email=self.email_address)
                    time.sleep(10)
                    
                    try:
                        mail.logout()
                    except:
                        pass
                    
                    try:
                        mail = imaplib.IMAP4_SSL('imap.gmx.com', 993)
                        mail.login(self.email_address, self.password)
                        mail.select('inbox')
                    except Exception as reconnect_error:
                        logger.error(f"Ошибка переподключения: {reconnect_error}", 
                                    email=self.email_address)
                        break
            
            logger.warning(f"Код не найден за {max_wait_time} секунд", email=self.email_address)
            return None
            
        except Exception as e:
            logger.error(f"Критическая ошибка получения кода: {e}", email=self.email_address)
            return None
        
        finally:
            if mail:
                try:
                    mail.logout()
                except:
                    pass