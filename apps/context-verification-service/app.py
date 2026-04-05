from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import time
import json
import requests
import base64
import yt_dlp
import glob  # 👉 ADDED: Your friend's library to find the downloaded video!
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Gemini Client
client = genai.Client()

IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")

@app.route('/api/verify', methods=['POST'])
def verify_post():
    try:
        data = request.get_json()
        
        # 1. Destructure the frontend data
        account_name = data.get('accountName', 'Unknown')
        account_link = data.get('accountLink', '')
        caption = data.get('caption', '')
        media_base64 = data.get('mediaBase64')
        media_type = data.get('mediaType', 'image')
        post_url = data.get('postUrl', '')

        # 👉 NEW: Extract post timing data from frontend
        post_date_iso = data.get('postDate')
        relative_time = data.get('relativeTime', 'unknown')

        # Parse the post date for the prompt
        try:
            from datetime import datetime, timezone
            if post_date_iso:
                # Handle ISO format with/without timezone
                post_date = datetime.fromisoformat(post_date_iso.replace('Z', '+00:00'))
                post_date_str = post_date.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            else:
                post_date_str = "Unknown publication date"
        except Exception as e:
            print(f"⚠️ Could not parse postDate: {e}")
            post_date_str = "Unknown publication date"# 👉 NEW: Timing context for Gemini's analysis       

        print(f"\n📥 [STEP 1] Received request from account: {account_name}")
        print(f"🔗 Post Link: {post_url}")
        print(f"📸 Media Type: {media_type}")

        if not media_base64:
            return jsonify({"error": "Missing mediaBase64"}), 400

        # Clean the Base64 string
        clean_base64 = re.sub(r'^data:image\/(png|jpeg|jpg|webp);base64,', '', media_base64)

        # 👉 1.5 NEW: YT-DLP Video Downloader Logic (Upgraded with friend's glob trick!)
        video_uri = None
        downloaded_file_path = None
        
        if media_type == 'video' and post_url:
            print(f"🎥 [STEP 1.5] Attempting to download video using yt-dlp from: {post_url}")
            try:
                # 👉 FIX: Let yt-dlp figure out the correct extension (.mp4, .webm, etc)
                base_filename = f"temp_video_{int(time.time())}"
                ydl_opts = {
                    'outtmpl': f"{base_filename}.%(ext)s", 
                    'format': 'best',
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([post_url])
                
                # 👉 FIX: Use glob to find the file, just like your friend did
                found_files = glob.glob(f"{base_filename}.*")
                
                if found_files:
                    downloaded_file_path = found_files[0]
                    print(f"✅ [STEP 1.5] Video downloaded successfully as {downloaded_file_path}! Uploading to Gemini...")
                    
                    # Upload directly to Google's servers so Gemini can watch it
                    video_file = client.files.upload(file=downloaded_file_path)
                    
                    # Wait for processing
                    while video_file.state.name == "PROCESSING":
                        print("⏳ Waiting for Gemini to process video audio/frames...")
                        time.sleep(2)
                        video_file = client.files.get(name=video_file.name)
                    
                    if video_file.state.name == "FAILED":
                        print("⚠️ Gemini failed to process the video.")
                    else:
                        video_uri = video_file
                        print("✅ [STEP 1.5] Video ready for AI analysis!")
            except Exception as e:
                print("⚠️ [STEP 1.5] yt-dlp failed to download the video:", e)

        # 2. Extract links from caption and use Jina Reader API
        article_text = "No linked article provided."
        url_regex = r'(https?://[^\s]+)'
        links = re.findall(url_regex, caption)
        
        if links:
            try:
                jina_response = requests.get(f"https://r.jina.ai/{links[0]}")
                article_text = jina_response.text[:1500]
                print(f"📝 [STEP 2] Jina Extracted Text: {article_text[:50]}...")
            except Exception as e:
                print("Jina Reader failed:", e)

        # 3. Upload the Base64 frame to ImgBB
        image_url = ""
        try:
            imgbb_res = requests.post(
                f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}",
                data={"image": clean_base64}
            )
            imgbb_data = imgbb_res.json()
            image_url = imgbb_data.get("data", {}).get("url", "")
            print(f"☁️ [STEP 3] ImgBB Public URL: {image_url}")
        except Exception as e:
            print("ImgBB upload failed:", e)


            

        # 4. Reverse Image Search via SerpApi (Provenance Mode)
        visual_matches_text = "Reverse image search failed or was skipped."
        if image_url:
            try:
                serp_url = f"https://serpapi.com/search.json?engine=google_lens&url={image_url}&api_key={SERPAPI_API_KEY}&type=about_this_image"
                serp_response = requests.get(serp_url)
                serp_data = serp_response.json()
                
                about_data = serp_data.get("about_this_image", {})
                sections = about_data.get("sections", [])
                
                match_details = []
                log_details = [] # 👉 Added for your personal terminal logging

                for section in sections:
                    for result in section.get("page_results", []):
                        title = result.get("title")
                        source = result.get("source")
                        publish_date = result.get("date", "Date unknown")
                        link = result.get("link", "No URL available") # 👉 Grab the URL
                        
                        # Data for Gemini (Keep it concise)
                        match_details.append(f"Source: {source} | Date: {publish_date} | Title: {title}")
                        
                        # Data for YOUR terminal (Includes the link)
                        log_details.append(f"📍 {source} ({publish_date})\n   🔗 Link: {link}\n   📝 Title: {title}")

                if match_details:
                    visual_matches_text = " | ".join(match_details[:3])
                    
                    # 👉 Print detailed logs to your terminal for manual checking
                    print("\n🕵️‍♂️ [STEP 4] DETAILED SEARCH HISTORY:")
                    for log in log_details[:3]:
                        print(log)
                else:
                    print("🕵️‍♂️ [STEP 4] No provenance history found.")
                    visual_matches_text = "No previous matches found. This media might be new or unique."

            except Exception as e:
                print("SerpApi search failed:", e)

        # 5. Pass everything to Gemini 2.5 Flash
        today = datetime.now().strftime("%A, %B %d, %Y") # e.g., "Sunday, April 05, 2026"

        print(f"🧠 [STEP 5] Asking Gemini to analyze context (Today is {today})...")
        
        prompt_text = f"""
        You are an expert digital forensics AI participating in a fact-checking hackathon. 
        Your task is to analyze social media posts for Contextual Consistency (Axis 2).

        ### TIMING CONTEXT:
        - Current Date/Time: {today}
        - Post Was Published: {post_date_str} ({relative_time} ago)

        ### MANDATORY FORENSIC ANALYSIS STEPS:

        1. **ON-SCREEN TEXT EXTRACTION (OCR):**
        - Extract ALL text visible IN the image/video itself (e.g., news banners, tickers, chyrons, signs, documents)
        - For this post: Extract the Arabic text from the red "عاجل" (Breaking News) banner
        - Translate or summarize what this on-screen text says
        - ⚠️ This is your PRIMARY evidence - the actual news content being shared

        2. **VISUAL CONTEXT ANALYSIS:**
        - Identify logos (Al Jazeera, CNN, etc.), landmarks, people, clothing, settings
        - Note any visual elements that indicate context (press conference, meeting, event)

        3. **CAPTION ASSESSMENT:**
        - Check if the user's caption contains meaningful text OR just metadata
        - Metadata indicators: numbers + time units only (e.g., "1w", "33.6K", "439", "2m")
        - If caption is metadata-only, IGNORE it and rely on ON-SCREEN TEXT (Step 1) instead
        - If caption has actual descriptive text, compare it against the on-screen text

        4. **CROSS-REFERENCE VERIFICATION:**
        - Compare the ON-SCREEN TEXT (Step 1) against:
            * Reverse Search History dates and sources
            * Post Publication Date: {post_date_str}
        - Does the news content match what was happening around {post_date_str}?
        - Do reverse search results show this same image/banner from similar dates?

        5. **TEMPORAL CONSISTENCY CHECK:**
        - If reverse search shows this image from BEFORE {post_date_str}, it may be recycled/out of context
        - If reverse search shows this image from AFTER {post_date_str}, it's likely a later repost
        - If reverse search matches around {post_date_str}, it's likely contemporary and authentic

        ### DATA PACKET:
        1. POST PUBLISHER: "{account_name}" (Profile URL: {account_link})
        2. POST PUBLICATION DATE: {post_date_str} (Relative: {relative_time} ago)
        3. USER'S CAPTION: "{caption}"
        - ⚠️ If this is just numbers/metadata (e.g., "1w 33.6K 439"), treat it as engagement metrics, NOT the news content
        4. LINKED ARTICLE CONTENT: "{article_text}"
        5. REVERSE IMAGE SEARCH HISTORY: "{visual_matches_text}"

        ### CRITICAL DECISION RULES:

        ✅ **VERIFY** if:
        - On-screen text (OCR) matches the news context from the publication date
        - Reverse search shows similar usage around {post_date_str}
        - Account is credible (e.g., verified news organization)

        🔴 **FLAG AS SUSPICIOUS** if:
        - On-screen text mentions a date/event that contradicts {post_date_str}
        - Reverse search shows this image is from months/years before {post_date_str}
        - On-screen text describes something completely different from what the caption claims

        ### TASK: 
        Based on your Forensic Steps, is this post using the media in an authentic, contemporary context, or is it recycled/out of context?

        **Focus on the ON-SCREEN TEXT (the actual news banner/chyron) as your primary evidence, NOT the user's caption if it's just metadata.**
        """

        # Build the contents list
        contents = [prompt_text]
        
        if video_uri:
            contents.append(video_uri)
        else:
            image_bytes = base64.b64decode(clean_base64)
            image_part = types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
            contents.append(image_part)

        # Call Gemini with Structured JSON Output
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "status": {"type": "STRING", "enum": ["Verified", "Suspicious"]},
                        "confidenceScore": {"type": "INTEGER", "description": "Number 0-100"},
                        "reasoning": {"type": "STRING", "description": "2-3 sentences explaining visual/search history clues."}
                    },
                    "required": ["status", "confidenceScore", "reasoning"]
                }
            )
        )

        final_json = json.loads(response.text.strip())
        print("🧠 [STEP 5] Final Output:\n", final_json)

        # Cleanup
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            os.remove(downloaded_file_path)
            print("🧹 Cleaned up local video file.")
        if video_uri:
            client.files.delete(name=video_uri.name)
            print("🧹 Cleaned up Gemini cloud video file.")

        return jsonify(final_json)

    except Exception as error:
        print("API Error:", error)
        return jsonify({
            "status": "Error",
            "confidenceScore": 0,
            "reasoning": "The backend server encountered an error processing this request."
        }), 500

if __name__ == '__main__':
    app.run(port=3000, debug=True, use_reloader=False)