import cv2
import os

# -----------------------------
# CONFIG
# -----------------------------
DIFF_THRESHOLD = 0.1
MAX_SEGMENTS = 6

NORMAL_INTERVAL_SEC = 0.5
FOCUS_INTERVAL_SEC = 0.25

def should_sample(current_sec, duration):
    #First second interval 
    if(current_sec <= 1):
        return True,FOCUS_INTERVAL_SEC
    
    if (current_sec >= duration -1):
        return True, FOCUS_INTERVAL_SEC
    
    return True,NORMAL_INTERVAL_SEC


def detect_segments(video_path: str, output_dir: str):
    """
    Videoyu tarar ve DIFF_THRESHOLD'u asan MAX_SEGMENTS adet "key frame"i 
    output_dir (dizinine) cikartir. Sonuc dondurulen listenin uzunlugu ile anlasilir.
    """
    os.makedirs(output_dir, exist_ok=True)

    #------------------------------
    # OPEN VIDEO
    # -----------------------------
    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        raise ValueError("Could not read FPS from video.")
        
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps

    prev_hist = None
    frame_index = 0
    candidate_frames = []
    last_sample_frame = -999

    # -----------------------------
    # PROCESS VIDEO
    # -----------------------------
    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break
        
        current_sec = frame_index / fps
        sample, interval_sec = should_sample(current_sec, duration)
        frame_interval = int(fps * interval_sec)

        # Modulo yerine fark hesabıyla frame seçiyoruz:
        if frame_index - last_sample_frame >= frame_interval:
            last_sample_frame = frame_index

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            cv2.normalize(hist, hist)

            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)

                if diff > DIFF_THRESHOLD:
                    filename = os.path.join(output_dir, f"candidate_{len(candidate_frames)}.jpg")
                    cv2.imwrite(filename, frame)
                    candidate_frames.append(filename)

            else:
                # first frame always save
                filename = os.path.join(output_dir, f"candidate_{len(candidate_frames)}.jpg")
                cv2.imwrite(filename, frame)
                candidate_frames.append(filename)
                
            prev_hist = hist

        frame_index += 1

    cap.release()

    # -----------------------------
    # FILTER CANDIDATES TO MAX_SEGMENTS
    # -----------------------------
    final_frames = []

    if len(candidate_frames) <= MAX_SEGMENTS:
        final_frames = candidate_frames
    else:
        # 1. İlk 2 kareyi kesin al
        # 2. Son 1 kareyi kesin al
        # 3. Kalan boşluğa ortadaki kareleri eşit dağıt
        
        selected_indices = [0, 1] 
        
        needed_middle = MAX_SEGMENTS - 3
        middle_candidates = list(range(2, len(candidate_frames) - 1))
        
        if needed_middle > 0 and middle_candidates:
            step = len(middle_candidates) / needed_middle
            for i in range(needed_middle):
                idx = int(i * step)
                selected_indices.append(middle_candidates[idx])
                
        # Son elemanı ekle
        selected_indices.append(len(candidate_frames) - 1)
        
        # Gereksiz tekrarı önle ve sırala
        selected_indices = sorted(list(set(selected_indices)))
        
        # Seçilenleri final listesine koy, seçilmeyenleri diskten sil
        for i, path in enumerate(candidate_frames):
            if i in selected_indices:
                final_frames.append(path)
            else:
                if os.path.exists(path):
                    os.remove(path)

    # Son karelerin isimlerini segment_0, segment_1 vs diye temizle
    saved_frames = []
    for i, old_path in enumerate(final_frames):
        new_path = os.path.join(output_dir, f"segment_{i}.jpg")
        if os.path.exists(old_path):
            if os.path.exists(new_path) and new_path != old_path:
                os.remove(new_path) 
            os.rename(old_path, new_path)
            
        saved_frames.append(new_path)

    return saved_frames

# Video test arayuzu
if __name__ == "__main__":
    detect_segments("video.mp4", "segments/test_video")
