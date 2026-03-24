import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pprint import pprint
import json
import time

from services.engagement_provider import EngagementProvider
from services.growth_engine_provider import GrowthEngineProvider
from services.metadata_provider import MetadataProvider
from agents.fusion_agent import FusionAgent


def _write_stage_error(video_data_dir, file_name, stage, message):
    path = os.path.join(video_data_dir, file_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "status": "error",
                "stage": stage,
                "message": message,
            },
            f,
            indent=4,
            ensure_ascii=False,
        )
    print(f"{stage.title()} error -> {path}")

# ------------------------------------------------
# FAZ 1 YARDIMCI FONKSIYONLARI (Servis Hazırlığı)
# ------------------------------------------------
def _prepare_vision(video_path, output_dir, video_data_dir, video_id):
    """Frame extraction + Strip creation (sıralı, kendi içinde)."""
    from services.segment_detector import detect_segments
    from services.strip_creator import create_vertical_strip

    print("\n--- [Thread-Vision] Extracting Frames ---")
    saved_frames = detect_segments(video_path, output_dir)
    print(f"[Thread-Vision] Extracted {len(saved_frames)} key frames.")
    
    if not saved_frames:
        raise RuntimeError("No frames were extracted.")
    
    print("[Thread-Vision] Creating Vertical Strip...")
    strip_path = os.path.join(video_data_dir, f"{video_id}_strip.jpg")
    create_vertical_strip(saved_frames, strip_path, max_width=600)
    return strip_path

def _prepare_audio(video_path, video_data_dir):
    """FFmpeg ile ses cikarimi."""
    from services.audio_extractor import extract_audio

    print("\n--- [Thread-Audio] Extracting Audio ---")
    audio_path = os.path.join(video_data_dir, "audio.wav")
    extract_audio(video_path, audio_path)
    print(f"[Thread-Audio] Audio extracted to: {audio_path}")
    return audio_path

def _int_env(name: str, default: int) -> int:
    """Read positive integer env var; fallback to default."""
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except ValueError:
        return default

def _run_stage_pipeline(executor, video_path, output_dir, video_data_dir, video_id, durations_ms):
    """Stage-triggered flow: start each agent as soon as its prep is ready."""
    strip_path = None
    audio_path = None
    vision_result = None
    transcript_result = None
    stage_errors = {"vision": None, "transcript": None}

    pending = {}
    start_times = {}

    from agents.vision_agent import analyze_video_strip
    from agents.transcript_agent import analyze_audio

    vision_prep = executor.submit(_prepare_vision, video_path, output_dir, video_data_dir, video_id)
    audio_prep = executor.submit(_prepare_audio, video_path, video_data_dir)
    pending[vision_prep] = ("prep", "vision")
    pending[audio_prep] = ("prep", "transcript")
    start_times[vision_prep] = time.perf_counter()
    start_times[audio_prep] = time.perf_counter()

    while pending:
        completed = next(as_completed(list(pending)))
        stage, branch = pending.pop(completed)
        elapsed_ms = int((time.perf_counter() - start_times.pop(completed)) * 1000)

        try:
            result = completed.result()
        except Exception as e:
            print(f"\n[{stage.upper()}::{branch.upper()}] Error: {e}")
            stage_errors[branch] = str(e)
            continue

        if stage == "prep":
            if branch == "vision":
                strip_path = result
                durations_ms["prep_vision_ms"] = elapsed_ms
                print(f"[PREP::VISION] Completed in {elapsed_ms} ms. Vision agent starting...")
                future = executor.submit(analyze_video_strip, strip_path)
                pending[future] = ("agent", "vision")
                start_times[future] = time.perf_counter()
            else:
                audio_path = result
                durations_ms["prep_audio_ms"] = elapsed_ms
                print(f"[PREP::TRANSCRIPT] Completed in {elapsed_ms} ms. Transcript agent starting...")
                future = executor.submit(analyze_audio, audio_path)
                pending[future] = ("agent", "transcript")
                start_times[future] = time.perf_counter()
            continue

        if branch == "vision":
            vision_result = result
            durations_ms["agent_vision_ms"] = elapsed_ms
        else:
            transcript_result = result
            durations_ms["agent_transcript_ms"] = elapsed_ms
        print(f"[AGENT::{branch.upper()}] Completed in {elapsed_ms} ms.")

    return vision_result, transcript_result, stage_errors

# ------------------------------------------------
# ANA PIPELINE
# ------------------------------------------------
def run_pipeline(video_id: str):
    """
    Iki fazli paralel pipeline:
      Faz 1: Frame+Strip || Audio extraction (servisler)
      Faz 2: Vision Agent || Transcript Agent (Gemini API calls)
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    video_data_dir = os.path.join(project_root, "catcher-data", video_id)
    output_dir = os.path.join(video_data_dir, "segments")
    
    if not os.path.exists(video_data_dir):
        print(f"Error: Directory not found at {video_data_dir}")
        return

    # Video dosyasini otomatik bul
    valid_extensions = ('.mp4', '.mov', '.avi', '.mkv')
    video_path = None
    for file in os.listdir(video_data_dir):
        if file.lower().endswith(valid_extensions):
            video_path = os.path.join(video_data_dir, file)
            break
            
    if not video_path:
        print(f"Error: No valid video file found in {video_data_dir}")
        return

    default_thread_workers = min(8, (os.cpu_count() or 4) * 2)
    thread_workers = _int_env("THREAD_WORKERS", default_thread_workers)
    print(f"\n[Config] THREAD_WORKERS={thread_workers}")

    # =============================================
    # PIPELINE: Hazirlanan branch aninda ilgili agent'a gider
    # =============================================
    print("\n========== Parallel Pipeline (Stage Triggered) ==========")
    vision_result = None
    transcript_result = None
    engagement_data = None
    growth_data = None
    video_metadata = None
    durations_ms = {}
    total_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=thread_workers) as executor:
        # Start fetching additional metadata concurrently
        def fetch_engagement():
            return EngagementProvider(os.path.join(project_root, "catcher-data")).get_engagement_data(video_id)
        def fetch_growth():
            return GrowthEngineProvider(os.path.join(project_root, "catcher-data")).get_growth_engine_results(video_id)
        def fetch_metadata():
            return MetadataProvider(os.path.join(project_root, "catcher-data")).get_metadata(video_id)

        future_eng = executor.submit(fetch_engagement)
        future_gro = executor.submit(fetch_growth)
        future_meta = executor.submit(fetch_metadata)

        # Run main vision/transcript stage-triggered pipeline
        vision_result, transcript_result, stage_errors = _run_stage_pipeline(
            executor, video_path, output_dir, video_data_dir, video_id, durations_ms
        )

        try:
            engagement_data = future_eng.result()
        except Exception as e:
            print(f"Error fetching engagement data: {e}")
            
        try:
            growth_data = future_gro.result()
        except Exception as e:
            print(f"Error fetching growth engine data: {e}")
            
        try:
            video_metadata = future_meta.result()
        except Exception as e:
            print(f"Error fetching video metadata: {e}")

    durations_ms["total_ms"] = int((time.perf_counter() - total_start) * 1000)

    # =============================================
    # SONUCLARI KAYDET
    # =============================================
    print("\n========== Saving Results ==========")
    
    if vision_result:
        path = os.path.join(video_data_dir, "vision_summary.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(vision_result, f, indent=4, ensure_ascii=False)
        print(f"Vision  → {path}")
        pprint(vision_result, indent=2)
    
    if transcript_result:
        path = os.path.join(video_data_dir, "transcript.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(transcript_result, f, indent=4, ensure_ascii=False)
        print(f"Transcript → {path}")
        pprint(transcript_result, indent=2)
    else:
        _write_stage_error(
            video_data_dir,
            "transcript.json",
            "transcript",
            stage_errors.get("transcript") or "Transcript stage did not produce a result. Check ffmpeg and Gemini logs.",
        )

    if not vision_result:
        _write_stage_error(
            video_data_dir,
            "vision_summary.json",
            "vision",
            stage_errors.get("vision") or "Vision stage did not produce a result. Check strip generation and Gemini logs.",
        )

    # =============================================
    # FAZ 3: Fusion Agent (Sentez)
    # =============================================
    if not vision_result or not transcript_result:
        print("\n========== FAZ 3: Skipping Fusion Agent ==========")
        print("Fusion skipped because vision or transcript stage did not complete successfully.")
        print("\n========== Timing ==========")
        pprint(durations_ms, indent=2)
        print("\n✅ Pipeline completed with partial results.")
        return

    print("\n========== FAZ 3: Running Fusion Agent ==========")
    fusion_start = time.perf_counter()
    try:
        fusion_agent = FusionAgent(data_root=os.path.join(project_root, "catcher-data"))
        fusion_result = fusion_agent.fuse(
            video_analysis=vision_result,
            transcript_analysis=transcript_result,
            engagement_metrics=engagement_data,
            growth_engine_results=growth_data,
            video_metadata=video_metadata
        )
        durations_ms["agent_fusion_ms"] = int((time.perf_counter() - fusion_start) * 1000)
        print("\n[FUSION AGENT] Completed successfully.")
        
        if fusion_result:
            path = os.path.join(video_data_dir, "fusion_summary.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(fusion_result, f, indent=4, ensure_ascii=False)
            print(f"Fusion → {path}")
            pprint(fusion_result, indent=2)
            
    except Exception as e:
        durations_ms["agent_fusion_ms"] = int((time.perf_counter() - fusion_start) * 1000)
        print(f"\n[FUSION AGENT] Error: {e}")

    print("\n========== Timing ==========")
    pprint(durations_ms, indent=2)

    print("\n✅ Pipeline completed.")
