import logging
from colorama import init, Fore, Style
from datetime import datetime

init()

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

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = CustomFormatter()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger

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


