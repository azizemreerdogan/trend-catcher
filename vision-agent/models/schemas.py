from pydantic import BaseModel, Field

class VideoAnalysis(BaseModel):
    camera_style: str = Field(description="Kamera açısı veya çekim stili (Örn: Selfie tarzı, Elde, Sabit tripod vb.)")
    editing_pace: str = Field(description="Kurgu hızı (Örn: Hızlı kesimler, yavaş tempolu vb.)")
    visual_summary: str = Field(description="Videoda görsel olarak ne olup bittiğinin özeti")
    topic: str = Field(description="Videonun genel konusu veya içeriği")
    target_audience: str = Field(description="Hedef kitle (Örn: Gen-Z, öğrenciler, yazılımcılar vb.)")
    emotion: str = Field(description="Videodaki hakim duygu veya his (Örn: Eğlenceli, motive edici, sakin vb.)")
    hooks: list[str] = Field(description="Videoda izleyiciyi yakalayan kilit/hook anlar")

class TranscriptAnalysis(BaseModel):
    transcript: str = Field(description="Videoda tespit edilen tam konuşma metni")
    language: str = Field(description="Konuşulan ana dil (Örn: Türkçe, İngilizce)")
    keywords: list[str] = Field(description="Konuşmadaki anahtar kelimeler")
    tone: str = Field(description="Konuşmanın genel tonu (Örn: Ciddi, eğlenceli, agresif)")
