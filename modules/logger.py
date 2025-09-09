import logging
from colorama import init, Fore, Style
from datetime import datetime
import os
import threading

init(autoreset=True)

class CustomFormatter(logging.Formatter):
    
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def format(self, record):
        timestamp = self.formatTime(record)
        level = record.levelname
        module = getattr(record, 'module_name', 'Unknown')
        email = getattr(record, 'email', 'NoEmail')
        position = getattr(record, 'position', '')
        message = record.getMessage()
        
        if len(email) > 30:
            email = email[:27] + "..."
        
        log_format = f"{timestamp} | {level:<7} | {module:<20} | {position:<8} | {email:<30} | {message}"
        
        if record.levelno == logging.ERROR:
            return f"{Fore.RED}{log_format}{Style.RESET_ALL}"
        elif record.levelno == logging.WARNING:
            return f"{Fore.YELLOW}{log_format}{Style.RESET_ALL}"
        elif record.levelno == logging.INFO and hasattr(record, 'highlight') and record.highlight:
            return f"{Fore.GREEN}{log_format}{Style.RESET_ALL}"
        elif record.levelno == logging.DEBUG:
            return f"{Fore.BLUE}{log_format}{Style.RESET_ALL}"
        else:
            return log_format

class FileFormatter(logging.Formatter):
    
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def format(self, record):
        timestamp = self.formatTime(record)
        level = record.levelname
        module = getattr(record, 'module_name', 'Unknown')
        email = getattr(record, 'email', 'NoEmail')
        position = getattr(record, 'position', '')
        message = record.getMessage()
        
        if len(email) > 30:
            email = email[:27] + "..."
        
        return f"{timestamp} | {level:<7} | {module:<20} | {position:<8} | {email:<30} | {message}"

_logger = None
_logger_lock = threading.Lock()

def setup_logger(log_to_file: bool = False, log_level: int = logging.INFO):
    global _logger
    
    with _logger_lock:
        if _logger is not None:
            return _logger
        
        _logger = logging.getLogger('JuneBot')
        _logger.setLevel(log_level)
        
        if _logger.handlers:
            _logger.handlers.clear()
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(CustomFormatter())
        console_handler.setLevel(log_level)
        _logger.addHandler(console_handler)
        
        if log_to_file:
            try:
                logs_dir = "logs"
                if not os.path.exists(logs_dir):
                    os.makedirs(logs_dir)
                
                log_filename = f"logs/june_bot_{datetime.now().strftime('%Y%m%d')}.log"
                file_handler = logging.FileHandler(log_filename, encoding='utf-8')
                file_handler.setFormatter(FileFormatter())
                file_handler.setLevel(log_level)
                _logger.addHandler(file_handler)
                
            except Exception as e:
                print(f"Ошибка создания файлового логгера: {e}")
        
        def success(self, msg, *args, module_name='Unknown', email='NoEmail', position='', highlight=True, **kwargs):
            if self.isEnabledFor(logging.INFO):
                extra = {'module_name': module_name, 'email': email, 'position': position, 'highlight': highlight}
                self._log(logging.INFO, msg, args, extra=extra, **kwargs)
        
        logging.Logger.success = success
        
        return _logger

def get_logger(module_name: str):
    global_logger = setup_logger()
    
    class ModuleLogger:
        
        def __init__(self, module_name: str):
            self.module_name = module_name
            self.logger = global_logger
        
        def _log(self, level, msg, email='NoEmail', position='', highlight=False):
            extra = {
                'module_name': self.module_name, 
                'email': email, 
                'position': position, 
                'highlight': highlight
            }
            self.logger._log(level, msg, (), extra=extra)
        
        def debug(self, msg, email='NoEmail', position=''):
            self._log(logging.DEBUG, msg, email, position)
        
        def info(self, msg, email='NoEmail', position='', highlight=False):
            self._log(logging.INFO, msg, email, position, highlight)
        
        def success(self, msg, email='NoEmail', position=''):
            self._log(logging.INFO, msg, email, position, highlight=True)
        
        def warning(self, msg, email='NoEmail', position=''):
            self._log(logging.WARNING, msg, email, position)
        
        def error(self, msg, email='NoEmail', position=''):
            self._log(logging.ERROR, msg, email, position)
        
        def critical(self, msg, email='NoEmail', position=''):
            self._log(logging.CRITICAL, msg, email, position)
    
    return ModuleLogger(module_name)

logger = setup_logger()

def log_info(msg, module_name='Main', email='NoEmail', position='', highlight=False):
    extra = {'module_name': module_name, 'email': email, 'position': position, 'highlight': highlight}
    logger.info(msg, extra=extra)

def log_success(msg, module_name='Main', email='NoEmail', position=''):
    logger.success(msg, module_name=module_name, email=email, position=position)

def log_warning(msg, module_name='Main', email='NoEmail', position=''):
    extra = {'module_name': module_name, 'email': email, 'position': position}
    logger.warning(msg, extra=extra)

def log_error(msg, module_name='Main', email='NoEmail', position=''):
    extra = {'module_name': module_name, 'email': email, 'position': position}
    logger.error(msg, extra=extra)

def set_log_level(level):
    global _logger
    if _logger:
        _logger.setLevel(level)
        for handler in _logger.handlers:
            handler.setLevel(level)

def enable_file_logging():
    global _logger
    if _logger:
        try:
            file_handler_exists = any(isinstance(h, logging.FileHandler) for h in _logger.handlers)
            
            if not file_handler_exists:
                logs_dir = "logs"
                if not os.path.exists(logs_dir):
                    os.makedirs(logs_dir)
                
                log_filename = f"logs/june_bot_{datetime.now().strftime('%Y%m%d')}.log"
                file_handler = logging.FileHandler(log_filename, encoding='utf-8')
                file_handler.setFormatter(FileFormatter())
                _logger.addHandler(file_handler)
                
                log_info("Логирование в файл включено", "Logger")
        except Exception as e:
            log_error(f"Ошибка включения файлового логирования: {e}", "Logger")

if __name__ != "__main__":
    setup_logger()