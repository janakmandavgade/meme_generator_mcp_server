import requests
import os
import mimetypes
from urllib.parse import urlparse
from datetime import datetime

# Folder to save memes
SAVE_FOLDER = "downloaded_memes"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Meme API endpoint
API_URL = "https://meme-api.com/gimme"

def get_meme():
    try:
        response = requests.get(API_URL, verify=False)
        if response.status_code != 200:
            print("❌ Failed to fetch meme.")
            return None
        meme = response.json()

        if meme.get("nsfw") or meme.get("spoiler"):
            print("⚠️ NSFW or spoiler meme skipped.")
            return None

        return meme
    except Exception as e:
        print(f"❌ Error fetching meme: {e}")
        return None

def download_meme(meme):
    meme_url = meme['url']
    title = meme['title'].replace("/", "_")
    author = meme['author']
    subreddit = meme['subreddit']

    parsed = urlparse(meme_url)
    ext = os.path.splitext(parsed.path)[-1]
    if not ext:
        mime = requests.head(meme_url, verify=False).headers.get("Content-Type", "")
        ext = mimetypes.guess_extension(mime) or ".jpg"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{subreddit}_{title}{ext}"
    filepath = os.path.join(SAVE_FOLDER, filename)

    print(f"⬇️ Downloading meme: {title} by u/{author} [{subreddit}]")

    try:
        img_data = requests.get(meme_url, verify=False).content
        with open(filepath, "wb") as f:
            f.write(img_data)
        print(f"✅ Saved to {filepath}\n")
    except Exception as e:
        print(f"❌ Failed to download meme image: {e}")

def main():
    meme = get_meme()
    if meme:
        download_meme(meme)

if __name__ == "__main__":
    # Disable InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    main()
