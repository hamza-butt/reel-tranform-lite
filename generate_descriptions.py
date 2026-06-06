import re
from pathlib import Path
import shutil

def process_transcripts():
    with open("all_transcripts.txt", "r", encoding="utf-8") as f:
        content = f.read()
    
    blocks = re.split(r"--- (.+?) ---", content)
    
    output_text = ""
    for i in range(1, len(blocks), 2):
        audio_name = blocks[i].strip()
        transcript = blocks[i+1].strip()
        
        # Original reel name from audio name
        reel_name = audio_name.replace(".mp3", ".mp4")
        
        # Create a simple engaging caption based on transcript
        words = transcript.split()
        if len(words) > 15:
            caption = " ".join(words[:15]) + "... 🤯 What do you think? Watch till the end to find out more! 👇"
        elif transcript:
            caption = transcript + " 🔥 Thoughts on this? Let us know below! 👇"
        else:
            caption = "Amazing insights! 🚀 What are your thoughts on this? Let us know below! 👇"
            
        # Create tags based on words
        tags_list = [w.strip(".,!?\"'()").lower() for w in words if len(w) > 4]
        # Get unique tags
        unique_tags = []
        for t in tags_list:
            if t not in unique_tags:
                unique_tags.append(t)
                
        # Default tags if not enough
        default_tags = ["ai", "tech", "future", "innovation", "technology", "trends", "startup", "business", "growth", "success"]
        final_tags = unique_tags[:10]
        while len(final_tags) < 10:
            for dt in default_tags:
                if dt not in final_tags:
                    final_tags.append(dt)
                    if len(final_tags) == 10:
                        break
        
        tags_str = " ".join(["#" + t for t in final_tags])
        
        entry = f"reelname: {reel_name}\ndescription: {caption}\ntags: {tags_str}\n\n"
        output_text += entry
        
    with open("all_reels_descriptions.txt", "w", encoding="utf-8") as f:
        f.write(output_text)
        
    print(output_text.strip())

if __name__ == "__main__":
    process_transcripts()
    
    # Delete audios and transcripts to keep folder clean
    if Path("reels_audios").exists():
        shutil.rmtree("reels_audios")
    if Path("all_transcripts.txt").exists():
        Path("all_transcripts.txt").unlink()
