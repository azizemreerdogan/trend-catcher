from models.schemas import EngagementMetrics
import os
import json 


class EngagementProvider:
    def __init__(self, data_root="catcher-data"):
        self.data_root = data_root
        
    def get_engagement_data(self, video_id:str) -> EngagementMetrics:  
        video_data_dir = os.path.join(self.data_root, video_id)
        engagement_path = os.path.join(video_data_dir, "engagement.json")
        
        #If there is an actual engagement.json file, return it or create a mock one 
        if os.path.exists(engagement_path):
            with open(engagement_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return EngagementMetrics(**data)
        elif(os.getenv("USE_MOCK_DATA") == "true"):
            print("Using mock engagement data")
            mock_data = EngagementMetrics(
                views=1000,
                likes=100,
                comment_count=10,
                share_count=10,
                save_count=10,
                engagement_rate=0.1,
            )
            os.makedirs(video_data_dir, exist_ok=True)
            with open(engagement_path, "w", encoding="utf-8") as f:
                json.dump(mock_data.model_dump(), f, indent=4, ensure_ascii=False)
            return mock_data
        else:
            raise FileNotFoundError(f"Engagement data not found for video {video_id}")  
            
            
            
            