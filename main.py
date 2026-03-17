import os
import requests
import subprocess
from fastapi import FastAPI, Request
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import smtplib
from email.message import EmailMessage

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

UPLOAD_DIR = "videos"
FRAME_DIR = "frames"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)


# -----------------------------
# Helper: Download video
# -----------------------------
def download_video(url, filename):
    r = requests.get(url)
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(r.content)
    return path


# -----------------------------
# Helper: Extract frames
# -----------------------------
def extract_frames(video_path):
    subprocess.run([
        "ffmpeg",
        "-i", video_path,
        "-vf", "fps=1",
        f"{FRAME_DIR}/frame_%03d.jpg"
    ])
    return sorted([f"{FRAME_DIR}/{f}" for f in os.listdir(FRAME_DIR)])[:20]


# -----------------------------
# Helper: AI analysis
# -----------------------------
def analyze_frames(frames, stroke, level):
    content = [
        {"type": "input_text", "text": f"""
You are a SwimSafer-certified assessor.

Level: {level}
Stroke: {stroke}

Evaluate based on:
- Body alignment
- Kick technique
- Arm stroke
- Breathing

Return STRICT format:

Score: (1-5)
Result: PASS or FAIL

Strengths:
- 

Weaknesses:
- 

Coaching Tips:
-
"""}
    ]

    for f in frames:
        content.append({
            "type": "input_image",
            "image_url": f
        })

    response = client.responses.create(
        model="gpt-5",
        input=[{"role": "user", "content": content}]
    )

    return response.output_text


# -----------------------------
# Helper: Generate PDF
# -----------------------------
def generate_pdf(name, result_text):
    file_path = f"{name}_report.pdf"

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = [
        Paragraph(f"SwimSafer Assessment Report: {name}", styles["Title"]),
        Spacer(1, 12),
        Paragraph(result_text, styles["BodyText"])
    ]

    doc.build(content)
    return file_path


# -----------------------------
# Helper: Send Email
# -----------------------------
def send_email(to_email, pdf_path):
    msg = EmailMessage()
    msg["Subject"] = "SwimSafer AI Assessment Report"
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = to_email

    msg.set_content("Attached is your SwimSafer assessment report.")

    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=pdf_path)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        smtp.send_message(msg)


# -----------------------------
# Webhook endpoint
# -----------------------------
@app.post("/webhook")
async def jotform_webhook(request: Request):
    data = await request.json()

    # ⚠️ Adjust keys based on your Jotform field IDs
    name = data["name"]
    email = data["email"]
    video_url = data["video"]
    stroke = data["stroke"]
    level = data["level"]

    # 1. Download video
    video_path = download_video(video_url, "swim.mp4")

    # 2. Extract frames
    frames = extract_frames(video_path)

    # 3. AI analysis
    result = analyze_frames(frames, stroke, level)

    # 4. Generate PDF
    pdf_path = generate_pdf(name, result)

    # 5. Send email
    send_email(email, pdf_path)

    return {"status": "processed"}
