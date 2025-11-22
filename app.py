from flask import Flask, request, send_file, Response
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import ImageSequenceClip, VideoFileClip
import cv2
import os
import random

app = Flask(__name__)

# -------------------
# Asset paths (same folder)
HAND_VIDEO = "hand_writing.mp4"
PEN_TIP = "pen_tip.png"
SHAPE = "tiger_silhouette.png"
FONT_PATH = "arial.ttf"  # Ensure this font exists in your system

# -------------------
# HTML page embedded
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Signature Video Generator</title>
    <style>
        body { font-family: Arial; text-align:center; margin-top:50px; background:#f0f0f0;}
        input, button { padding:10px; font-size:18px; margin:10px; }
        h1 { margin-bottom: 40px; }
    </style>
</head>
<body>
    <h1>Generate Your AI Signature Video</h1>
    <form method="post" action="/generate">
        <input type="text" name="name" placeholder="Enter Your Name" required />
        <br/>
        <button type="submit">Generate Video</button>
    </form>
</body>
</html>
"""

@app.route('/')
def index():
    return Response(HTML_PAGE, mimetype="text/html")

@app.route('/generate', methods=['POST'])
def generate():
    name = request.form.get("name", "").strip()
    if not name:
        return "Please enter a valid name"
    video_file = create_signature_video(name)
    return send_file(video_file, as_attachment=True)

# -------------------
def create_signature_video(name):
    width, height = 1080, 1920
    font_size = 140

    hand_clip = VideoFileClip(HAND_VIDEO).resize(height=height).crop(x1=0, y1=0, width=width, height=height)
    pen_tip_img = Image.open(PEN_TIP).convert("RGBA").resize((40,40))
    shape_img = Image.open(SHAPE).convert("L").resize((width, height))
    shape_array = np.array(shape_img)

    total_frames = int(hand_clip.fps * hand_clip.duration)
    char_len = len(name)
    stroke_progress = 0.0

    # Approx pen positions
    pen_positions = [(width//2, height//2) for _ in range(total_frames)]
    particles = []

    frames = []
    for i in range(total_frames):
        img = Image.new("RGBA", (width, height), (255,255,255,0))
        draw = ImageDraw.Draw(img)

        # Stroke progression
        stroke_progress += char_len / total_frames
        progress_index = int(stroke_progress)
        current_text = name[:progress_index]

        # Draw text
        text_x, text_y = 100, height//2
        draw.text((text_x, text_y), current_text, font=ImageFont.truetype(FONT_PATH, font_size), fill="black")

        # Pen tip overlay
        pen_x, pen_y = pen_positions[i]
        img.paste(pen_tip_img, (int(pen_x), int(pen_y)), pen_tip_img)

        # Generate ink particles
        for _ in range(5):
            particles.append({
                "x": pen_x + random.randint(-5,5),
                "y": pen_y + random.randint(-5,5),
                "vx": random.uniform(-1,1),
                "vy": random.uniform(-2,-0.5),
                "life": random.randint(10,20)
            })

        for p in particles:
            draw.ellipse((p["x"]-2, p["y"]-2, p["x"]+2, p["y"]+2), fill="black")
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
        particles = [p for p in particles if p["life"]>0]

        # Blend with silhouette
        gray_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2GRAY)
        mask = cv2.addWeighted(gray_frame, 0.7, shape_array, 0.3, 0)
        color_frame = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        frames.append(color_frame)

    final_clip = ImageSequenceClip(frames, fps=hand_clip.fps)
    output_file = f"{name}_signature.mp4"
    final_clip.write_videofile(output_file, fps=hand_clip.fps, codec="libx264")
    return output_file

# -------------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
