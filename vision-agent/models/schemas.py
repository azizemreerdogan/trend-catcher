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
    is_music_only: str = Field(description="Seste doğal bir konuşma yoksa, SADECE müzik/şarkı çalıyorsa True olmalı.")

class EngagementMetrics(BaseModel):
    views: int = Field(description="Videonun izlenme sayısı")
    likes: int = Field(description="Videonun beğeni sayısı")
    comment_count: int = Field(description="Videonun yorum sayısı")
    share_count: int = Field(description="Videonun paylaşım sayısı")
    save_count: int = Field(description="Videonun kaydetme sayısı")
    engagement_rate: float = Field(description="Videonun etkileşim oranı (Beğeni + Yorum + Paylaşım + Kaydetme) / İzlenme sayısı")

class GrowthEngineResults(BaseModel):
    delta_views: int = Field(description="Videonun izlenme sayısı")
    velocity: int = Field(description="Videonun etkileşim artış hızı")
    normalized_growth: float = Field(description="Videonun normalize edilmiş büyüme skoru")
    final_growth_score: int = Field(description="Videonun genel büyüme skoru")
    