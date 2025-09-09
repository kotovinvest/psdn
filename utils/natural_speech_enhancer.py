import random
import re
from typing import Dict, List
from logger import get_logger
from utils import config

logger = get_logger('NaturalSpeechEnhancer')

class NaturalSpeechEnhancer:
    
    def __init__(self):
        self.settings = {
            'add_pauses': True,
            'add_breathing': True,
            'pause_probability': 0.3,
            'breathing_probability': 0.1,
            'remove_question_marks': True
        }
        
        self.eleven_labs_pauses = [
            '<break time="0.3s"/>',
            '<break time="0.5s"/>',
            '<break time="0.7s"/>',
            '<break time="1.0s"/>'
        ]
        
        self.eleven_labs_breathing_sounds = [
            '<break time="0.2s"/>',
            '<break time="0.4s"/>',
        ]
        
        self.gtts_pauses = [
            '... ',
            ', ',
            '. ',
        ]
        
        self.gtts_breathing_sounds = [
            '... ',
            ', ',
        ]

    def update_settings(self, new_settings: Dict):
        self.settings.update(new_settings)

    def get_pauses_for_engine(self) -> List[str]:
        engine = getattr(config, 'TTS_ENGINE', 'eleven_labs').lower()
        if engine == 'gtts':
            return self.gtts_pauses
        else:
            return self.eleven_labs_pauses

    def get_breathing_for_engine(self) -> List[str]:
        engine = getattr(config, 'TTS_ENGINE', 'eleven_labs').lower()
        if engine == 'gtts':
            return self.gtts_breathing_sounds
        else:
            return self.eleven_labs_breathing_sounds

    def add_natural_pauses(self, text: str) -> str:
        if not self.settings['add_pauses']:
            return text
        
        engine = getattr(config, 'TTS_ENGINE', 'eleven_labs').lower()
        pauses = self.get_pauses_for_engine()
        
        if engine == 'gtts':
            text = re.sub(r',(\s+)', lambda m: f',{random.choice(pauses)}{m.group(1)}' if random.random() < self.settings['pause_probability'] else m.group(0), text)
            text = re.sub(r'\.(\s+)', lambda m: f'.{random.choice(pauses)}{m.group(1)}' if random.random() < self.settings['pause_probability'] else m.group(0), text)
        else:
            text = re.sub(r',(\s+)', lambda m: f',{random.choice(pauses)}{m.group(1)}' if random.random() < self.settings['pause_probability'] else m.group(0), text)
            text = re.sub(r'\.(\s+)', lambda m: f'.{random.choice(pauses)}{m.group(1)}' if random.random() < self.settings['pause_probability'] else m.group(0), text)
        
        return text

    def add_breathing(self, text: str) -> str:
        if not self.settings['add_breathing']:
            return text
        
        engine = getattr(config, 'TTS_ENGINE', 'eleven_labs').lower()
        breathing_sounds = self.get_breathing_for_engine()
        
        sentences = re.split(r'([.!?])', text)
        result = []
        
        for i, sentence in enumerate(sentences):
            result.append(sentence)
            
            if (sentence.strip().endswith('.') or sentence.strip().endswith('!') or sentence.strip().endswith('?')) and \
               len(sentence.strip()) > 50 and \
               random.random() < self.settings['breathing_probability'] and \
               i < len(sentences) - 1:
                breathing = random.choice(breathing_sounds)
                result.append(breathing)
        
        return ''.join(result)

    def remove_question_marks_naturally(self, text: str) -> str:
        if not self.settings['remove_question_marks']:
            return text
        
        text = text.replace('?', '.')
        return text

    def enhance_text_naturalness(self, text: str, email: str = "", position: str = "") -> str:
        try:
            engine = getattr(config, 'TTS_ENGINE', 'eleven_labs').lower()
            logger.info(f"Добавление естественных элементов речи к тексту (движок: {engine})", 
                       email=email, position=position)
            
            original_length = len(text)
            
            enhanced_text = text
            enhanced_text = self.remove_question_marks_naturally(enhanced_text)
            
            if engine == 'gtts':
                enhanced_text = re.sub(r'\s+', ' ', enhanced_text).strip()
            else:
                enhanced_text = self.add_natural_pauses(enhanced_text)
                enhanced_text = self.add_breathing(enhanced_text)
                enhanced_text = re.sub(r'\s+', ' ', enhanced_text).strip()
            
            final_length = len(enhanced_text)
            
            logger.info(f"Естественные элементы добавлены. Было: {original_length} символов, стало: {final_length}", 
                       email=email, position=position)
            
            logger.info(f"Модифицированный текст: {enhanced_text}", 
                       email=email, position=position)
            
            return enhanced_text
            
        except Exception as e:
            logger.error(f"Ошибка улучшения естественности текста: {e}", 
                        email=email, position=position)
            return text