import os
from pathlib import Path
from moviepy import ImageClip, CompositeVideoClip, ColorClip, AudioFileClip

# from moviepy.audio.io.AudioFileClip import AudioFileClip
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# VIDEO_SIZE = (1080, 1920)
# IMG_WIDTH = 1080

def createVideo(meme_image_name, audio_name, out_name, duration):
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        VIDEO_SIZE = (1080, 1920)
        IMG_WIDTH = 1080
        
        AUDIO_PATH = os.path.join(BASE_DIR, "data", "audio", audio_name)
        MEME_PATH = os.path.join(BASE_DIR, "data", "downloaded_memes", meme_image_name)
        OUT_PATH = os.path.join(BASE_DIR, "data", "generated_video", out_name)
        
        if not os.path.exists(MEME_PATH):
            raise FileNotFoundError(f"Meme image not found: '{MEME_PATH}'")
        
        if not os.path.exists(AUDIO_PATH):
            raise FileNotFoundError(f"Audio not found: '{AUDIO_PATH}'")
        
        if not os.access(os.path.dirname(OUT_PATH), os.W_OK):
            raise SystemError(f"Path Not Writable '{OUT_PATH}'")
        
        
        # Add Audio
        # Loading audio file
        audioclip = AudioFileClip(AUDIO_PATH).subclipped(0, duration)
        
        # Create a static clip
        clip = ImageClip(MEME_PATH, duration=duration).resized(width=IMG_WIDTH).with_position(("center","center"))
        clip = clip.with_audio(audioclip)
        
        # Create Background with black image.
        bg = ColorClip(size=VIDEO_SIZE, color=(0, 0, 0), duration=clip.duration)
        
        # Overlay and save
        final = CompositeVideoClip([bg,clip])
        final.write_videofile(OUT_PATH, fps=24, codec="libx264", threads=6 )
    
    except Exception as e:
        print(f"Exception in create video is: {e}")
        return None

createVideo("image.png", "audio.mp3", "out.mp4", 5)
