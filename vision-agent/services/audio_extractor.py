import subprocess
import shutil
import os

def _find_ffmpeg():
    """ffmpeg binary'sini PATH veya bilinen konumlarda arar."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    
    # Winget varsayilan kurulum yolu
    winget_links = os.path.join(
        os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links", "ffmpeg.exe"
    )
    if os.path.exists(winget_links):
        return winget_links
    
    raise FileNotFoundError(
        "ffmpeg bulunamadi. Lutfen terminalinizi yeniden baslatin veya ffmpeg'i PATH'e ekleyin."
    )

def extract_audio(video_path, output_audio="audio.wav"):
    """Video dosyasindan ses parcasini WAV formatinda cikarir."""
    ffmpeg_bin = _find_ffmpeg()
    
    command = [
        ffmpeg_bin,
        "-y",
        "-i", video_path,
        "-q:a", "0",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        output_audio
    ]
    
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_audio
