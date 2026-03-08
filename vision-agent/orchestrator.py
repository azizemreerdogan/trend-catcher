import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.segment_detector import detect_segments
from services.strip_creator import create_vertical_strip
from services.audio_extractor import extract_audio
from agents.vision_agent import analyze_video_strip
from agents.transcript_agent import analyze_audio
from pprint import pprint
import json

# ------------------------------------------------
# FAZ 1 YARDIMCI FONKSIYONLARI (Servis Hazırlığı)
# ------------------------------------------------
def _prepare_vision(video_path, output_dir, video_data_dir, video_id):
    """Frame extraction + Strip creation (sıralı, kendi içinde)."""
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
    print("\n--- [Thread-Audio] Extracting Audio ---")
    audio_path = os.path.join(video_data_dir, "audio.wav")
    extract_audio(video_path, audio_path)
    print(f"[Thread-Audio] Audio extracted to: {audio_path}")
    return audio_path

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

    # =============================================
    # FAZ 1: Servisler Paralel (Frame+Strip || Audio)
    # =============================================
    print("\n========== FAZ 1: Preparing Data (Parallel) ==========")
    strip_path = None
    audio_path = None
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        vision_prep = executor.submit(_prepare_vision, video_path, output_dir, video_data_dir, video_id)
        audio_prep  = executor.submit(_prepare_audio, video_path, video_data_dir)
        
        try:
            strip_path = vision_prep.result()
        except Exception as e:
            print(f"Error in vision preparation: {e}")
            
        try:
            audio_path = audio_prep.result()
        except Exception as e:
            print(f"Error in audio preparation: {e}")

    # =============================================
    # FAZ 2: Agentlar Paralel (Vision || Transcript)
    # =============================================
    print("\n========== FAZ 2: Running Agents (Parallel) ==========")
    vision_result = None
    transcript_result = None
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}
        
        if strip_path:
            futures[executor.submit(analyze_video_strip, strip_path)] = "vision"
        if audio_path:
            futures[executor.submit(analyze_audio, audio_path)] = "transcript"
        
        for future in as_completed(futures):
            agent_name = futures[future]
            try:
                result = future.result()
                if agent_name == "vision":
                    vision_result = result
                else:
                    transcript_result = result
                print(f"\n[{agent_name.upper()} AGENT] Completed successfully.")
            except Exception as e:
                print(f"\n[{agent_name.upper()} AGENT] Error: {e}")

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
    
    print("\n✅ Pipeline completed.")
