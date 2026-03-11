import os
import json
from models.schemas import VideoMetadata

class MetadataProvider:
    def __init__(self, data_root="catcher-data"):
        self.data_root = data_root
        
    def get_metadata(self, video_id: str) -> VideoMetadata:  
        video_data_dir = os.path.join(self.data_root, video_id)
        metadata_path = os.path.join(video_data_dir, "video_metadata.json")
        
        # If there is an actual video_metadata.json file, return it or create a mock one 
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return VideoMetadata(**data)
        elif os.getenv("USE_MOCK_DATA") == "true":
            print("Using mock video metadata")
            mock_data = VideoMetadata(
                title="Akordiyon Patates🍟🥔🥔\nMalzemeleri anlatmaya gerek yok😅\nSos içeriği (ketçap,mayonez, kekik)\nPatatesleri dikdörtgen keselim.\nSonrasında çubukları iki yanına koyalım.\nBir yüzünü düz diğer yüzünü çapraz bir şekilde keselim.\nŞeritler halinde kestikten sonra, yağda kızartalım.\nAfiyet olsun😊",
                author="TechGuru",
                platform="Instagram",
                duration=45
            )
            os.makedirs(video_data_dir, exist_ok=True)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(mock_data.model_dump(), f, indent=4, ensure_ascii=False)
            return mock_data
        else:
            raise FileNotFoundError(f"Video metadata not found for video {video_id}")
