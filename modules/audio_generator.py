import os
import time
import hashlib
import requests
import subprocess
import tempfile
from logger import get_logger
from eleven_labs_models import get_best_model_for_language
import config

logger = get_logger('AudioGenerator')

class AudioGenerator:
    
    def __init__(self, email, position, total_accounts, proxy=None, voice_config=None):
        self.email = email
        self.position = position
        self.total_accounts = total_accounts
        self.proxy = proxy
        self.voice_config = voice_config or {}

    def calculate_sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def validate_webm_format(self, data: bytes) -> bool:
        if len(data) < 4:
            return False
        webm_signatures = [
            b'\x1a\x45\xdf\xa3',
            b'\x1a\x45\xdf\xa3'
        ]
        return data[:4] in webm_signatures or b'webm' in data[:100].lower()

    def convert_mp3_to_webm(self, mp3_data: bytes) -> bytes:
        temp_mp3 = None
        temp_webm = None
        
        try:
            logger.info(f"Конвертация MP3 в WebM", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            timestamp = str(int(time.time() * 1000))
            temp_mp3 = f"temp_audio_{timestamp}_{self.position}.mp3"
            temp_webm = f"temp_audio_{timestamp}_{self.position}.webm"
            
            with open(temp_mp3, 'wb') as f:
                f.write(mp3_data)
            
            cmd = [
                'ffmpeg', 
                '-i', temp_mp3,
                '-c:a', 'libopus',
                '-b:a', '64k',
                '-ar', '48000',
                '-ac', '1',
                '-f', 'webm',
                '-y',
                temp_webm
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(temp_webm):
                with open(temp_webm, 'rb') as f:
                    webm_data = f.read()
                
                if self.validate_webm_format(webm_data):
                    logger.success(f"Конвертация успешна: {len(webm_data)} байт", 
                                  email=self.email, position=f"{self.position}/{self.total_accounts}")
                    return webm_data
                else:
                    raise Exception("Создан невалидный WebM файл")
            else:
                raise Exception(f"FFmpeg ошибка: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception("Таймаут конвертации FFmpeg")
        except Exception as e:
            logger.error(f"Ошибка конвертации: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            raise Exception(f"WebM конвертация не удалась: {e}")
        finally:
            for temp_file in [temp_mp3, temp_webm]:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass

    def generate_voice_audio_with_eleven_labs(self, text: str, language_code: str = "en") -> bytes:
        try:
            logger.info(f"Генерация через Eleven Labs ({language_code}): {text[:50]}...", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            timestamp = str(int(time.time() * 1000))
            
            voice_id = self.voice_config.get("voice_id", "JBFqnCBsd6RMkjVDRZzb")
            if not voice_id or len(voice_id) < 10:
                logger.error(f"Некорректный VOICE_ID: {voice_id}", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return b''
            
            best_model = get_best_model_for_language(language_code)
            model_id = self.voice_config.get("model_id", best_model["model_id"])
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": config.ELEVEN_LABS_API_KEY
            }
            
            voice_settings = {
                "stability": self.voice_config.get("stability", 0.6),
                "similarity_boost": self.voice_config.get("similarity_boost", 0.8)
            }
            
            if "style" in self.voice_config:
                voice_settings["style"] = self.voice_config["style"]
            if "use_speaker_boost" in self.voice_config:
                voice_settings["use_speaker_boost"] = self.voice_config["use_speaker_boost"]
            
            data = {
                "text": text,
                "model_id": model_id,
                "voice_settings": voice_settings
            }
            
            if not self.proxy:
                logger.error(f"Прокси обязательны! self.proxy = {self.proxy}", 
                            email=self.email, position=f"{self.position}/{self.total_accounts}")
                return b''
            
            logger.info(f"Используем прокси: {str(self.proxy.get('http', ''))[:40]}...", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            for attempt in range(3):
                try:
                    logger.info(f"Попытка {attempt + 1}/3 запроса к Eleven Labs", 
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    response = requests.post(
                        url, 
                        headers=headers, 
                        json=data, 
                        proxies=self.proxy, 
                        timeout=60,
                        allow_redirects=False
                    )
                    
                    logger.info(f"Статус ответа: {response.status_code}", 
                               email=self.email, position=f"{self.position}/{self.total_accounts}")
                    
                    if response.status_code == 200:
                        mp3_data = response.content
                        
                        if len(mp3_data) < 1000:
                            logger.error(f"Слишком короткое аудио: {len(mp3_data)} байт", 
                                        email=self.email, position=f"{self.position}/{self.total_accounts}")
                            return b''
                        
                        webm_data = self.convert_mp3_to_webm(mp3_data)
                        
                        self.save_audio_file(webm_data, timestamp)
                        self.save_text_file(text, timestamp, webm_data, language_code)
                        
                        logger.success(f"Аудио сгенерировано: {len(webm_data)} байт", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return webm_data
                        
                    elif response.status_code == 403:
                        response_text = response.text[:300]
                        logger.warning(f"403 ошибка, попытка {attempt + 1}: {response_text}...", 
                                      email=self.email, position=f"{self.position}/{self.total_accounts}")
                        
                        if "cloudflare" in response_text.lower() or "just a moment" in response_text.lower():
                            logger.warning(f"Cloudflare блокировка, ждем", 
                                          email=self.email, position=f"{self.position}/{self.total_accounts}")
                            if attempt < 2:
                                time.sleep(10 + attempt * 5)
                                continue
                        else:
                            logger.error(f"403 - возможно неверный VOICE_ID или нет доступа", 
                                        email=self.email, position=f"{self.position}/{self.total_accounts}")
                            return b''
                    elif response.status_code == 401:
                        logger.error(f"401 - неверный API ключ", 
                                    email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return b''
                    elif response.status_code == 422:
                        logger.error(f"422 - ошибка валидации: {response.text[:200]}", 
                                    email=self.email, position=f"{self.position}/{self.total_accounts}")
                        return b''
                    else:
                        logger.error(f"Неожиданный статус {response.status_code}: {response.text[:200]}...", 
                                    email=self.email, position=f"{self.position}/{self.total_accounts}")
                        if attempt < 2:
                            time.sleep(3)
                            continue
                        return b''
                        
                except requests.RequestException as e:
                    logger.error(f"Ошибка запроса на попытке {attempt + 1}: {e}", 
                                email=self.email, position=f"{self.position}/{self.total_accounts}")
                    if attempt < 2:
                        time.sleep(5)
                        continue
                    return b''
            
            return b''
            
        except Exception as e:
            logger.error(f"Ошибка генерации аудио через Eleven Labs: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return b''

    def generate_voice_audio(self, text: str, language_code: str = "en") -> bytes:
        return self.generate_voice_audio_with_eleven_labs(text, language_code)

    def save_audio_file(self, audio_data: bytes, timestamp: str):
        try:
            if hasattr(config, 'SAVE_GENERATED_AUDIO') and config.SAVE_GENERATED_AUDIO:
                save_dir = getattr(config, 'AUDIO_SAVE_DIR', 'generated_audio')
                os.makedirs(save_dir, exist_ok=True)
                
                safe_email = self.email.replace('@', '_at_').replace('.', '_')
                save_filename = f"{safe_email}_{timestamp}_text.webm"
                save_path = os.path.join(save_dir, save_filename)
                
                with open(save_path, 'wb') as save_file:
                    save_file.write(audio_data)
                
                logger.success(f"Аудио файл сохранен: {save_path}", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                
        except Exception as save_error:
            logger.warning(f"Ошибка сохранения аудио файла: {save_error}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")

    def save_text_file(self, text: str, timestamp: str, audio_data: bytes, language_code: str = "en"):
        try:
            if hasattr(config, 'SAVE_SCRIPT_TEXTS') and config.SAVE_SCRIPT_TEXTS:
                save_dir = getattr(config, 'TEXTS_SAVE_DIR', 'generated_texts')
                os.makedirs(save_dir, exist_ok=True)
                
                safe_email = self.email.replace('@', '_at_').replace('.', '_')
                text_filename = f"{safe_email}_{timestamp}_text.txt"
                text_path = os.path.join(save_dir, text_filename)
                
                with open(text_path, 'w', encoding='utf-8') as text_file:
                    text_file.write(f"Email: {self.email}\n")
                    text_file.write(f"Timestamp: {timestamp}\n")
                    text_file.write(f"Language: {language_code}\n")
                    text_file.write(f"Text: {text}\n")
                    text_file.write(f"SHA256: {self.calculate_sha256(audio_data)}\n")
                    text_file.write(f"Voice ID: {self.voice_config.get('voice_id', 'N/A')}\n")
                    text_file.write(f"Model ID: {self.voice_config.get('model_id', 'N/A')}\n")
                    text_file.write(f"Stability: {self.voice_config.get('stability', 'N/A')}\n")
                    text_file.write(f"Similarity Boost: {self.voice_config.get('similarity_boost', 'N/A')}\n")
                
                logger.success(f"Текст скрипта сохранен: {text_path}", 
                              email=self.email, position=f"{self.position}/{self.total_accounts}")
                
        except Exception as save_error:
            logger.warning(f"Ошибка сохранения текста: {save_error}", 
                          email=self.email, position=f"{self.position}/{self.total_accounts}")