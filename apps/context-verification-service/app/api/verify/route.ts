import { NextResponse } from 'next/server';
import { GoogleGenAI, Type } from '@google/genai';

// Initialize the Google Gemini client
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });

export async function POST(req: Request) {
  try {
    const body = await req.json();
    
    // 👉 1. UPDATED DESTRUCTURING: Now grabbing the account details
    const { accountName, accountLink, caption, mediaBase64 } = body;

    // 👉 2. NEW LOGS: Verify the frontend data arrived correctly
    console.log(`\n📥 [STEP 1] Received request from account: ${accountName}`);
    console.log(`🔗 Profile Link: ${accountLink || "None provided"}`);
    // ADDED LOG: Displaying the extracted caption (truncated to keep terminal clean)
    console.log(`💬 Caption: ${caption ? caption.substring(0, 100).replace(/\n/g, ' ') + (caption.length > 100 ? "..." : "") : "No caption provided"}`);
    console.log(`📸 Media received: ${mediaBase64 ? "Yes (Image or Video Frame Base64)" : "No"}`);

    if (!mediaBase64) {
      return NextResponse.json({ error: "Missing mediaBase64" }, { status: 400 });
    }

    // 1. Clean the Base64 string (Remove the data:image prefix if the frontend sent it)
    const cleanBase64 = mediaBase64.replace(/^data:image\/(png|jpeg|jpg|webp);base64,/, "");

    // 2. Extract links from caption and use Jina Reader API to get the blog text
    let articleText = "No linked article provided.";
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const links = caption.match(urlRegex);
    
    if (links && links.length > 0) {
        try {
            const jinaResponse = await fetch(`https://r.jina.ai/${links[0]}`);
            articleText = await jinaResponse.text();
            // Truncate to save tokens, we only need the gist of the article
            articleText = articleText.substring(0, 1500); 

            console.log(`📝 [STEP 2] Jina Extracted Text: ${articleText.substring(0, 50)}...`);

        } catch (e) {
            console.error("Jina Reader failed to fetch the blog text", e);
        }
    }

    // 3. Upload the Base64 frame to ImgBB to get a temporary public URL for SerpApi
    let imageUrl = "";
    try {
        const formData = new FormData();
        formData.append("image", cleanBase64);
        const imgbbRes = await fetch(`https://api.imgbb.com/1/upload?key=${process.env.IMGBB_API_KEY}`, {
            method: 'POST',
            body: formData
        });
        const imgbbData = await imgbbRes.json();
        imageUrl = imgbbData.data.url;

        console.log("☁️ [STEP 3] ImgBB Public URL:", imageUrl);

    } catch (e) {
        console.error("ImgBB upload failed", e);
    }

    // 4. Perform Reverse Image Search via SerpApi (Google Lens) using the ImgBB URL
    let visualMatchesText = "Reverse image search failed or was skipped.";
    if (imageUrl) {
        try {
            const serpUrl = `https://serpapi.com/search.json?engine=google_lens&url=${encodeURIComponent(imageUrl)}&api_key=${process.env.SERPAPI_API_KEY}`;
            const serpResponse = await fetch(serpUrl);
            const serpData = await serpResponse.json();
            
            // Extract the top 3 matches and log ONLY those
            if (serpData.visual_matches && serpData.visual_matches.length > 0) {
                const topThreeMatches = serpData.visual_matches.slice(0, 3);
                
                console.log("🕵️‍♂️ [STEP 4] TOP 3 SERPAPI MATCHES:");
                topThreeMatches.forEach((match: any, index: number) => {
                    console.log(`   ${index + 1}. ${match.title} (${match.link})`);
                });

                visualMatchesText = topThreeMatches
                    .map((match: any) => match.title)
                    .join(" | ");
            } else {
                console.log("🕵️‍♂️ [STEP 4] No SerpApi matches found.");
                visualMatchesText = "No previous matches found on the internet. This image might be unique or new.";
            }
        } catch (e) {
            console.error("SerpApi search failed", e);
        }
    }

    // 5. Pass everything to Gemini 2.5 Flash for the final verification
    // 👉 UPDATED: Passed accountName and accountLink down to the AI
    const finalResult = await analyzeWithGemini(accountName, accountLink, caption, articleText, visualMatchesText, cleanBase64);

    console.log("🧠 [STEP 5] Final Gemini AI JSON Output:\n", finalResult);

    // 6. Return the parsed JSON back to the Chrome Extension
    return NextResponse.json(JSON.parse(finalResult));

  } catch (error) {
    console.error("API Error:", error);
    return NextResponse.json({ 
        status: "Error", 
        confidenceScore: 0, 
        reasoning: "The backend server encountered an error processing this request." 
    }, { status: 500 });
  }
}

// Helper Function: The Gemini AI Logic
// 👉 UPDATED: Accepts the new account parameters
async function analyzeWithGemini(accountName: string, accountLink: string, userCaption: string, articleText: string, reverseImageResults: string, imageBase64: string): Promise<string> {
  
  // 👉 UPDATED PROMPT: Included Publisher context into the AI's instructions
  const promptText = `
    You are an expert digital forensics AI participating in a fact-checking hackathon. 
    Your task is to analyze social media posts for Contextual Consistency (Axis 2).
    
    You have been provided with an image (a screenshot of the media in question).
    
    Here is the surrounding context:
    1. POST PUBLISHER: "${accountName}" (Profile URL: ${accountLink})
    2. USER'S CAPTION (Claim): "${userCaption}"
    3. LINKED ARTICLE CONTENT (If the caption had a link): "${articleText}"
    4. REVERSE IMAGE SEARCH HISTORY (Where this exact image has appeared on the internet before): "${reverseImageResults}"
    
    Task: 
    Compare the actual visual contents of the image and its Reverse Image Search history against the Publisher, Caption, and linked article. 
    Is the caption accurately describing the image, or is this image taken out of context (e.g., an old image used for a new event, or a different location)? Consider the publisher's identity if it helps determine context.
    
    You MUST respond with a valid JSON object in this exact format, and nothing else:
    {
      "status": "Verified" | "Suspicious",
      "confidenceScore": <a number between 0 and 100 representing how confident you are in your status>,
      "reasoning": "<A brief, 2-to-3 sentence explanation of why you made this decision. Reference the visual clues and the reverse image search history to explain your logic to the user.>"
    }
  `;

  const result = await ai.models.generateContent({
    model: 'gemini-2.5-flash',
    contents: [
      {
        role: 'user',
        parts: [
          { text: promptText },
          {
            inlineData: {
              data: imageBase64, 
              mimeType: 'image/jpeg'
            }
          }
        ]
      }
    ],
    config: {
      responseMimeType: "application/json",
      responseJsonSchema: {
        type: Type.OBJECT,
        properties: {
          status: {
            type: Type.STRING,
            description: 'Either "Verified" or "Suspicious"',
            enum: ['Verified', 'Suspicious']
          },
          confidenceScore: {
            type: Type.NUMBER,
            description: 'A number between 0 and 100 representing confidence level'
          },
          reasoning: {
            type: Type.STRING,
            description: 'A brief 2-3 sentence explanation of the decision'
          }
        },
        required: ['status', 'confidenceScore', 'reasoning'],
        propertyOrdering: ['status', 'confidenceScore', 'reasoning']
      }
    }
  });

  const responseText = result.text?.trim();
  
  if (!responseText) {
    console.error("Gemini returned empty response");
    return JSON.stringify({
      status: "Suspicious",
      confidenceScore: 0,
      reasoning: "Failed to receive a valid response from the analysis model."
    });
  }

  return responseText;
}