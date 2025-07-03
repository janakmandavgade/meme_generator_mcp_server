from fastmcp import FastMCP
import requests
import os
import mimetypes
from urllib.parse import urlparse
from datetime import datetime
import urllib3
import json
import os
from pathlib import Path
from moviepy import ImageClip, CompositeVideoClip, ColorClip, AudioFileClip
# import gradio as gr

import os
os.environ["DANGEROUSLY_OMIT_AUTH"] = "true"

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> dict:
    """Add two numbers"""
    result = {
        "result": 50
    }
    return result

@mcp.tool
def download_random_meme(save_dir="downloaded_memes", subreddit=None, max_retries=5):
    """
    Downloads a random meme (or from a specific subreddit) using Meme API,
    but retries if the meme’s base filename already exists or on transient errors.

    Args:
        save_dir (str): Folder where the meme will be saved.
        subreddit (str, optional): If provided, fetch meme from this subreddit.
        max_retries (int): How many times to retry before giving up.

    Returns:
        dict: Metadata about the saved meme, or None if failed.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    os.makedirs(save_dir, exist_ok=True)

    api_base = "https://meme-api.com/gimme"
    if subreddit:
        api_base += f"/{subreddit}"

    attempts = 0
    while attempts < max_retries:
        attempts += 1
        try:
            # 1) Fetch meme JSON
            resp = requests.get(api_base, verify=False, timeout=10)
            resp.raise_for_status()
            meme = resp.json()

            # 2) Skip bad content
            if meme.get("nsfw") or meme.get("spoiler"):
                print(f"⚠️ NSFW/spoiler, retrying ({attempts}/{max_retries})…")
                continue

            # 3) Build base filename (no timestamp)
            title = meme["title"].replace("/", "_").strip()
            sub = meme["subreddit"]
            url = meme["url"]
            parsed = urlparse(url)
            ext = os.path.splitext(parsed.path)[-1]
            if not ext:
                head = requests.head(url, verify=False, timeout=5)
                mime = head.headers.get("Content-Type", "")
                ext = mimetypes.guess_extension(mime) or ".jpg"

            base_name = f"{sub}_{title}{ext}"

            # 4) Check collision
            existing = [f for f in os.listdir(save_dir) if f.endswith(base_name)]
            if existing:
                print(f"⚠️ Already have {base_name}, retrying ({attempts}/{max_retries})…")
                continue

            # 5) Download & save
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{base_name}"
            filepath = os.path.join(save_dir, filename)

            img_resp = requests.get(url, verify=False, timeout=10)
            img_resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(img_resp.content)

            print(f"✅ Saved new meme: {filepath}")
            return {
                "title": title,
                "author": meme.get("author"),
                "subreddit": sub,
                "file": filepath,
                "url": url,
                "postLink": meme.get("postLink"),
                "ups": meme.get("ups", 0),
            }

        except requests.exceptions.RequestException as net_err:
            print(f"❌ Network error ({net_err}), retrying ({attempts}/{max_retries})…")
        except OSError as fs_err:
            print(f"❌ File system error ({fs_err}), aborting.")
            break
        except Exception as e:
            print(f"❌ Unexpected error ({e}), retrying ({attempts}/{max_retries})…")

    print("⚠️ Failed to download a new meme after maximum retries.")
    return None

@mcp.tool
def createVideo(meme_image_name, audio_name, out_name, duration):
    """
    Creates a video using audios, and an image of a meme. 

    Args:
        meme_image_name (str): Name of the image inside of the default saved dir.
        audio_name (str): Name of the audio file inside of the default saved dir.
        out_name (str): Name of the output video file
        duration (int): Duration of the video.

    Returns:
        dict: Returns if video was created successfully or not with status key.
    """
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
        return {"status": True}
    except Exception as e:
        print(f"Exception in create video is: {e}")
        return {"status": False}

if __name__ == "__main__":
    mcp.run(transport="streamable-http",host="127.0.0.1", port=8000, path="/mcp")