import random
from typing import List, Dict
from logger import get_logger
from campaigns import CAMPAIGNS, get_random_campaigns
import config

logger = get_logger('CampaignManager')

class CampaignManager:
    
    def __init__(self, email, position, total_accounts):
        self.email = email
        self.position = position
        self.total_accounts = total_accounts
        self.selected_campaigns = []
        self.campaign_tasks = {}

    def select_random_campaigns(self) -> List[Dict]:
        try:
            campaigns_count = random.randint(
                config.CAMPAIGNS_COUNT_RANGE["min"],
                config.CAMPAIGNS_COUNT_RANGE["max"]
            )
            
            self.selected_campaigns = get_random_campaigns(campaigns_count)
            
            for campaign in self.selected_campaigns:
                tasks_count = random.randint(
                    config.TEXTS_PER_CAMPAIGN_RANGE["min"],
                    config.TEXTS_PER_CAMPAIGN_RANGE["max"]
                )
                self.campaign_tasks[campaign["virtual_id"]] = tasks_count
            
            logger.info(f"Выбрано {len(self.selected_campaigns)} кампаний для обработки", 
                       email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            for i, campaign in enumerate(self.selected_campaigns):
                tasks_count = self.campaign_tasks[campaign["virtual_id"]]
                logger.info(f"Кампания {i+1}: {campaign['campaign_name']} ({campaign['language_code']}) - {tasks_count} заданий", 
                           email=self.email, position=f"{self.position}/{self.total_accounts}")
            
            return self.selected_campaigns
            
        except Exception as e:
            logger.error(f"Ошибка выбора кампаний: {e}", 
                        email=self.email, position=f"{self.position}/{self.total_accounts}")
            return []

    def get_tasks_count_for_campaign(self, campaign_id: str) -> int:
        return self.campaign_tasks.get(campaign_id, 1)

    def get_selected_campaigns(self) -> List[Dict]:
        return self.selected_campaigns

    def get_total_tasks_count(self) -> int:
        return sum(self.campaign_tasks.values())