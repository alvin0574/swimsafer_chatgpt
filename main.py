import os, base64, subprocess, requests, glob
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -------------------------
# Download video
# -------------------------
def download(url):
    r = requests.get(url)
    with open("video.mp4", "wb") as f:
        f.write(r.content)


# -------------------------
# Clean old frames
# -------------------------
def clean_frames():
    for f in glob.glob("f_*.jpg"):
        os.remove(f)


# -------------------------
# Extract frames (LIMITED)
# -------------------------
def frames():
    subprocess.run([
        "ffmpeg",
        "-i", "video.mp4",
        "-vf", "fps=1",
        "f_%03d.jpg"
    ])
    return sorted([f for f in os.listdir() if f.startswith("f_")])[:5]  # ONLY 5 frames


# -------------------------
# Convert to base64
# -------------------------
def b64(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()


# -------------------------
# MAIN ENDPOINT
# -------------------------
@app.post("/analyze")
async def analyze(req: Request):
    try:
        d = await req.json()
        print("RECEIVED:", d)

        # 🔥 Handle Zapier variations
        video_url = d.get("video") or d.get("video_upload") or d.get("Video Upload")

        if isinstance(video_url, list):
            video_url = video_url[0]

        if not video_url:
            return {"error": f"No video found. Keys: {list(d.keys())}"}

        # Step 1: download
        download(video_url)

        # Step 2: clean old frames
        clean_frames()

        # Step 3: extract frames
        frame_list = frames()

        # Step 4: build prompt
        imgs = [{
            "type": "input_text",
            "text": f"""
You are a SwimSafer assessor.

Level: {d.get('level')}
Stroke: {d.get('stroke')}

Score:
Body Position (1-5)
Kick (1-5)
Arm Stroke (1-5)
Breathing (1-5)

Return:

Overall Score:
PASS/FAIL

Strengths:
-

Weaknesses:
-

Tips:
-
"""
        }]

        # Step 5: add images (FIXED FORMAT)
        for f in frame_list:
            base64_image = b64(f)
            imgs.append({
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{base64_image}"
            })

        # Step 6: OpenAI call (WITH ERROR HANDLING)
        response = client.responses.create(
            model="gpt-5",
            input=[{"role": "user", "content": imgs}]
        )

        return {"result": response.output_text}

    except Exception as e:
        print("ERROR:", str(e))
        return {"error": str(e)}
