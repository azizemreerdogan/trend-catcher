import json
import os
from models.schemas import VideoAnalysis
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file at the project root (TrendCatcher)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path)

def analyze_video_strip(strip_image_path: str):
    """
    Şerit (strip) tarzında birleştirilmiş resim dosyasını Gemini 2.5 Flash'a
    göndererek JSON çıktısı alır.
    """
    if not os.path.exists(strip_image_path):
        raise FileNotFoundError(f"Strip image not found at {strip_image_path}")
        
    client = genai.Client()
    
    # 2. Upload the file to the Gemini API
    # Dosya boyutu ve API maliyeti optimize edilebilir
    print(f"Uploading image to Gemini: {strip_image_path}")
    myfile = client.files.upload(file=strip_image_path)
    
    prompt = (
        "Bu dikey şerit (strip) kısa form bir videonun (ör. TikTok/Reels) zaman akışına göre sıralanmış karelerini (framelerini) içermektedir.\n"
        "Görsellerdeki sahneleri, çekim türlerini, hissettirilen duygusal bağı ve izleyiciyi yakalayan (hook) anları çıkar."
    )
    
    # Generate content using Gemini 2.5 Flash with Structured Outputs
    print("Calling Gemini 2.5 Flash API for structured analysis...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[prompt, myfile],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VideoAnalysis,
        ),
    )
    
    try:
        # Pydantic schema json dönecek
        result_json = json.loads(response.text)
        return result_json
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return {"error": "Invalid JSON response", "raw_text": response.text}
