import os
from pathlib import Path
from faster_whisper import WhisperModel

def transcribe_all():
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    audio_dir = Path("reels_audios")
    
    with open("all_transcripts.txt", "w", encoding="utf-8") as f:
        for audio_path in audio_dir.glob("*.mp3"):
            print(f"Transcribing {audio_path.name}...")
            segments, _ = model.transcribe(str(audio_path), beam_size=5)
            transcript = "".join([segment.text for segment in segments])
            f.write(f"--- {audio_path.name} ---\n")
            f.write(f"{transcript}\n\n")

if __name__ == "__main__":
    transcribe_all()
