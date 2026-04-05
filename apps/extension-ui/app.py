from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import requests
import uuid
import yt_dlp
import cv2  # <--- NEW: For video frame extraction
import glob # <--- NEW: To find the downloaded video file

app = Flask(__name__)
CORS(app) 

SAVE_DIR = "intercepted_posts"
os.makedirs(SAVE_DIR, exist_ok=True)

# Helper function to slice the video into frames
def extract_frames(video_path, output_folder, num_frames=10):
    print(f"🎞️ Extracting {num_frames} frames from video...")
    vidcap = cv2.VideoCapture(video_path)
    total_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames <= 0:
        print("⚠️ Could not read total frames.")
        return

    # Calculate the step size to grab evenly spaced frames
    step = max(1, total_frames // num_frames)
    
    count = 0
    saved_count = 0
    
    while True:
        success, image = vidcap.read()
        if not success:
            break
            
        # Save a frame every 'step' amount
        if count % step == 0 and saved_count < num_frames:
            frame_path = os.path.join(output_folder, f"video_frame_{saved_count}.jpg")
            cv2.imwrite(frame_path, image)
            saved_count += 1
            
        count += 1
        
    vidcap.release()
    print(f"✅ Saved {saved_count} frames to {output_folder}")


@app.route('/verify', methods=['POST'])
def verify_post():
    data = request.json
    post_id = data.get('postId', str(uuid.uuid4())[:8])
    post_folder = os.path.join(SAVE_DIR, f"post_{post_id}")
    os.makedirs(post_folder, exist_ok=True)
    
    print(f"\n📥 Received new post. Saving to: {post_folder}")

    # 1. Save Text Data
    metadata = {
        "context_url": data.get("contextUrl", ""),
        "scraped_text": data.get("text", ""),
        "timestamp": data.get("timestamp", "")
    }
    with open(os.path.join(post_folder, "data.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)
        
    # 2. Save Standard Images
    image_urls = data.get('imageUrls', [])
    for i, url in enumerate(image_urls):
        try:
            if url.startswith('http') and not 'blob:' in url: 
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    with open(os.path.join(post_folder, f"image_{i}.jpg"), 'wb') as img_file:
                        for chunk in response.iter_content(1024):
                            img_file.write(chunk)
        except Exception as e:
            print(f"⚠️ Failed to download image: {e}")

    # 3. Save Video & Extract Frames
    context_url = data.get("contextUrl", "")
    if context_url:
        print(f"🎥 Checking for videos at: {context_url}")
        try:
            ydl_opts = {
                'outtmpl': os.path.join(post_folder, 'video_main.%(ext)s'),
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([context_url])
                print("✅ Video successfully downloaded!")
                
            # Find the video we just downloaded (yt-dlp might save it as .mp4, .webm, etc.)
            downloaded_videos = glob.glob(os.path.join(post_folder, "video_main.*"))
            if downloaded_videos:
                # Send it to our OpenCV function to slice into 10 frames
                extract_frames(downloaded_videos[0], post_folder, num_frames=10)
                
        except Exception as e:
            print(f"⚠️ No video found or page is private.")

    # 4. Mock AI Response
    import random
    score = random.randint(10, 99)
    is_authentic = score > 50
    return jsonify({
        "status": "Verified" if is_authentic else "Suspicious",
        "score": score,
        "reasoning": "AI Analysis complete." if is_authentic else "Warning: Manipulated media detected."
    })

if __name__ == '__main__':
    print("🚀 TrustMeBro Backend running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)