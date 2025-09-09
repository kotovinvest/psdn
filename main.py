import os
import sys
import random
import time
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from datetime import datetime
import logging
from colorama import init, Fore, Style

warnings.filterwarnings("ignore", category=UserWarning, module="camoufox")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from database import Database
from poseidon_client import PoseidonClient
from proxy_manager import ProxyManager
import config

init()

logger = logging.getLogger('Main')
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def format(self, record):
        timestamp = self.formatTime(record)
        level = record.levelname
        module = record.module_name if hasattr(record, 'module_name') else 'Unknown'
        email_addr = record.email if hasattr(record, 'email') else 'NoEmail'
        position = record.position if hasattr(record, 'position') else ''
        message = record.getMessage()
        log_format = f"{timestamp} | {level:<7} | {module:<20} | {position:<8} | {email_addr:<30} | {message}"
        
        if record.levelno == logging.ERROR:
            return f"{Fore.RED}{log_format}{Style.RESET_ALL}"
        elif record.levelno == logging.WARNING:
            return f"{Fore.YELLOW}{log_format}{Style.RESET_ALL}"
        elif record.levelno == logging.INFO and hasattr(record, 'highlight') and record.highlight:
            return f"{Fore.GREEN}{log_format}{Style.RESET_ALL}"
        return log_format

formatter = CustomFormatter()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def log_info(msg, module_name='Main', email='NoEmail', position='', highlight=False):
    extra = {'module_name': module_name, 'email': email, 'position': position, 'highlight': highlight}
    logger.info(msg, extra=extra)

def log_success(msg, module_name='Main', email='NoEmail', position=''):
    extra = {'module_name': module_name, 'email': email, 'position': position, 'highlight': True}
    logger.info(msg, extra=extra)

def log_warning(msg, module_name='Main', email='NoEmail', position=''):
    extra = {'module_name': module_name, 'email': email, 'position': position}
    logger.warning(msg, extra=extra)

def log_error(msg, module_name='Main', email='NoEmail', position=''):
    extra = {'module_name': module_name, 'email': email, 'position': position}
    logger.error(msg, extra=extra)

def print_banner():
    banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗
║                           {Fore.YELLOW}Poseidon AI {Fore.CYAN}                        ║
║                         {Fore.GREEN}by KOTOV INVEST{Fore.CYAN}                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

def print_menu():
    menu = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗
║                        {Fore.YELLOW}ГЛАВНОЕ МЕНЮ{Fore.CYAN}                         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  {Fore.GREEN}1.{Fore.WHITE} Создать базу данных                                       {Fore.CYAN}║
║  {Fore.GREEN}2.{Fore.WHITE} Полная обработка аккаунтов                                {Fore.CYAN}║
║  {Fore.RED}0.{Fore.WHITE} Выход                                                     {Fore.CYAN}║
╚═══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(menu)

def load_file_lines(file_path: str, description: str) -> List[str]:
    log_info(f"Загрузка {description} из {file_path}")
    
    try:
        if not os.path.exists(file_path):
            log_error(f"Файл {file_path} не найден")
            return []
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if not lines:
            log_warning(f"Файл {file_path} пуст")
            return []
        
        log_info(f"Загружено {len(lines)} {description}")
        return lines
        
    except Exception as e:
        log_error(f"Ошибка загрузки {file_path}: {e}")
        return []

def load_emails() -> List[str]:
    emails = load_file_lines(config.EMAIL_FILE, "email аккаунтов")
    
    if emails and config.SHUFFLE_EMAILS:
        random.shuffle(emails)
        log_info("Email аккаунты перемешаны")
    
    return emails

def load_proxies() -> List[dict]:
    if not config.USE_PROXIES:
        log_info("Прокси отключены в настройках")
        return []
    
    proxy_lines = load_file_lines(config.PROXY_FILE, "прокси")
    if not proxy_lines:
        log_warning("Файл прокси пуст или не найден")
        return []
    
    proxies = []
    bad_proxies_count = 0
    
    proxy_manager = ProxyManager()
    
    for line in proxy_lines:
        try:
            if "@" in line and ":" in line:
                auth_part, server_part = line.split("@")
                username, password = auth_part.split(":")
                ip, port = server_part.split(":")
                
                proxy_dict = {
                    "http": f"http://{username}:{password}@{ip}:{port}",
                    "https": f"http://{username}:{password}@{ip}:{port}"
                }
                
                proxy_string = proxy_dict["http"]
                
                if proxy_manager.is_proxy_bad(proxy_string):
                    bad_proxies_count += 1
                    if bad_proxies_count <= 5:  
                        log_warning(f"Пропущен плохой прокси: {proxy_string[:30]}...")
                    elif bad_proxies_count == 6:
                        log_warning("... (остальные плохие прокси пропущены без вывода)")
                    continue
                
                proxies.append(proxy_dict)
            else:
                log_warning(f"Неверный формат прокси: {line}")
        except Exception as e:
            log_error(f"Ошибка парсинга прокси '{line}': {e}")
    
    if bad_proxies_count > 0:
        log_info(f"Пропущено {bad_proxies_count} плохих прокси")
    
    log_info(f"Загружено {len(proxies)} валидных прокси")
    return proxies

def process_account(email_line: str, db: Database, position: int, total_accounts: int) -> tuple:
    try:
        log_info(f"Обработка аккаунта {position}/{total_accounts}")
        client = PoseidonClient(email_line, db, position, total_accounts)
        success = client.process_account()
        
        summary = client.get_account_summary()
        
        log_info(f"Аккаунт {position}/{total_accounts} обработан успешно" if success else f"Аккаунт {position}/{total_accounts} обработан с ошибкой")
        
        if position < total_accounts:
            delay = random.uniform(config.DELAY_BETWEEN_ACCOUNTS["min"], config.DELAY_BETWEEN_ACCOUNTS["max"])
            log_info(f"Задержка {delay:.1f}s перед следующим аккаунтом")
            time.sleep(delay)
        
        return success, summary
        
    except Exception as e:
        log_error(f"Ошибка обработки аккаунта {position}: {e}")
        import traceback
        log_error(f"Трейсбек: {traceback.format_exc()}")
        
        error_summary = {
            "email": "неизвестен",
            "status": "ошибка"
        }
        
        return False, error_summary

def execute_action(action_type: str, emails: List[str], db: Database):
    if action_type == "generate":
        log_info("=== СОЗДАНИЕ БАЗЫ ДАННЫХ ===")
        
        proxies = load_proxies()
        
        try:
            log_info("Начинаем создание базы данных...")
            new_accounts, updated_accounts = db.create_db(emails, proxies)
            log_success(f"База данных создана успешно! Новых: {new_accounts}, Обновленных: {updated_accounts}")
            
            if os.path.exists(config.DATABASE_FILE):
                file_size = os.path.getsize(config.DATABASE_FILE)
                log_success(f"Файл базы данных создан: {config.DATABASE_FILE} ({file_size} байт)")
            else:
                log_error(f"Файл базы данных не был создан: {config.DATABASE_FILE}")
                
        except Exception as e:
            log_error(f"Ошибка при создании базы данных: {e}")
            import traceback
            log_error(f"Трейсбек: {traceback.format_exc()}")
        
        return

    log_info("=== ЗАПУСК ПОЛНОЙ ОБРАБОТКИ АККАУНТОВ ===")
    
    log_info(f"Будет обработано {len(emails)} аккаунтов")
    
    start_time = time.time()
    successful_accounts = 0
    failed_accounts = 0
    account_summaries = []
    
    with ThreadPoolExecutor(max_workers=config.THREADS_COUNT) as executor:
        future_to_email = {
            executor.submit(process_account, email, db, i + 1, len(emails)): email 
            for i, email in enumerate(emails)
        }
        
        for future in as_completed(future_to_email):
            email = future_to_email[future]
            try:
                success, summary = future.result()
                account_summaries.append(summary)
                
                if success:
                    successful_accounts += 1
                    log_success(f"Аккаунт {summary['email'][:20]}... обработан успешно")
                else:
                    failed_accounts += 1
                    log_error(f"Аккаунт {summary['email'][:20]}... обработан с ошибкой")
            except Exception as e:
                failed_accounts += 1
                log_error(f"Критическая ошибка аккаунта {email[:20]}...: {e}")
                
                error_summary = {
                    "email": email,
                    "status": "ошибка"
                }
                account_summaries.append(error_summary)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    log_info("=== ИТОГИ ОБРАБОТКИ ===")
    log_info(f"Обработано за {total_time:.1f} секунд")
    log_success(f"Успешно: {successful_accounts}")
    log_error(f"С ошибками: {failed_accounts}")
    log_info(f"Общий процент успеха: {(successful_accounts / len(emails) * 100):.1f}%")
    
    try:
        db.save_db()
        logger.info("База данных сохранена")
    except Exception as e:
        logger.warning(f"Ошибка сохранения: {e}")

def main():
    print_banner()
    
    db = Database(config.DATABASE_FILE)
    
    try:
        while True:
            try:
                print_menu()
                choice = input(f"{Fore.YELLOW}Выберите действие (0-2): {Style.RESET_ALL}").strip()
                
                if choice == "0":
                    print(f"\n{Fore.GREEN}Спасибо за использование Poseidon AI Bot!{Style.RESET_ALL}")
                    break
                
                elif choice == "1":
                    emails = load_emails()
                    if not emails:
                        log_error("Нет email аккаунтов для создания базы данных")
                        input(f"\n{Fore.YELLOW}Нажмите Enter для продолжения...{Style.RESET_ALL}")
                        continue
                    execute_action("generate", emails, db)
                    
                elif choice == "2":
                    emails = load_emails()
                    if not emails:
                        log_error("Нет email аккаунтов для обработки")
                        input(f"\n{Fore.YELLOW}Нажмите Enter для продолжения...{Style.RESET_ALL}")
                        continue
                    
                    execute_action("full", emails, db)
                
                else:
                    print(f"{Fore.RED}Неверный выбор! Пожалуйста, выберите число от 0 до 2.{Style.RESET_ALL}")
                    
                input(f"\n{Fore.YELLOW}Нажмите Enter для продолжения...{Style.RESET_ALL}")
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Работа прервана пользователем{Style.RESET_ALL}")
                break
            except Exception as e:
                log_error(f"Критическая ошибка: {e}")
                import traceback
                log_error(f"Трейсбек: {traceback.format_exc()}")
                input(f"\n{Fore.YELLOW}Нажмите Enter для продолжения...{Style.RESET_ALL}")
                
    finally:
        try:
            logger.info("Финальное сохранение базы данных завершено")
        except Exception as e:
            logger.warning(f"Ошибка финального сохранения: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_warning("Работа прервана пользователем")
    except Exception as e:
        log_error(f"Критическая ошибка: {e}")
        import traceback
        log_error(f"Трейсбек: {traceback.format_exc()}")