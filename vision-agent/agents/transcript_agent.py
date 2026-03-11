import json
import os
from models.schemas import TranscriptAnalysis
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env file at the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path)

def analyze_audio(audio_path: str):
    """
    Ses dosyasini Gemini 1.5 Flash ile metne cevirir ve
    bir Pydantic/Dictionary objesi gibi dondurur.
    Hem hizli hem de JSON formatinda garantili donus yapar.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found at {audio_path}")
        
    client = genai.Client()
    
    print(f"Uploading audio to Gemini for transcription: {audio_path}")
    myfile = client.files.upload(file=audio_path)
    
    prompt = (
    "Bu ses dosyasını (kısa form video sesi) dinle ve harfi harfine metne çevir. "
    "ÖNEMLİ KURAL: Eğer seste bir insanın doğal konuşması yoksa, yani sadece bir şarkı "
    "veya arka plan müziği çalıyorsa, şarkı sözlerini KESİNLİKLE metne çevirme! "
    "Tüm şarkı sözlerini yazmak yerine 'transcript' alanına sadece '[Arka Plan Müziği]' veya '[Şarkı]' yaz. "
    "Ayrıca konuşulan dili (language) (eğer sadece müzikse boş bırak), anahtar kelimeleri (keywords) ve "
    "genel duygu tonunu (tone - örn: Eğlenceli Müzik, Nostaljik, Hareketli) belirle."
    )
    
    print("Calling Gemini 2.5 Flash API for audio analysis...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[prompt, myfile],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TranscriptAnalysis,
        ),
    )
    
    try:
        result_json = json.loads(response.text)
        return result_json
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return {"error": "Invalid JSON response", "raw_text": response.text}
