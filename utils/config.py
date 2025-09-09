import os

PROJECT_NAME = "Poseidon AI"
VERSION = "1.0.0"

EMAIL_FILE = "mail.txt"
PROXY_FILE = "proxy.txt"
DATABASE_FILE = "database.json"
PHRASES_FILE = "phrases.txt"

BASE_URL = "https://app.psdn.ai/login"

DELAY_BETWEEN_ACCOUNTS = {"min": 1, "max": 2}
DELAY_BETWEEN_REQUESTS = {"min": 2, "max": 5}
DELAY_ON_ERROR = {"min": 5, "max": 10}

RETRIES = 3
REQUEST_TIMEOUT = 45

THREADS_COUNT = 1

SHUFFLE_EMAILS = True
USE_PROXIES = True

USE_CAMOUFOX_PROFILES = True

HEADLESS_MODE = False
HUMANIZE_BROWSER = True

SELECTOR_WAIT_TIMEOUT = 10000
SELECTOR_CHECK_INTERVAL = 100

CHECK_IP_URL = "https://httpbin.org/ip"
IP_CHECK_WAIT_TIME = 1

EMAIL_RETRY_ATTEMPTS = 10
EMAIL_CHECK_INTERVAL = 5
EMAIL_MAX_WAIT_TIME = 150

SAVE_GENERATED_AUDIO = True
SAVE_SCRIPT_TEXTS = True
AUDIO_SAVE_DIR = "generated_audio"
TEXTS_SAVE_DIR = "generated_texts"

DEBUG_FILE_SAVING = True

ELEVEN_LABS_API_KEY = ""

CAMPAIGNS_COUNT_RANGE = {"min": 3, "max": 5}
TEXTS_PER_CAMPAIGN_RANGE = {"min": 1, "max": 3}
DELAY_BETWEEN_TASKS = {"min": 5, "max": 15}
DELAY_BETWEEN_CAMPAIGNS = {"min": 10, "max": 25}

TWOCAPTCHA_API_KEY = ""

TWOCAPTCHA_CONFIG = {
    "timeout": 60,
    "polling_interval": 3,
    "max_retries": 2,
    "use_for_registration": True,
    "balance_check": True
}

TURNSTILE_CONFIG = {
    "auto_solve": True,
    "detection_timeout": 10,
    "solve_timeout": 60,
    "retry_count": 1,
    "inject_delay": 1,
    "website_key": "0x4AAAAAABz5S6oP4WR4cVij",
    "website_url": "https://app.psdn.ai/login"
}

SITE_CONFIG = {
    "base_url": "https://app.psdn.ai",
    "login_url": "https://app.psdn.ai/login",
    "registration_timeout": 300,
    "page_load_timeout": 30
}