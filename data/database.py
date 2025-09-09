import json
import os
import threading
import random
import time
from typing import Dict, List, Optional
from datetime import datetime

from logger import get_logger
from utils.voice_models import get_random_voice_config

logger = get_logger('Database')

class Database:
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.lock = threading.Lock()
        self.data = self.load_db()
        
        logger.info(f"База данных инициализирована: {len(self.data)} записей")
        
        self.validate_data()
        self.good_proxies_cache = []
    
    def validate_data(self):
        try:
            fixed_accounts = 0
            for email, account_data in self.data.items():
                if not isinstance(account_data, dict):
                    logger.warning(f"Некорректные данные для аккаунта {email[:20]}..., восстанавливаем")
                    self.data[email] = self._create_default_account_data()
                    fixed_accounts += 1
                    continue
                
                required_fields = {
                    "email": "",
                    "login": "",
                    "password": "",
                    "proxy": {},
                    "authorized": False,
                    "last_activity": "",
                    "created_at": "",
                    "stats": {"successful_logins": 0, "failed_logins": 0, "total_sessions": 0},
                    "voice_config": {}
                }
                
                updated = False
                for field, default_value in required_fields.items():
                    if field not in account_data:
                        if field == "voice_config":
                            account_data[field] = get_random_voice_config()
                        else:
                            account_data[field] = default_value
                        updated = True
                
                if not account_data.get("browser_profile"):
                    account_data["browser_profile"] = {}
                    updated = True
                
                if updated:
                    fixed_accounts += 1
            
            if fixed_accounts > 0:
                logger.info(f"Исправлены данные для {fixed_accounts} аккаунтов")
                
        except Exception as e:
            logger.error(f"Ошибка валидации данных: {e}")
    
    def load_proxies_cache(self, proxies: List[Dict] = None):
        try:
            if proxies:
                self.good_proxies_cache = [p for p in proxies]
                logger.success(f"Загружено {len(proxies)} прокси в кэш")
                return
                
            from utils import config
            
            if not config.USE_PROXIES:
                logger.info("Прокси отключены в настройках")
                return
            
            proxy_file = config.PROXY_FILE
            if not os.path.exists(proxy_file):
                logger.warning(f"Файл прокси {proxy_file} не найден")
                return
            
            with open(proxy_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            
            proxies_loaded = []
            
            for line in lines:
                try:
                    if "@" in line and ":" in line:
                        auth_part, server_part = line.split("@")
                        username, password = auth_part.split(":")
                        ip, port = server_part.split(":")
                        
                        proxy_dict = {
                            "http": f"http://{username}:{password}@{ip}:{port}",
                            "https": f"http://{username}:{password}@{ip}:{port}"
                        }
                        
                        proxies_loaded.append(proxy_dict)
                        
                except Exception as e:
                    logger.warning(f"Ошибка парсинга прокси '{line}': {e}")
                    continue
            
            self.good_proxies_cache = proxies_loaded
            logger.success(f"Загружено {len(proxies_loaded)} прокси в кэш")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки прокси в кэш: {e}")
    
    def _create_default_account_data(self) -> Dict:
        return {
            "email": "",
            "login": "",
            "password": "",
            "proxy": {},
            "authorized": False,
            "last_activity": "",
            "created_at": "",
            "stats": {
                "successful_logins": 0,
                "failed_logins": 0,
                "total_sessions": 0
            },
            "voice_config": get_random_voice_config()
        }
    
    def load_db(self) -> Dict:
        logger.info(f"Загрузка базы данных из {self.db_file}")
        
        try:
            with self.lock:
                if os.path.exists(self.db_file):
                    backup_file = f"{self.db_file}.backup"
                    try:
                        import shutil
                        shutil.copy2(self.db_file, backup_file)
                    except Exception:
                        pass
                    
                    with open(self.db_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        
                        if not content:
                            logger.warning("Файл базы данных пуст, создаем новую")
                            return {}
                        
                        try:
                            data = json.loads(content)
                            if not isinstance(data, dict):
                                logger.error("Некорректный формат базы данных, создаем новую")
                                return {}
                            
                            logger.success(f"Загружено {len(data)} записей из базы данных")
                            return data
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Ошибка парсинга JSON: {e}")
                            
                            if os.path.exists(backup_file):
                                try:
                                    with open(backup_file, "r", encoding="utf-8") as backup_f:
                                        backup_data = json.load(backup_f)
                                    logger.warning("Восстановлена резервная копия базы данных")
                                    return backup_data
                                except Exception:
                                    pass
                            
                            logger.error("Не удалось восстановить базу данных, создаем новую")
                            return {}
                else:
                    logger.info("База данных не найдена, будет создана новая")
                    return {}
                    
        except Exception as e:
            logger.error(f"Критическая ошибка загрузки базы данных: {e}")
            return {}
    
    def save_db(self):
        try:
            with self.lock:
                logger.info(f"Начинаем сохранение базы данных с {len(self.data)} записями")
                
                temp_file = f"{self.db_file}.tmp"
                
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
                
                try:
                    with open(temp_file, "r", encoding="utf-8") as f:
                        test_data = json.load(f)
                        if len(test_data) != len(self.data):
                            raise ValueError(f"Размер данных не совпадает: {len(test_data)} != {len(self.data)}")
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка валидации временного файла: {e}")
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    return False
                
                if os.path.exists(self.db_file):
                    backup_file = f"{self.db_file}.old"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(self.db_file, backup_file)
                    logger.info(f"Создан бэкап: {backup_file}")
                
                os.rename(temp_file, self.db_file)
                
                backup_file = f"{self.db_file}.old"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                
                file_size = os.path.getsize(self.db_file)
                logger.success(f"База данных сохранена: {len(self.data)} записей, размер файла: {file_size} байт")
                
                return True
                
        except Exception as e:
            logger.error(f"Ошибка сохранения базы данных: {e}")
            
            temp_file = f"{self.db_file}.tmp"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            return False
    
    def distribute_proxies_evenly(self, emails: List[str], proxies: List[Dict]) -> Dict[str, Dict]:
        if not proxies:
            return {email: {} for email in emails}
        
        if len(proxies) < len(emails):
            logger.error(f"Недостаточно прокси! Прокси: {len(proxies)}, Аккаунтов: {len(emails)}")
            logger.error(f"Требуется минимум {len(emails)} прокси для {len(emails)} аккаунтов")
            return {email: {} for email in emails}
        
        proxy_assignments = {}
        
        for i, email in enumerate(emails):
            proxy_assignments[email] = proxies[i]
        
        return proxy_assignments
    
    def create_db(self, emails: List[str], proxies: List[Dict], force_update_proxies: bool = False):
        logger.info(f"Создание базы данных для {len(emails)} аккаунтов")
        
        if proxies:
            self.load_proxies_cache(proxies)
        
        new_accounts = 0
        updated_accounts = 0
        database_changed = False
        
        total_emails = len(emails)
        progress_step = max(1, total_emails // 20)
        
        extracted_emails = []
        for email_line in emails:
            try:
                if ":" in email_line:
                    email_full, password = email_line.rsplit(":", 1)
                    extracted_emails.append(email_full)
                else:
                    logger.warning(f"Неверный формат строки: {email_line}")
                    continue
            except Exception as e:
                logger.warning(f"Ошибка парсинга email строки {email_line}: {e}")
                continue
        
        proxy_assignments = self.distribute_proxies_evenly(extracted_emails, proxies)
        
        if not proxy_assignments or not any(proxy_assignments.values()):
            logger.error("Распределение прокси не удалось, операция прервана")
            return 0, 0
        
        from utils import config
        
        for i, email_line in enumerate(emails):
            if i % progress_step == 0 or i == total_emails - 1:
                progress = (i + 1) / total_emails * 100
                logger.info(f"Обработка аккаунтов: {i + 1}/{total_emails} ({progress:.1f}%)")
            
            try:
                if ":" in email_line:
                    email_full, password = email_line.rsplit(":", 1)
                    login = email_full.split("@")[0] if "@" in email_full else email_full
                else:
                    logger.warning(f"Неверный формат строки: {email_line}")
                    continue
            except Exception as e:
                logger.warning(f"Ошибка парсинга email строки {email_line}: {e}")
                continue
            
            if email_full not in self.data:
                proxy = proxy_assignments.get(email_full, {})
                voice_config = get_random_voice_config()
                
                account_data = {
                    "email": email_full,
                    "login": login,
                    "password": password,
                    "proxy": proxy,
                    "authorized": False,
                    "last_activity": "",
                    "created_at": datetime.now().isoformat(),
                    "stats": {
                        "successful_logins": 0,
                        "failed_logins": 0,
                        "total_sessions": 0
                    },
                    "voice_config": voice_config
                }
                
                self.data[email_full] = account_data
                new_accounts += 1
                database_changed = True
                
                if i < 5 or i % (progress_step * 4) == 0: 
                    proxy_string = proxy.get("http", "")[:40] if proxy else "нет"
                    voice_name = voice_config.get("voice_name", "Unknown")
                    logger.info(f"Создан аккаунт {i+1}/{len(emails)}: {email_full[:20]}... -> {proxy_string}... -> {voice_name}", 
                               email=email_full[:20], position=f"{i+1}/{len(emails)}")
            else:
                account_data = self.data[email_full]
                current_proxy = account_data.get("proxy", {})
                
                if proxies:
                    new_proxy = proxy_assignments.get(email_full, {})
                    if new_proxy != current_proxy:
                        account_data["proxy"] = new_proxy
                        updated_accounts += 1
                        database_changed = True
                        account_data["last_updated"] = datetime.now().isoformat()
                        
                        if i < 5 or i % (progress_step * 4) == 0:
                            old_proxy_string = current_proxy.get("http", "")[:30] if current_proxy else "нет"
                            new_proxy_string = new_proxy.get("http", "")[:40] if new_proxy else "нет"
                            logger.info(f"Прокси обновлен для аккаунта {i+1}/{len(emails)}: {old_proxy_string}... -> {new_proxy_string}...")
                
                if "voice_config" not in account_data or not account_data["voice_config"]:
                    account_data["voice_config"] = get_random_voice_config()
                    updated_accounts += 1
                    database_changed = True
        
        if database_changed:
            logger.info("Сохранение базы данных...")
            save_success = self.save_db()
            if save_success:
                logger.success(f"База данных обновлена: {new_accounts} новых, {updated_accounts} обновленных аккаунтов")
            else:
                logger.error("Ошибка сохранения базы данных")
        else:
            logger.info("База данных не изменилась - сохранение не требуется")
        
        return new_accounts, updated_accounts
    
    def get_account_data(self, email: str) -> Dict:
        if email not in self.data:
            logger.warning(f"Аккаунт {email[:20]}... не найден в базе данных")
            return self._create_default_account_data()
        
        return self.data.get(email, {})
    
    def update_account(self, email: str, updates: Dict):
        if not isinstance(updates, dict):
            logger.error(f"Некорректный тип данных для обновления: {type(updates)}")
            return
        
        try:
            if email in self.data:
                validated_updates = {}
                for key, value in updates.items():
                    if key in ["stats"] and not isinstance(value, dict):
                        logger.warning(f"Некорректный тип для {key}: {type(value)}, пропускаем")
                        continue
                    validated_updates[key] = value
                
                self.data[email].update(validated_updates)
            else:
                logger.warning(f"Аккаунт {email[:20]}... не найден, создаем новый")
                self.data[email] = self._create_default_account_data()
                self.data[email].update(updates)
                    
        except Exception as e:
            logger.error(f"Ошибка обновления аккаунта {email[:20]}...: {e}")
    
    def get_proxy(self, email: str) -> Dict:
        account_data = self.get_account_data(email)
        return account_data.get("proxy", {})
    
    def get_voice_config(self, email: str) -> Dict:
        account_data = self.get_account_data(email)
        voice_config = account_data.get("voice_config", {})
        if not voice_config:
            voice_config = get_random_voice_config()
            self.update_account(email, {"voice_config": voice_config})
        return voice_config
    
    def update_proxy(self, email: str, proxy: Dict):
        if email in self.data:
            with self.lock:
                self.data[email]["proxy"] = proxy
                logger.info(f"Прокси обновлен для {email[:20]}...")
    
    def get_random_good_proxy(self) -> Optional[Dict]:
        try:
            logger.info(f"Поиск случайного хорошего прокси...")
            
            if not self.good_proxies_cache:
                logger.warning(f"Кэш прокси пуст")
                return None
            
            proxy = random.choice(self.good_proxies_cache)
            proxy_string = proxy.get('http', '')[:30]
            logger.info(f"Выбран прокси: {proxy_string}...")
            return proxy
            
        except Exception as e:
            logger.error(f"Ошибка получения случайного хорошего прокси: {e}")
            if self.good_proxies_cache:
                return random.choice(self.good_proxies_cache)
            return None
    
    def update_stats(self, email: str, stat_type: str, increment: int = 1):
        if email in self.data:
            if "stats" not in self.data[email]:
                self.data[email]["stats"] = {
                    "successful_logins": 0,
                    "failed_logins": 0,
                    "total_sessions": 0
                }
            
            if stat_type in self.data[email]["stats"]:
                self.data[email]["stats"][stat_type] += increment
    
    def get_stats(self) -> Dict:
        total_accounts = len(self.data)
        authorized_accounts = sum(1 for acc in self.data.values() if acc.get("authorized", False))
        
        return {
            "total_accounts": total_accounts,
            "authorized_accounts": authorized_accounts,
            "unauthorized_accounts": total_accounts - authorized_accounts
        }
    
    def get_user_agent(self, email: str) -> str:
        return ""
    
    def get_browser_profile(self, email: str) -> Dict:
        return {}
    
    def get_account_os(self, email: str) -> str:
        return ""