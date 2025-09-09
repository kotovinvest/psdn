import random
from typing import Dict, List

VOICE_MODELS = [
    {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "name": "Rachel",
        "gender": "female",
        "accent": "american",
        "age": "young",
        "description": "A young American female voice"
    },
    {
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "name": "Domi",
        "gender": "female", 
        "accent": "american",
        "age": "young",
        "description": "A young American female voice"
    },
    {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "name": "Bella",
        "gender": "female",
        "accent": "american", 
        "age": "young",
        "description": "A young American female voice"
    },
    {
        "voice_id": "ErXwobaYiN019PkySvjV",
        "name": "Antoni",
        "gender": "male",
        "accent": "american",
        "age": "young", 
        "description": "A young American male voice"
    },
    {
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "name": "Arnold",
        "gender": "male",
        "accent": "american",
        "age": "middle_aged",
        "description": "A middle-aged American male voice"
    },
    {
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "name": "Adam",
        "gender": "male",
        "accent": "american",
        "age": "middle_aged",
        "description": "A middle-aged American male voice"
    },
    {
        "voice_id": "yoZ06aMxZJJ28mfd3POQ",
        "name": "Sam",
        "gender": "male",
        "accent": "american", 
        "age": "young",
        "description": "A young American male voice"
    },
    {
        "voice_id": "CYw3kZ02Hs0563khs1Fj",
        "name": "Dave",
        "gender": "male",
        "accent": "british-essex",
        "age": "young",
        "description": "A young British male voice"
    },
    {
        "voice_id": "JBFqnCBsd6RMkjVDRZzb",
        "name": "George",
        "gender": "male",
        "accent": "british",
        "age": "middle_aged",
        "description": "A middle-aged British male voice"
    },
    {
        "voice_id": "N2lVS1w4EtoT3dr4eOWO",
        "name": "Callum",
        "gender": "male",
        "accent": "american",
        "age": "middle_aged", 
        "description": "A middle-aged American male voice"
    },
    {
        "voice_id": "XB0fDUnXU5powFXDhCwa",
        "name": "Charlotte",
        "gender": "female",
        "accent": "english-swedish",
        "age": "middle_aged",
        "description": "A middle-aged Swedish-English female voice"
    },
    {
        "voice_id": "IKne3meq5aSn9XLyUdCD",
        "name": "Charlie",
        "gender": "male",
        "accent": "australian",
        "age": "middle_aged",
        "description": "A middle-aged Australian male voice"
    },
    {
        "voice_id": "onwK4e9ZLuTAKqWW03F9",
        "name": "Daniel",
        "gender": "male",
        "accent": "british",
        "age": "middle_aged",
        "description": "A middle-aged British male voice"
    },
    {
        "voice_id": "cjVigY5qzO86Huf0OWal",
        "name": "Eric",
        "gender": "male",
        "accent": "american",
        "age": "middle_aged",
        "description": "A middle-aged American male voice"
    },
    {
        "voice_id": "g5CIjZEefAph4nQFvHAz",
        "name": "Freya",
        "gender": "female",
        "accent": "american",
        "age": "young",
        "description": "A young American female voice"
    }
]

ELEVEN_LABS_MODELS = [
    {
        "model_id": "eleven_multilingual_v2",
        "name": "Multilingual V2",
        "description": "Cutting edge turbo model - lowest latency",
        "languages": ["en", "ja", "zh", "de", "hi", "fr", "ko", "pt", "it", "es", "id", "nl", "tr", "pl", "sv", "bg", "ro", "ar", "cs", "el", "fi", "hr", "ms", "sk", "da", "ta", "uk"],
        "max_characters": 2500
    },
    {
        "model_id": "eleven_turbo_v2_5", 
        "name": "Turbo V2.5",
        "description": "Fast and reliable model",
        "languages": ["en", "ja", "zh", "de", "hi", "fr", "ko", "pt", "it", "es", "id", "nl", "tr", "pl", "sv", "bg", "ro", "ar", "cs", "el", "fi", "hr", "ms", "sk", "da", "ta", "uk"],
        "max_characters": 2500
    },
    {
        "model_id": "eleven_turbo_v2",
        "name": "Turbo V2", 
        "description": "Fast and reliable model",
        "languages": ["en", "ja", "zh", "de", "hi", "fr", "ko", "pt", "it", "es", "id", "nl", "tr", "pl", "sv", "bg", "ro", "ar", "cs", "el", "fi", "hr", "ms", "sk", "da", "ta", "uk"],
        "max_characters": 2500
    },
    {
        "model_id": "eleven_multilingual_v1",
        "name": "Multilingual V1",
        "description": "Use this model for the best quality",
        "languages": ["en", "de", "pl", "es", "it", "fr", "pt", "hi"],
        "max_characters": 2500
    },
    {
        "model_id": "eleven_english_v1",
        "name": "English V1",
        "description": "Use this model for the best quality - English only",
        "languages": ["en"],
        "max_characters": 2500
    }
]

VOICE_SETTINGS_RANGES = {
    "stability": {"min": 0.2, "max": 0.8},
    "similarity_boost": {"min": 0.3, "max": 0.9},
    "style": {"min": 0.0, "max": 0.3},
    "use_speaker_boost": [True, False]
}

def get_random_voice_config() -> Dict:
    voice = random.choice(VOICE_MODELS)
    model = random.choice(ELEVEN_LABS_MODELS)
    
    stability = round(random.uniform(VOICE_SETTINGS_RANGES["stability"]["min"], 
                                   VOICE_SETTINGS_RANGES["stability"]["max"]), 2)
    similarity_boost = round(random.uniform(VOICE_SETTINGS_RANGES["similarity_boost"]["min"], 
                                          VOICE_SETTINGS_RANGES["similarity_boost"]["max"]), 2)
    style = round(random.uniform(VOICE_SETTINGS_RANGES["style"]["min"], 
                                VOICE_SETTINGS_RANGES["style"]["max"]), 2)
    use_speaker_boost = random.choice(VOICE_SETTINGS_RANGES["use_speaker_boost"])
    
    return {
        "voice_id": voice["voice_id"],
        "voice_name": voice["name"],
        "voice_gender": voice["gender"],
        "voice_accent": voice["accent"],
        "voice_age": voice["age"],
        "model_id": model["model_id"],
        "model_name": model["name"],
        "stability": stability,
        "similarity_boost": similarity_boost,
        "style": style,
        "use_speaker_boost": use_speaker_boost
    }

def get_model_for_language(language_code: str) -> Dict:
    for model in ELEVEN_LABS_MODELS:
        if language_code in model["languages"]:
            return model
    return ELEVEN_LABS_MODELS[0]

def get_voice_by_id(voice_id: str) -> Dict:
    for voice in VOICE_MODELS:
        if voice["voice_id"] == voice_id:
            return voice
    return None

def get_model_by_id(model_id: str) -> Dict:
    for model in ELEVEN_LABS_MODELS:
        if model["model_id"] == model_id:
            return model
    return None

def get_voices_by_gender(gender: str) -> List[Dict]:
    return [voice for voice in VOICE_MODELS if voice["gender"] == gender]

def get_voices_by_accent(accent: str) -> List[Dict]:
    return [voice for voice in VOICE_MODELS if voice["accent"] == accent]