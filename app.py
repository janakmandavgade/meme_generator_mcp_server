from fastmcp import FastMCP
import requests
import os
import mimetypes
from urllib.parse import urlparse
from datetime import datetime
import urllib3
import json
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

    
if __name__ == "__main__":
    mcp.run(transport="streamable-http",host="127.0.0.1", port=8000, path="/mcp")