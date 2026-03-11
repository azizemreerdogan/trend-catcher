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

class VideoMetadata(BaseModel):
    title: str = Field(description="Videonun başlığı veya açıklaması")
    author: str = Field(description="Videoyu yayınlayan kanal/kişi")
    platform: str = Field(description="Videonun platformu (Örn: TikTok, Instagram, YouTube)")
    duration: int = Field(default=0, description="Saniye cinsinden video süresi")

#As the last step, we will create a schema for the final fusion result that combines all the insights from the vision,
#transcript, engagement, growth, and metadata analyses.
class FusionResult(BaseModel):
    dominant_topic: str = Field(description="Videonun baskın ana konusu")
    content_category: str = Field(description="İçerik kategorisi (ör: education, entertainment, fitness)")
    trend_potential: str = Field(description="Trend potansiyeli: low / medium / high")
    viral_score: int = Field(description="0-100 arası viral olma skoru")
    trend_reasoning: str = Field(description="Bu sonuca neden ulaşıldığının kısa açıklaması")
    audience_match: str = Field(description="İçeriğin hedef kitle ile uyum seviyesi")
    content_audio_alignment: str = Field(description="Görsel ve ses uyumu")
    growth_interpretation: str = Field(description="Büyüme verisinin yorumu")
    engagement_interpretation: str = Field(description="Engagement verisinin yorumu")
    recommended_action: str = Field(description="Takip edilmeli / watchlist / ignore")