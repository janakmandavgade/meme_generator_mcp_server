from fastmcp import FastMCP
import requests
import os
import json
import time
import mimetypes
from urllib.parse import urlparse
from datetime import datetime
import urllib3
import json
import os
from pathlib import Path
from moviepy import ImageClip, CompositeVideoClip, ColorClip, AudioFileClip, VideoFileClip, AudioClip, concatenate_audioclips
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path
from youtube_video_upload.upload_video import my_custom_uploader
import base64

load_dotenv()
# import gradio as gr

os.environ.setdefault("DANGEROUSLY_OMIT_AUTH", "true")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("BASE_DIR")
os.makedirs(BASE_DIR, exist_ok=True)
OUT_PATH = os.path.join(BASE_DIR, "data", "generated_video", "out.mp4")
random_meme_path = os.path.join(BASE_DIR,"data","downloaded_memes")

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> dict:
    """Add two numbers"""
    result = {
        "result": a+b
    }
    return result

@mcp.tool
def download_random_meme(save_dir=random_meme_path, subreddit=None, max_retries=5):
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

            base_name = f"downloaded_meme{ext}"

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
def createVideo(meme_image_name=None, audio_type=None, out_name="out.mp4", duration=3):
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
        # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        VIDEO_SIZE = (1080, 1920)
        IMG_WIDTH = 1080
        
        # Define the base directory for memes
        meme_base_dir = os.path.join(BASE_DIR, "data", "downloaded_memes")

        if meme_image_name is None:
            
            if not os.path.exists(os.path.join(BASE_DIR, "data", "downloaded_memes")):
                raise FileNotFoundError("No memes downloaded. Please download a meme first.")
            meme_image_name = os.listdir(meme_base_dir)[0]  

        print(meme_image_name)

        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        AUDIO_PATH = os.path.join(current_dir, "data", "audio")
        MEME_PATH = os.path.join(BASE_DIR, "data", "downloaded_memes", meme_image_name)
        OUT_PATH = os.path.join(BASE_DIR, "data", "generated_video", out_name)
        
        # audio_base_dir = os.path.join(BASE_DIR, "data", "audio")
        if audio_type is None:
            print("No audio type provided, using phonk as default.")
            if not os.path.exists(os.path.join(current_dir, "data", "audio", "phonk")):
                raise FileNotFoundError("No phonk dir")
            audio_phonk_path = os.path.join(AUDIO_PATH, "phonk")
            audio_name = os.listdir(audio_phonk_path)[0]  
            AUDIO_PATH = os.path.join(audio_phonk_path, audio_name)
        else:
            print(f"Using audio type: {audio_type}")
            audio_path = os.path.join(AUDIO_PATH, audio_type)
            print(f"Audio path: {audio_path}")
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"No audio found for type: {audio_type}")
            audio_name = os.listdir(audio_path)[0]  
            AUDIO_PATH = os.path.join(audio_path, audio_name)
            
        print(AUDIO_PATH)

        if not os.path.exists(MEME_PATH):
            raise FileNotFoundError(f"Meme image not found: '{MEME_PATH}'")
        
        if not os.path.exists(AUDIO_PATH):
            raise FileNotFoundError(f"Audio not found: '{AUDIO_PATH}'")
        
        if not os.access(os.path.dirname(OUT_PATH), os.W_OK):
            raise SystemError(f"Path Not Writable '{OUT_PATH}'")
        
        ext = Path(MEME_PATH).suffix.lower()

        # Add Audio
        # Loading audio file

        # if ext
        # audioclip = AudioFileClip(AUDIO_PATH).subclipped(0, duration)

        if ext == ".gif" or ext == ".mp4":
            print("Detected animated GIF meme.")
            gif_clip = VideoFileClip(MEME_PATH)

            

            # audioclip = AudioFileClip(AUDIO_PATH).subclipped(0, gif_clip.duration)
            audioclip = AudioFileClip(AUDIO_PATH)
            # If audio shorter, pad with silence to match video duration
            if audioclip.duration < audioclip.duration:
                silence_duration = gif_clip.duration - audioclip.duration
                # create a silent AudioClip at the same fps
                silent = AudioClip(lambda t: 0, duration=silence_duration, fps=audioclip.fps)
                audioclip = concatenate_audioclips([audioclip, silent])
            else:
                # trim if audio is longer
                audioclip = audioclip.subclipped(0, gif_clip.duration)

            gif_clip = gif_clip.resized(width=IMG_WIDTH).with_position(("center", "center"))
            clip = gif_clip.with_audio(audioclip)
        else:
            # Treat as static image
            clip = ImageClip(MEME_PATH, duration=duration).resized(width=IMG_WIDTH).with_position(("center", "center"))
            audioclip = AudioFileClip(AUDIO_PATH).subclipped(0, duration)
            clip = clip.with_audio(audioclip)

        print("Line 207")
        # Create a static clip
        # clip = ImageClip(MEME_PATH, duration=duration).resized(width=IMG_WIDTH).with_position(("center","center"))
        # clip = clip.with_audio(audioclip)
        
        # Create Background with black image.
        bg = ColorClip(size=VIDEO_SIZE, color=(0, 0, 0), duration=clip.duration)
        print("Line 214")
        # Overlay and save
        final = CompositeVideoClip([bg,clip])
        final.write_videofile(OUT_PATH, fps=24, codec="libx264", threads=6 )

        print("Line 219")
        print(f"Video created successfully: {OUT_PATH}")

        clip.close()
        audioclip.close()
        bg.close()
        final.close()

        with open(OUT_PATH, "rb") as f:
            video_bytes = f.read()
        # return {"video_bytes": video_bytes}

        video_b64 = base64.b64encode(video_bytes).decode('ascii')
        print(f"Video bytes encoded to base64, length: {video_b64} characters.")

        # Clean up
        if os.path.exists(meme_base_dir):
            for f in os.listdir(meme_base_dir):
                file_path = os.path.join(meme_base_dir, f)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        else:
            print("Directory does not exist.")

        return {"status": True, "video_bytes": video_b64}
    except Exception as e:
        print(f"Exception in create video is: {e}")
        return {"status": False}

# # @mcp.tool
# # def call_gemini_api() -> dict:
#     """
#     Calls the Gemini API to generate a response based on the provided prompt.
    
#     Args:
#         prompt (str): The input prompt for the Gemini API.
        
#     Returns:
#         str: The generated response from the Gemini API.
#     """
#     # Initialize the client
#     client = genai.Client(api_key=GEMINI_API_KEY)

#     BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#     meme_base_dir = os.path.join(BASE_DIR, "data", "downloaded_memes")
#     if not os.path.exists(os.path.join(BASE_DIR, "data", "downloaded_memes")):
#         raise FileNotFoundError("No memes downloaded. Please download a meme first.")
#     meme_image_name = os.listdir(meme_base_dir)[0]
#     meme_full_path = os.path.join(meme_base_dir, meme_image_name)
#     _, ext = os.path.splitext(meme_image_name)
#     ext_no_dot = ext[1:]
#     # image1_path = "path/to/image1.jpg"

#     if ext_no_dot == "gif":
#         print("Detected animated GIF meme.")
#         # For GIFs, we need to upload as a video
#         # Convert GIF to video format using moviepy
#         gif_clip = VideoFileClip(meme_full_path)
#         gif_clip.write_videofile(meme_full_path.replace(".gif", ".mp4"), codec="libx264")
#         os.remove(meme_full_path)  # Remove the temporary video file
#         meme_full_path = meme_full_path.replace(".gif", ".mp4")
#         ext_no_dot = "mp4" 

#     uploaded_file = client.files.upload(file=meme_full_path)

#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         config=types.GenerateContentConfig(
#             system_instruction="""You are a creative AI assistant specialized in meme audio. Given a meme image (Meme), choose exactly one audio style from this list:
#                                     [ambient, club_beat, comedy_hiphop, funny, hyperpop, lofi, meme_music, phonk, rpg_fantasy_medieval, sad]
#                                     Respond in JSON: {"style": <one style>, "reason": <brief justification>}."""
#             ),
#         contents=[
#             "Can you strictly return only an audio style for this meme image using the list provided?",
#             uploaded_file
#         ],
#     )

#     print(f"Response: {json.loads(response.text)}")
#     return json.loads(response.text)

@mcp.tool
def call_gemini_api() -> dict:
    """
    Calls the Gemini API to generate a response based on the provided meme image.
    Returns:
        dict: The generated response from Gemini in JSON format.Like {"status": True, "audio_type": <audio type>, "title": "Title here", "description": "description here", "keywords":"keywords1, keyword2, keyword3, # keyword4 etc"}
    """
    # Initialize Gemini client
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Locate meme
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    meme_base_dir = os.path.join(BASE_DIR, "data", "downloaded_memes")

    if not os.path.exists(meme_base_dir):
        raise FileNotFoundError("No memes downloaded.")

    meme_image_name = os.listdir(meme_base_dir)[0]
    meme_full_path = os.path.join(meme_base_dir, meme_image_name)
    _, ext = os.path.splitext(meme_image_name)
    ext_no_dot = ext[1:].lower()

    # Convert GIF to MP4 if needed
    if ext_no_dot == "gif" or ext_no_dot == "mp4":
        print("Detected animated GIF meme or mp4.")
        clip = VideoFileClip(meme_full_path)
        if ext_no_dot == "gif":
            new_path = meme_full_path.replace(".gif", ".mp4")
        else:
            new_path = meme_full_path
        clip.write_videofile(new_path, codec="libx264")
        clip.close()
        os.remove(meme_full_path)
        meme_full_path = new_path
        ext_no_dot = "mp4"

    # Upload file to Gemini
    uploaded_file = client.files.upload(file=meme_full_path)

    # Wait until file is ACTIVE
    file_id = uploaded_file.name  # or uploaded_file.id depending on SDK version
    print(f"Uploaded file ID: {file_id}")

    # Polling for ACTIVE status
    timeout = 30  # seconds
    interval = 2
    waited = 0

    while waited < timeout:
        file_status = client.files.get(name=file_id)
        if file_status.state == "ACTIVE":
            print("File is ACTIVE.")
            break
        print("Waiting for file to become ACTIVE...")
        time.sleep(interval)
        waited += interval
    else:
        raise TimeoutError(f"File {file_id} did not become ACTIVE in time.")

    # Call Gemini with prompt + image
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction="""
You are a creative AI assistant specialized in memes. Given a meme image (Meme), choose exactly one audio style from this list:
[ambient, club_beat, comedy_hiphop, funny, hyperpop, lofi, meme_music, phonk, rpg_fantasy_medieval, sad]
Also provide a suitable title, description and keywords for the meme that is going to be uploaded on youtube.

Respond in JSON in the format: {"style": <one style>, "title": "<insert_title_here>", "description": "<Insert funny meme description here>" , "keywords": "keywords here comma (,) seperated"}.

NEVER add ```json``` or any other formatting. Just return the JSON object directly.
"""
        ),
        contents=[
            "Can you strictly return only an audio style for this meme image using the list provided along with title, description and keywords appropriate for a youtube short?",
            file_status  # use the fully ready file object
        ],
    )

    try:
        print("Response received from Gemini API.", response.text)
        parsed = json.loads(response.text)
        print(f"Response: {parsed}")

        
        return {"status": True, "audio_type": parsed["style"], "title": parsed["title"], "description": parsed["description"], "keywords": parsed["keywords"]}
    except Exception as e:
        print("Failed to parse response as JSON.")
        return {"status": False, "error": str(e)}

@mcp.tool
def upload_video_to_youtube(
        file_path: str= OUT_PATH,
        title: str = "Test Video",
        description: str = "Test automated upload",
        category: str = "23",
        keywords: str = "meme,funny,dank,geeks",
        privacy_status: str = "public",
        access_token: str = None,
        refresh_token: str = None
    ) -> dict:
    """
    Uploads a video to YouTube using the provided parameters.

    Args:
        file_path (str): Path to the video file.
        title (str): Title of the video.
        description (str): Description of the video.
        category (str): Category ID for the video.
        keywords (str): Comma-separated keywords for the video.
        privacy_status (str): Privacy status of the video ('public', 'private', 'unlisted').
        access_token(str): OAuth 2.0 access token for YouTube API.
        refresh_token(str): OAuth 2.0 refresh token for YouTube API.

    Returns:
        dict: Response from YouTube API or error message.
    """
    try:
        print(f"Uploading video of : {file_path}")
        my_custom_uploader(
            file_path,
            title,
            description,
            category,
            keywords,
            privacy_status,
            access_token,
            refresh_token,
        )

        # Clean up the generated video file
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Removed temporary video file: {file_path}")

        return {"status": True, "message": "Video uploaded successfully.", }
    except Exception as e:
        print(f"Error uploading video: {e}")
        os.remove(file_path)
        # os.remove(random_meme_path)
        return {"status": False, "error": str(e)}

if __name__ == "__main__":
    # mcp.run(transport="streamable-http",host="127.0.0.1", port=8000, path="/mcp")
    mcp.run(transport="streamable-http",host="0.0.0.0", port=8000, path="/mcp")