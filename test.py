import os
import json

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def call_gemini_api() -> dict:
    """
    Calls the Gemini API to generate a response based on the provided prompt.
    
    Args:
        prompt (str): The input prompt for the Gemini API.
        
    Returns:
        str: The generated response from the Gemini API.
    """
    # Initialize the client
    client = genai.Client(api_key=GEMINI_API_KEY)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    meme_base_dir = os.path.join(BASE_DIR, "data", "downloaded_memes")
    if not os.path.exists(os.path.join(BASE_DIR, "data", "downloaded_memes")):
        raise FileNotFoundError("No memes downloaded. Please download a meme first.")
    meme_image_name = os.listdir(meme_base_dir)[0]
    meme_full_path = os.path.join(meme_base_dir, meme_image_name)
    _, ext = os.path.splitext(meme_image_name)
    ext_no_dot = ext[1:]
    # image1_path = "path/to/image1.jpg"
    uploaded_file = client.files.upload(file=meme_full_path)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction="""You are a creative AI assistant specialized in meme audio. Given a meme image (Meme), choose exactly one audio style from this list:
                                    [ambient, club_beat, comedy_hiphop, funny, hyperpop, lofi, meme_music, phonk, rpg_fantasy_medieval, sad]
                                    Respond in JSON: {"style": <one style>, "reason": <brief justification>}."""
            ),
        contents=[
            "Can you strictly return only an audio style for this meme image using the list provided?",
            uploaded_file
        ],
    )

    print(f"Response: {json.loads(response.text)}")
    return json.loads(response.text)

call_gemini_api()