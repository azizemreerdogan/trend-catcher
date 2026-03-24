# 🔍 TrendCatcher

**AI-powered short-form video analysis pipeline** that extracts visual and audio insights from TikTok/Reels-style videos using Google Gemini 2.5 Flash.

> Videoları indirin, agentlara verin, trend olup olmadığını anlayın.

---

## 🏗️ Architecture

```
TrendCatcher/
├── .env                          # API keys (GEMINI_API_KEY)
├── .gitignore
├── README.md
├── catcher-data/                 # Video veritabanı (her video kendi klasöründe)
│   ├── video/
│   │   ├── video.mp4             # Orijinal video dosyası
│   │   ├── segments/             # Çıkarılan key frame'ler
│   │   ├── video_strip.jpg       # Birleştirilmiş dikey şerit (grid)
│   │   ├── audio.wav             # Çıkarılan ses dosyası
│   │   ├── vision_summary.json   # Gemini görsel analiz çıktısı
│   │   └── transcript.json       # Gemini ses analiz çıktısı
│   └── video1/
│       └── ...
│
└── vision-agent/                 # Ana analiz modülü
    ├── main.py                   # Entry point
    ├── orchestrator.py           # Pipeline yöneticisi (paralel çalıştırma)
    ├── agents/                   # AI Agent'lar (LLM çağrıları)
    │   ├── vision_agent.py       # Görsel analiz (Gemini 2.5 Flash)
    │   └── transcript_agent.py   # Ses analiz (Gemini 2.5 Flash)
    ├── services/                 # Deterministik işçi servisleri
    │   ├── segment_detector.py   # OpenCV ile key frame çıkarma
    │   ├── strip_creator.py      # Frame'leri dikey şerite birleştirme
    │   └── audio_extractor.py    # FFmpeg ile ses ayırma
    ├── models/
    │   └── schemas.py            # Pydantic veri şemaları
    └── tests/
        └── test_agents.py        # Agent unit testleri
```

## 🧠 How It Works

Pipeline iki fazlı **paralel** mimari ile çalışır:

```
FAZ 1 — Servisler (Paralel)
  Thread A: Video → Key Frames → Dikey Strip Görseli
  Thread B: Video → FFmpeg → audio.wav

FAZ 2 — AI Agent'lar (Paralel)  
  Thread A: Strip Görseli → Gemini Vision → vision_summary.json
  Thread B: audio.wav → Gemini Audio → transcript.json
```

### Vision Agent Çıktısı
```json
{
    "camera_style": "Selfie tarzı, Elde, Dinamik yakın çekimler",
    "editing_pace": "Hızlı kesimler, Dinamik",
    "visual_summary": "Bir benzin istasyonunda lüks bir spor araba...",
    "topic": "Lüks araba şakası, beklenmedik komik anlar",
    "target_audience": "Gençler, Gen-Z, araba tutkunları",
    "emotion": "Eğlenceli, şaşırtıcı, komik",
    "hooks": ["Motor bölmesinin patlamış mısırla dolu olması", "..."]
}
```


```

## 🚀 Quick Start

### 1. Kurulum

```bash
# Repo'yu klonla
git clone https://github.com/azizemreerdogan/trend-catcher.git
cd TrendCatcher

# Virtual environment oluştur ve aktif et
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate     # macOS/Linux

# Bağımlılıkları yükle
pip install opencv-python pillow google-genai pydantic python-dotenv pytest
```

### 2. FFmpeg Kurulumu

```bash
# Windows (winget)
winget install -e --id Gyan.FFmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### 3. API Key Ayarla

Proje kök dizinine `.env` dosyası oluştur:

```env
GEMINI_API_KEY=your_api_key_here
```

> API key almak için: https://aistudio.google.com/apikey

### 4. Video Ekle ve Çalıştır

```bash
# catcher-data altına video klasörü oluştur
mkdir catcher-data\my_video

# Video dosyasını kopyala
copy path\to\video.mp4 catcher-data\my_video\

# Pipeline'ı çalıştır (klasör adını ver)
cd vision-agent
python3 main.py my_video
```

## 🧪 Tests

```bash
cd vision-agent
python3 -m pytest tests/ -v
```

Testler Gemini API'ını **mock'layarak** çalışır — gerçek API çağrısı yapmaz, para harcamaz.

Instagram scraper testleri:

```bash
./.venv/bin/python -m pytest instagram-scraper/tests -v
```

## 📦 Instagram Scraper v1

Instagram uzerinde bulunan reel/video metadata bilgisini toplayip `instagram-scraper/data/videos.json` dosyasina yazar.

Ilk calistirma:

```bash
cd instagram-scraper
python3 scripts/save_instagram_state.py
```

Bu script Instagram login ekranini acar. Girisi manuel yapin, sonra terminale donup Enter tusuna basin. Playwright auth state dosyasi `instagram-scraper/auth/state.json` olarak kaydedilir.

Scraper calistirma:

```bash
cd instagram-scraper
python3 main.py --max-links 20
```

Akis:
- Browser context `auth/state.json` ile acilir
- Baslangic sayfasi `https://www.instagram.com/reels/`
- Scroll ile reel linkleri toplanir
- Linkler normalize edilip benzersiz hale getirilir
- Her reel icin metadata cikarilir
- Veriler `video_id` bazli dedup ile JSON dosyasina yazilir

Hata durumlari:
- `auth/state.json` yoksa scraper anlamli hata verir ve once `python3 scripts/save_instagram_state.py` calistirmanizi ister
- Playwright kurulu degilse kurulum komutunu soyler
- Sayfadan metadata parse edilemezse ilgili reel `failed_items` olarak sayilir

## 💰 Cost Analysis

Strip + Audio Gemini mimarisi sayesinde maliyet son derece düşüktür:

| Ölçek | Tahmini Maliyet |
|---|---|
| 1 video | ~$0.0005 |
| 1,000 video | ~$0.52 |
| 10,000 video | ~$5.20 |
| 100,000 video | ~$52 |

> Frame'leri tek bir strip görsele birleştirmek, token sayısını dramatik şekilde düşürür.

## 🛣️ Roadmap

- [x] Vision Agent (Gemini 2.5 Flash — görsel analiz)
- [x] Transcript Agent (Gemini 2.5 Flash — ses analiz)
- [x] Paralel pipeline (ThreadPoolExecutor)
- [x] Modüler mimari (agents / services / models)
- [x] Unit tests
- [ ] Fusion Agent (Vision + Transcript birleştirme)
- [ ] Trend Analyzer Agent (batch analiz + trend tespiti)
- [ ] Instagram/TikTok scraper entegrasyonu
- [ ] Vector DB ile semantik kümeleme
- [ ] Dashboard / API endpoint

## 📄 License

MIT

---

Built with ❤️ and Gemini 2.5 Flash
