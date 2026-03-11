import os
import json
from models.schemas import GrowthEngineResults

class GrowthEngineProvider:
    def __init__(self,data_root="catcher-data"):
        self.data_root=data_root
    
    def get_growth_engine_results(self,video_id):
        video_data_dir = os.path.join(self.data_root, video_id)
        growth_engine_result_path = os.path.join(video_data_dir, "growth_results.json")
        
        #If there is an actual growth data find it, or generate Mock data (for testing only)
        if os.path.exists(growth_engine_result_path):
            with open(growth_engine_result_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return GrowthEngineResults(**data)
        elif(os.getenv("USE_MOCK_DATA") == "true"):
            print("Using mock growth engine data")
            mock_data = GrowthEngineResults(
                delta_views=500,
                velocity=50,
                normalized_growth=0.5,
                final_growth_score=75,
            )
            os.makedirs(video_data_dir, exist_ok=True)
            with open(growth_engine_result_path, "w", encoding="utf-8") as f:
                json.dump(mock_data.model_dump(), f, indent=4, ensure_ascii=False)
            return mock_data
        else:
            raise FileNotFoundError(f"Growth engine results not found for video {video_id}")