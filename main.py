import os, base64, subprocess, requests
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()
client = OpenAI()

def download(url):
    r = requests.get(url)
    with open("video.mp4","wb") as f: f.write(r.content)

def frames():
    subprocess.run(["ffmpeg","-i","video.mp4","-vf","fps=1","f_%03d.jpg"])
    return sorted([f for f in os.listdir() if f.endswith(".jpg")])[:10]

def b64(p):
    return base64.b64encode(open(p,"rb").read()).decode()

@app.post("/analyze")
async def analyze(req: Request):
    d = await req.json()
 video_url = d.get("video") or d.get("video_upload") or d.get("Video Upload")

if not video_url:
    return {"error": f"Missing video field. Received keys: {list(d.keys())}"}

download(video_url)

    imgs = [{"type":"input_text","text":f"""
SwimSafer assessment.
Level:{d['level']} Stroke:{d['stroke']}

Return:
Score (1-5)
PASS/FAIL
Strengths
Weaknesses
Tips
"""}]

    for f in frames():
        imgs.append({"type":"input_image","image_base64":b64(f)})

    r = client.responses.create(
        model="gpt-5",
        input=[{"role":"user","content":imgs}]
    )

    return {"result": r.output_text}
client = OpenAI(api_key="sk-xxxxx")
