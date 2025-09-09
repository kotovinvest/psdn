import os
import sys
import random
import time
import threading
import warnings

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from datetime import datetime


warnings.filterwarnings("ignore", category=UserWarning, module="camoufox")



from data.database import Database
from clients.poseidon_client import PoseidonClient
from utils.proxy_manager import ProxyManager
from utils import config
from utils.logger import get_logger, print_banner, print_menu

logger = get_logger(\'Main\')

def load_file_lines(file_path: str, description: str) -> List[str]:
    logger.info(f"Загрузка {description} из {file_path}")
    
    try:
        if not os.path.exists(file_path):
            logger.error(f"Файл {file_path} не найден")
            return []
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if not lines:
            logger.warning(f"Файл {file_path} пуст")
            return []
        
        logger.info(f"Загружено {len(lines)} {description}")
        return lines
        
    except Exception as e:
        logger.error(f"Ошибка загрузки {file_path}: {e}")
        return []

def load_emails() -> List[str]:
    emails = load_file_lines(config.EMAIL_FILE, "email аккаунтов")
    
    if emails and config.SHUFFLE_EMAILS:
        random.shuffle(emails)
        logger.info("Email аккаунты перемешаны")
    
    return emails

def load_proxies() -> List[dict]:
    if not config.USE_PROXIES:
        logger.info("Прокси отключены в настройках")
        return []
    
    proxy_lines = load_file_lines(config.PROXY_FILE, "прокси")
    if not proxy_lines:
        logger.warning("Файл прокси пуст или не найден")
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
                        logger.warning(f"Пропущен плохой прокси: {proxy_string[:30]}...")
                    elif bad_proxies_count == 6:
                        logger.warning("... (остальные плохие прокси пропущены без вывода)")
                    continue
                
                proxies.append(proxy_dict)
            else:
                logger.warning(f"Неверный формат прокси: {line}")
        except Exception as e:
          logger.error(f"Ошибка парсинга прокси \'{line}\': {e}")
    
    if bad_proxies_count > 0:
        logger.info(f"Пропущено {bad_proxies_count} плохих прокси")
    
    logger.info(f"Загружено {len(proxies)} валидных прокси")
    return proxies

def process_account(email_line: str, db: Database, position: int, total_accounts: int) -> tuple:
    try:
        logger.info(f"Обработка аккаунта {position}/{total_accounts}")
        client = PoseidonClient(email_line, db, position, total_accounts)
        success = client.process_account()
        
        summary = client.get_account_summary()
        
        logger.info(f"Аккаунт {position}/{total_accounts} обработан успешно" if success else f"Аккаунт {position}/{total_accounts} обработан с ошибкой")
        
        if position < total_accounts:
            delay = random.uniform(config.DELAY_BETWEEN_ACCOUNTS["min"], config.DELAY_BETWEEN_ACCOUNTS["max"])
            logger.info(f"Задержка {delay:.1f}s перед следующим аккаунтом")
            time.sleep(delay)
        
        return success, summary
        
    except Exception as e:
        logger.error(f"Ошибка обработки аккаунта {position}: {e}")
        
        
        
        error_summary = {
            "email": "неизвестен",
            "status": "ошибка"
        }
        
        return False, error_summary

def execute_action(action_type: str, emails: List[str], db: Database):
    if action_type == "generate":
        logger.info("=== СОЗДАНИЕ БАЗЫ ДАННЫХ ===")
        
        proxies = load_proxies()
        
        try:
            logger.info("Начинаем создание базы данных...")
            new_accounts, updated_accounts = db.create_db(emails, proxies)
            logger.success(f"База данных создана успешно! Новых: {new_accounts}, Обновленных: {updated_accounts}")
            
            if os.path.exists(config.DATABASE_FILE):
                file_size = os.path.getsize(config.DATABASE_FILE)
                logger.success(f"Файл базы данных создан: {config.DATABASE_FILE} ({file_size} байт)")
            else:
                logger.error(f"Файл базы данных не был создан: {config.DATABASE_FILE}")
                
        except Exception as e:
            logger.error(f"Ошибка при создании базы данных: {e}")
            
            
        
        return

    logger.info("=== ЗАПУСК ПОЛНОЙ ОБРАБОТКИ АККАУНТОВ ===")
    
    logger.info(f"Будет обработано {len(emails)} аккаунтов")
    
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
                  logger.success(f"Аккаунт {summary[\'email\'][:20]}... обработан успешно")
                else:
                    failed_accounts += 1
                   logger.error(f"Аккаунт {summary[\"email\"][:20]}... обработан с ошибкой")            except Exception as e:
                failed_accounts += 1
                logger.error(f"Критическая ошибка аккаунта {email[:20]}...: {e}")
                
                error_summary = {
                    "email": email,
                    "status": "ошибка"
                }
                account_summaries.append(error_summary)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    logger.info("=== ИТОГИ ОБРАБОТКИ ===")
    logger.info(f"Обработано за {total_time:.1f} секунд")
    logger.success(f"Успешно: {successful_accounts}")
    logger.error(f"С ошибками: {failed_accounts}")
    logger.info(f"Общий процент успеха: {(successful_accounts / len(emails) * 100):.1f}%")
    
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
                choice = input("Выберите действие (0-2): ").strip()
                
                if choice == "0":
                    logger.info("Спасибо за использование Poseidon AI Bot!")
                    break
                
                elif choice == "1":
                    emails = load_emails()
                    if not emails:
                        logger.error("Нет email аккаунтов для создания базы данных")
                        input("\nНажмите Enter для продолжения...")
                        continue
                    execute_action("generate", emails, db)
                    
                elif choice == "2":
                    emails = load_emails()
                    if not emails:
                        logger.error("Нет email аккаунтов для обработки")
                        input("\nНажмите Enter для продолжения...")
                        continue
                    
                    execute_action("full", emails, db)
                
                else:
                    logger.error("Неверный выбор! Пожалуйста, выберите число от 0 до 2.")
                    
                input("\nНажмите Enter для продолжения...")
                
            except KeyboardInterrupt:
                logger.warning("Работа прервана пользователем")
                break
            except Exception as e:
                logger.error(f"Критическая ошибка: {e}")
                
                
                input("\nНажмите Enter для продолжения...")
                
    finally:
        try:
            logger.info("Финальное сохранение базы данных завершено")
        except Exception as e:
            logger.warning(f"Ошибка финального сохранения: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Работа прервана пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        