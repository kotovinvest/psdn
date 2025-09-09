CAMPAIGNS = [
    {
        "virtual_id": "d45dc5b0-cc5d-4daa-a7a2-2866f5ba51f8",
        "campaign_name": "English Voice Data Campaign",
        "language_code": "en",
        "description": "Help democratize AI technology by sharing your English voice.",
        "is_featured": True,
        "participant_count": 34770
    },
    {
        "virtual_id": "85fa33ca-02a6-4ee3-8a27-4b5ff8793a4e",
        "campaign_name": "Marathi Voice Data Campaign",
        "language_code": "mr",
        "description": "Help democratize AI technology by sharing your Marathi voice.",
        "is_featured": False,
        "participant_count": 3442
    },
    {
        "virtual_id": "c7e38d54-7b69-4e16-9719-147c56ab9a2a",
        "campaign_name": "Urdu Voice Data Campaign",
        "language_code": "ur",
        "description": "Shape tomorrow's AI today! Record simple phrases in Urdu.",
        "is_featured": False,
        "participant_count": 5055
    },
    {
        "virtual_id": "c295d0be-4e4b-4cb2-843d-060651810a7b",
        "campaign_name": "Arabic Voice Data Campaign",
        "language_code": "ar",
        "description": "Shape tomorrow's AI today! Record simple phrases in Arabic.",
        "is_featured": False,
        "participant_count": 3500
    },
    {
        "virtual_id": "23995d6e-4de3-40d5-92a5-47808be58e7d",
        "campaign_name": "Mandarin Chinese Voice Data Campaign",
        "language_code": "zh",
        "description": "Help democratize AI technology by sharing your Mandarin Chinese voice.",
        "is_featured": False,
        "participant_count": 2489
    },
    {
        "virtual_id": "6cadbdf5-b7fc-49bc-896d-f5807e52cb23",
        "campaign_name": "Indonesian Voice Data Campaign",
        "language_code": "id",
        "description": "Your voice matters! Contribute to our Indonesian voice dataset.",
        "is_featured": False,
        "participant_count": 8616
    },
    {
        "virtual_id": "6fd9c4a5-62f7-4ea6-944a-00127744be06",
        "campaign_name": "Vietnamese Voice Data Campaign",
        "language_code": "vi",
        "description": "Your voice matters! Contribute to our Vietnamese voice dataset.",
        "is_featured": False,
        "participant_count": 5167
    },
    {
        "virtual_id": "bd8bba61-9656-4a3e-9cc3-8d003a74829a",
        "campaign_name": "Turkish Voice Data Campaign",
        "language_code": "tr",
        "description": "Shape tomorrow's AI today! Record simple phrases in Turkish.",
        "is_featured": False,
        "participant_count": 1880
    },
    {
        "virtual_id": "d76ebfe1-6667-4014-a386-1bd7273b9758",
        "campaign_name": "Russian Voice Data Campaign",
        "language_code": "ru",
        "description": "Join our mission to build inclusive AI by contributing voice samples in Russian.",
        "is_featured": False,
        "participant_count": 2230
    },
    {
        "virtual_id": "89389bd5-7c53-4ccd-8a21-44361a65d0a6",
        "campaign_name": "Portuguese Voice Data Campaign",
        "language_code": "pt",
        "description": "Help democratize AI technology by sharing your Portuguese voice.",
        "is_featured": False,
        "participant_count": 1739
    },
    {
        "virtual_id": "a523bf85-d5b6-4614-963f-0a50c398bc2d",
        "campaign_name": "German Voice Data Campaign",
        "language_code": "de",
        "description": "Join our mission to build inclusive AI by contributing voice samples in German.",
        "is_featured": False,
        "participant_count": 1812
    },
    {
        "virtual_id": "40601c24-4ec9-49a2-a9a1-3c8f75f47c6e",
        "campaign_name": "French Voice Data Campaign",
        "language_code": "fr",
        "description": "Shape tomorrow's AI today! Record simple phrases in French.",
        "is_featured": False,
        "participant_count": 2013
    },
    {
        "virtual_id": "89c3528d-aa60-4e90-a55e-c4f6163fb7fc",
        "campaign_name": "Spanish Voice Data Campaign",
        "language_code": "es",
        "description": "Help democratize AI technology by sharing your Spanish voice.",
        "is_featured": False,
        "participant_count": 3019
    },
    {
        "virtual_id": "3fae6080-4a35-48f7-948c-721dc1aae2e6",
        "campaign_name": "Korean Voice Data Campaign",
        "language_code": "ko",
        "description": "Join our mission to build inclusive AI by contributing voice samples in Korean.",
        "is_featured": True,
        "participant_count": 4112
    },
    {
        "virtual_id": "0d800fe2-d8b8-4078-99f0-311cf365c649",
        "campaign_name": "Japanese Voice Data Campaign",
        "language_code": "ja",
        "description": "Shape tomorrow's AI today! Record simple phrases in Japanese.",
        "is_featured": True,
        "participant_count": 2398
    },
    {
        "virtual_id": "da9842c2-39cc-4e96-9e0e-07a6a52687e6",
        "campaign_name": "Hindi Voice Data Campaign",
        "language_code": "hi",
        "description": "Your voice matters! Contribute to our Hindi voice dataset.",
        "is_featured": True,
        "participant_count": 5677
    }
]

def get_campaign_by_id(campaign_id):
    for campaign in CAMPAIGNS:
        if campaign["virtual_id"] == campaign_id:
            return campaign
    return None

def get_campaigns_by_language(language_code):
    return [campaign for campaign in CAMPAIGNS if campaign["language_code"] == language_code]

def get_all_language_codes():
    return list(set(campaign["language_code"] for campaign in CAMPAIGNS))

def get_featured_campaigns():
    return [campaign for campaign in CAMPAIGNS if campaign["is_featured"]]

def get_random_campaigns(count):
    import random
    return random.sample(CAMPAIGNS, min(count, len(CAMPAIGNS)))