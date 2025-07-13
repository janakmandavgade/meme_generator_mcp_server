
# Meme Generator MCP Server

Uses FastMCP (Model Context Protocol) for defining tools for the LLM.

This repo contains all mcp tools and prompts and resources required for the llm to fetch reddit memes, create memes, add in audio, etc

### Tools Contained

##### 1) Add two numbers - Adds Two Numbers
##### 2) download_random_meme - Downloads random meme from Reddit
##### 3) createVideo - Creates a meme video with background music.
##### 4) call_gemini_api - Gives info about downloaded meme
##### 5) upload_video_to_youtube - Upload Video to SignedIn users Youtube Channel


 

## Prerequisites

##### PYTHON=3.12.11
##### Git

For Deployment Purpose - Render.com Account
## Run Locally

Clone the project

```bash
  git clone https://github.com/janakmandavgade/meme_generator_mcp_server.git
```

Go to the project directory

```bash
  cd meme_generator_mcp_server
```

Install dependencies

```bash
  pip install -r requirements.txt
```

Start the server

```bash
  python app.py
```

