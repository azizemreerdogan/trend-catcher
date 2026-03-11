import os
import json 
from google import genai
from google.genai import types
from models.schemas import FusionResult
from dotenv import load_dotenv

# Load environment variables from .env file at the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path)

class FusionAgent:
    def __init__(self, data_root="catcher-data"):
        self.data_root = data_root
    
    def fuse(
        self,
        video_analysis,
        transcript_analysis,
        engagement_metrics,
        growth_engine_results,
        video_metadata
    ):
        client = genai.Client()
        
        # Gelen sözlük/json verilerini string olarak düzenli bir şekilde string'e çeviriyoruz
        # Bu LLM'in halüsinasyon yapmasını azaltır ve veriyi daha iyi parse etmesini sağlar.
        #dict objesi değilken de çalışabilmesi için
        def safe_dump(obj):
            if obj is None:
                return "{}"
            if hasattr(obj, "model_dump"):
                return json.dumps(obj.model_dump(), indent=2, ensure_ascii=False)
            if hasattr(obj, "dict"):
                return json.dumps(obj.dict(), indent=2, ensure_ascii=False)
            return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
        
        v_analysis_str = safe_dump(video_analysis)
        t_analysis_str = safe_dump(transcript_analysis)
        e_metrics_str = safe_dump(engagement_metrics)
        g_results_str = safe_dump(growth_engine_results)
        v_metadata_str = safe_dump(video_metadata)
        
        prompt = f"""
Aşağıda bir kısa form videonun (TikTok/Reels/Shorts formatında) farklı ajanlar tarafından analiz edilmiş verileri bulunmaktadır.
Bu verileri inceleyerek videonun genel bir sentezini (fusion) yapmanı ve istenilen JSON formatında yanıt vermeni bekliyorum.
Lütfen sadece sana verilen verilere dayanarak analiz yap, varsayımlarda bulunma.

1. Video Görsel Analizi:
{v_analysis_str}

2. Video Transkript Analizi:
{t_analysis_str}

3. Etkileşim (Engagement) Metrikleri:
{e_metrics_str}

4. Büyüme (Growth Engine) Sonuçları:
{g_results_str}

5. Video Meta Verileri:
{v_metadata_str}

Yukarıdaki verilere dayanarak lütfen FusionResult şemasına uygun olarak nihai analiz sonucunu oluştur.
"""
        print("Calling Gemini 2.5 Flash API for Fusion synthesis calculation...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FusionResult,
                temperature=0.1,  # Halüsinasyonu azaltmak için düşük sıcaklık
            ),
        )
        
        try:
            result_json = json.loads(response.text if response.text else "{}")
            return result_json
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response in FusionAgent: {e}")
            return {"error": "Invalid JSON response", "raw_text": response.text}