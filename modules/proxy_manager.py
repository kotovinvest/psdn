import json
import os
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from logger import get_logger

logger = get_logger('ProxyManager')

class ProxyManager:
    
    def __init__(self, bad_proxies_file: str = "bad_proxies.json"):
        self.bad_proxies_file = bad_proxies_file
        self.lock = threading.Lock()
        self.bad_proxies = self.load_bad_proxies()
        
        logger.info(f"Менеджер прокси инициализирован, плохих прокси: {len(self.bad_proxies)}")
    
    def load_bad_proxies(self) -> Dict:
        try:
            if os.path.exists(self.bad_proxies_file):
                with open(self.bad_proxies_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки плохих прокси: {e}")
            return {}
    
    def save_bad_proxies(self):
        try:
            with self.lock:
                temp_file = f"{self.bad_proxies_file}.tmp"
                
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(self.bad_proxies, f, indent=2, ensure_ascii=False)
                
                if os.path.exists(self.bad_proxies_file):
                    os.replace(temp_file, self.bad_proxies_file)
                else:
                    os.rename(temp_file, self.bad_proxies_file)
                
                logger.info(f"Сохранено {len(self.bad_proxies)} плохих прокси")
        except Exception as e:
            logger.error(f"Ошибка сохранения плохих прокси: {e}")
            temp_file = f"{self.bad_proxies_file}.tmp"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def is_proxy_bad(self, proxy_string: str) -> bool:
        with self.lock:
            return proxy_string in self.bad_proxies
    
    def mark_proxy_bad(self, proxy_string: str, reason: str = "", email: str = ""):
        try:
            if not proxy_string or len(proxy_string) < 10:
                return
                
            with self.lock:
                if proxy_string not in self.bad_proxies:
                    self.bad_proxies[proxy_string] = {
                        "first_failed": datetime.now().isoformat(),
                        "fail_count": 1,
                        "last_reason": reason,
                        "last_email": email
                    }
                else:
                    self.bad_proxies[proxy_string]["fail_count"] += 1
                    self.bad_proxies[proxy_string]["last_failed"] = datetime.now().isoformat()
                    self.bad_proxies[proxy_string]["last_reason"] = reason
                    self.bad_proxies[proxy_string]["last_email"] = email
                
                logger.warning(f"Прокси отмечен как плохой: {proxy_string[:30]}... Причина: {reason}")
                
                import threading
                save_thread = threading.Thread(target=self.save_bad_proxies)
                save_thread.daemon = True
                save_thread.start()
                
        except Exception as e:
            logger.error(f"Ошибка отметки плохого прокси: {e}")
    
    def get_proxy_string(self, proxy_dict: Dict) -> str:
        try:
            if proxy_dict and "http" in proxy_dict:
                return proxy_dict["http"]
            return ""
        except Exception:
            return ""
    
    def cleanup_old_bad_proxies(self, hours_old: int = 6):
        try:
            cutoff_date = datetime.now() - timedelta(hours=hours_old)
            
            with self.lock:
                proxies_to_remove = []
                
                for proxy_string, data in self.bad_proxies.items():
                    try:
                        first_failed = data.get("first_failed", "")
                        last_failed = data.get("last_failed", "")
                        
                        dates_to_check = [d for d in [first_failed, last_failed] if d]
                        
                        if dates_to_check:
                            earliest_date = min(datetime.fromisoformat(d) for d in dates_to_check)
                            
                            if earliest_date < cutoff_date:
                                proxies_to_remove.append(proxy_string)
                        else:
                            proxies_to_remove.append(proxy_string)
                            
                    except Exception:
                        proxies_to_remove.append(proxy_string)
                
                for proxy_string in proxies_to_remove:
                    del self.bad_proxies[proxy_string]
                
                if proxies_to_remove:
                    logger.info(f"Удалено {len(proxies_to_remove)} старых плохих прокси (старше {hours_old}ч)")
                    self.save_bad_proxies()
                    
        except Exception as e:
            logger.error(f"Ошибка расширенной очистки старых плохих прокси: {e}")

proxy_manager = ProxyManager()