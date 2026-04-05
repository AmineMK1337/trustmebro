// --- 0. UTILITY HELPERS ---

/**
 * Converts relative time strings (e.g., "2m", "3h", "2d") to an ISO date string
 * @param {string} relativeTime - e.g., "2m", "3h", "2d", "1w"
 * @returns {string} ISO 8601 date string
 */
function calculatePostDate(relativeTime) {
  const now = new Date();
  const match = relativeTime.match(/(\d+)\s*(s|m|h|d|w|mo|y)/i);
  
  if (!match) return now.toISOString(); // Fallback to now if can't parse
  
  const value = parseInt(match[1]);
  const unit = match[2].toLowerCase();
  
  const date = new Date(now);
  
  switch(unit) {
    case 's': date.setSeconds(date.getSeconds() - value); break;
    case 'm': date.setMinutes(date.getMinutes() - value); break;
    case 'h': date.setHours(date.getHours() - value); break;
    case 'd': date.setDate(date.getDate() - value); break;
    case 'w': date.setDate(date.getDate() - (value * 7)); break;
    case 'mo': date.setMonth(date.getMonth() - value); break;
    case 'y': date.setFullYear(date.getFullYear() - value); break;
  }
  
  return date.toISOString();
}

// --- 1. THE ROUTER ---
async function extractPostData(post) {
  const host = window.location.hostname;

  if (host.includes("x.com") || host.includes("twitter.com")) {
    console.log("🌐 Routing to: TWITTER / X Scraper");
    return await scrapeTwitter(post);
  } else if (host.includes("facebook.com")) {
    console.log("🌐 Routing to: FACEBOOK Scraper");
    return await scrapeFacebook(post);
  } else if (host.includes("instagram.com")) {
    console.log("🌐 Routing to: INSTAGRAM Scraper");
    return await scrapeInstagram(post);
  } else {
    console.log("🌐 Routing to: GENERIC Scraper (Unknown site)");
    return await scrapeGeneric(post);
  }
}

// --- 2. PLATFORM SPECIFIC SCRAPERS ---

// 🐦 TWITTER / X (Upgraded with specific URL hunting)
// 🐦 TWITTER / X (Upgraded with Bulletproof Timestamp Hunting)
async function scrapeTwitter(post) {
  let accountName = "Unknown";
  let accountLink = "";
  let caption = "";
  // Ensure we ALWAYS have a fallback
  let postUrl = window.location.href; 

  // 👉 THE FIX: Twitter always wraps the post's timestamp in the exact post URL!
  const timeElement = post.querySelector('time');
  if (timeElement) {
    const timeLink = timeElement.closest('a');
    if (timeLink && timeLink.href) {
      postUrl = timeLink.href;
      console.log("🎯 [SCRAPER] Found exact Twitter status URL via timestamp:", postUrl);
    }
  }

  // Grab the username
  const nameNode = post.querySelector('[data-testid="User-Name"]');
  if (nameNode) {
    accountName = nameNode.innerText.split('\n').join(' ');
    const linkNode = nameNode.querySelector('a');
    if (linkNode) accountLink = linkNode.href;
  }

  // Grab the caption text
  const textNode = post.querySelector('[data-testid="tweetText"]');
  if (textNode) caption = textNode.innerText;

  // Extract the media
  const mediaInfo = await extractMedia(post, postUrl);
  
  return { 
      accountName, 
      accountLink, 
      caption, 
      mediaBase64: mediaInfo.base64, 
      mediaType: mediaInfo.type, 
      postUrl 
  };
}
// 📘 FACEBOOK
async function scrapeFacebook(post) {
  let accountName = "Unknown";
  let accountLink = "";
  let postUrl = window.location.href;
  
  const nameNode = post.querySelector('h3, h4, strong');
  if (nameNode) {
    accountName = nameNode.innerText;
    const linkNode = nameNode.closest('a') || post.querySelector('a');
    if (linkNode) accountLink = linkNode.href;
  }

  let caption = post.innerText.replace(accountName, '').trim();

  const mediaInfo = await extractMedia(post, postUrl);
  return { accountName, accountLink, caption, mediaBase64: mediaInfo.base64, mediaType: mediaInfo.type, postUrl };
}

// 📸 INSTAGRAM (Aggressive URL Hunter)
// 📸 INSTAGRAM (Aggressive URL Hunter + Post Date Extraction)
async function scrapeInstagram(post) {
  let accountName = "Unknown";
  let accountLink = "";
  let postUrl = ""; 

  // 1. Hunt for the Post URL (The Aggressive Method)
  const allLinks = Array.from(post.querySelectorAll('a'));
  
  // Find the first link that points to a specific post or reel
  const actualPostLink = allLinks.find(link => link.href.includes('/p/') || link.href.includes('/reel/'));
  
  if (actualPostLink) {
      postUrl = actualPostLink.href;
      console.log("🎯 [SCRAPER] Found exact post URL inside the DOM:", postUrl);
  } else {
      // Fallback: If we can't find it in the DOM, grab the main browser bar URL
      postUrl = window.location.href;
      console.log("⚠️ [SCRAPER] Couldn't find exact link, falling back to window URL:", postUrl);
  }

  // 2. Hunt for Account Name & Link
  for (const link of allLinks) {
    const text = link.innerText.trim();
    if (text && text.length > 0 && !text.includes(' likes') && !text.includes(' comments')) {
      accountName = text;
      accountLink = link.href;
      break; 
    }
  }

  // 👉 THE FIX: Bulletproof Post URL Extractor
  const postLinks = post.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
  if (postLinks.length > 0) {
      postUrl = postLinks[0].href;
  } else if (window.location.href.includes('/p/') || window.location.href.includes('/reel/')) {
      postUrl = window.location.href;
  }

  if (accountName === "Unknown") {
    const spanInsideLink = post.querySelector('a span');
    if (spanInsideLink) {
      accountName = spanInsideLink.innerText.trim();
      const parentLink = spanInsideLink.closest('a');
      if (parentLink) accountLink = parentLink.href;
    }
  }

  const clickableElements = Array.from(post.querySelectorAll('span, div[role="button"]'));
  const moreBtn = clickableElements.find(el => el.innerText.trim().toLowerCase() === 'more' || el.innerText.trim() === '...');
  
  if (moreBtn) {
    moreBtn.click();
    await new Promise(resolve => setTimeout(resolve, 150));
  }

  let caption = post.innerText || "";
  if (caption) {
      if (accountName !== "Unknown") caption = caption.replace(accountName, '');
      caption = caption.replace("⏳ Analyzing...", "").replace("🔍 Verify", "").trim();
  }

  // 👉 NEW: Extract and calculate post date
  let relativeTime = "0m";
  let calculatedPostDate = new Date().toISOString();
  
  // Try to find time element (Instagram uses various selectors)
  const timeElement = post.querySelector('time, ._ap3a, ._a9zs, [datetime]');
  if (timeElement) {
    const datetimeAttr = timeElement.getAttribute('datetime');
    const innerText = timeElement.innerText.trim();
    
    // Prefer ISO datetime if available (Instagram sometimes provides exact timestamps)
    if (datetimeAttr && !datetimeAttr.startsWith('P')) {
      calculatedPostDate = new Date(datetimeAttr).toISOString();
      relativeTime = "exact";
      console.log(`⏰ [INSTAGRAM] Found exact datetime: ${calculatedPostDate}`);
    } else {
      // Try to parse relative time like "2m", "3h", "2d", "5 minutes", etc.
      const relativeMatch = innerText.match(/(\d+\s*[smhdw])/i) || 
                           innerText.match(/(\d+)\s*(minutes?|hours?|days?|weeks?)/i);
      if (relativeMatch) {
        relativeTime = relativeMatch[0];
        calculatedPostDate = calculatePostDate(relativeTime);
        console.log(`⏰ [INSTAGRAM] Parsed relative time: "${relativeTime}" → ${calculatedPostDate}`);
      } else {
        console.log(`⚠️ [INSTAGRAM] Could not parse time from: "${innerText}"`);
      }
    }
  } else {
    console.log("⚠️ [INSTAGRAM] No time element found, using current time as fallback");
  }

  // 👉 THE FIX: Extracting using the new Object format
  const mediaInfo = await extractMedia(post, postUrl);
  
  // 👉 UPDATED RETURN: Add postDate and relativeTime
  return { 
    accountName, 
    accountLink, 
    caption, 
    mediaBase64: mediaInfo.base64, 
    mediaType: mediaInfo.type, 
    postUrl,
    postDate: calculatedPostDate,  // 👈 NEW: ISO string for backend
    relativeTime: relativeTime      // 👈 NEW: For debugging/logging
  };
}


// 🌐 GENERIC FALLBACK
async function scrapeGeneric(post) {
  const postUrl = window.location.href;
  const mediaInfo = await extractMedia(post, postUrl);
  return {
    accountName: "Unknown Web User",
    accountLink: postUrl,
    caption: post.innerText,
    mediaBase64: mediaInfo.base64,
    mediaType: mediaInfo.type,
    postUrl
  };
}

// --- 3. THE MEDIA EXTRACTOR (Handles Image & Video) ---
// --- 3. THE MEDIA EXTRACTOR (Handles Image & Video) ---
async function extractMedia(post, postUrl = "") {
  let mediaType = "image";
  let base64 = null;

  const video = post.querySelector('video');
  
  // 👉 THE FIX: Broaden the hunt to include Twitter video containers and generic play buttons
  const isTwitterVideo = post.querySelector('[data-testid="videoComponent"], [data-testid="playButton"]');
  const hasPlayIcon = post.querySelector('svg[aria-label="Play"], svg[aria-label="Clip"], [class*="play"], [class*="Play"]');
  
  // If ANY of these markers exist, it's a video. Also check if the URL itself implies a video.
  if (video || isTwitterVideo || hasPlayIcon || postUrl.includes('/reel/') || postUrl.includes('/video/')) {
      mediaType = "video";
      console.log("🎥 Video marker detected! Flagging as video for Python backend...");
  }

  // If a physical video tag is present, try to grab a frame
  if (video) {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 360;
      canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
      base64 = canvas.toDataURL('image/jpeg');
      return { base64, type: mediaType };
    } catch (e) {
      console.error("Video frame capture failed (likely CORS), falling back to thumbnail image...", e);
    }
  }

  // Fallback to finding the poster image/thumbnail
  const img = post.querySelector('img');
  if (img) {
    try {
      const response = await fetch(img.src);
      const blob = await response.blob();
      base64 = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(blob);
      });
    } catch (e) {
      console.error("Image capture failed", e);
    }
  }

  return { base64, type: mediaType };
}

// Function to inject our custom UI into posts
function injectTrustUI() {
  const posts = document.querySelectorAll('article, div[role="article"]');

  posts.forEach((post, index) => {
    if (post.classList.contains("trust-post-wrapper")) return;
    post.classList.add("trust-post-wrapper");

    const verifyBtn = document.createElement("button");
    verifyBtn.className = "trust-verify-btn";
    verifyBtn.innerHTML = "🔍 Verify";

    verifyBtn.onclick = async (e) => {
      e.preventDefault();
      e.stopPropagation();

      verifyBtn.innerHTML = "⏳ Analyzing...";
      verifyBtn.disabled = true;

      try {
        // 👉 THE FIX: Destructuring the NEW variables
        const { accountName, accountLink, caption, mediaBase64, mediaType, postUrl, postDate, relativeTime } = await extractPostData(post);

        console.log("🕵️‍♂️ --- EXTRACTED POST DATA ---");
        console.log("👤 Account Name:", accountName);
        console.log("🔗 Post URL:", postUrl);
        console.log("🎬 Media Type:", mediaType);
        console.log("-----------------------------");

        if (!mediaBase64) {
          alert("TrustMeBro: Could not find an image or video in this post to analyze.");
          verifyBtn.innerHTML = "🔍 Verify";
          verifyBtn.disabled = false;
          return;
        }

        // 👉 THE FIX: Sending `mediaType` and `postUrl` to Python!
        const response = await fetch("http://localhost:3000/api/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ accountName, accountLink, caption, mediaBase64, mediaType, postUrl, postDate, relativeTime })
        });

        const data = await response.json();

        if (data.error) throw new Error(data.error);

        verifyBtn.innerHTML = data.status === "Verified" ? "✅ Verified" : "🔴 Suspicious";
        verifyBtn.style.backgroundColor = data.status === "Verified" ? "#1e8e3e" : "#d93025";
        verifyBtn.style.color = "white";

        const resultsBox = document.createElement("div");
        resultsBox.className = "trust-results-box";
        resultsBox.style.padding = "12px";
        resultsBox.style.marginTop = "10px";
        resultsBox.style.borderRadius = "8px";
        resultsBox.style.backgroundColor = "#f8f9fa";
        resultsBox.style.borderLeft = `4px solid ${data.status === "Verified" ? "#1e8e3e" : "#d93025"}`;
        resultsBox.style.fontFamily = "sans-serif";
        resultsBox.style.fontSize = "14px";
        resultsBox.style.color = "#333";

        resultsBox.innerHTML = `
          <div style="margin-bottom: 6px;">
            <strong>Status:</strong> <span style="color: ${data.status === "Verified" ? "#1e8e3e" : "#d93025"}">${data.status}</span>
          </div>
          <div style="margin-bottom: 6px;">
            <strong>Confidence Score:</strong> ${data.confidenceScore}%
          </div>
          <div style="line-height: 1.4;">
            <strong>Reasoning:</strong> ${data.reasoning}
          </div>
        `;

        post.appendChild(resultsBox);

      } catch (error) {
        console.error("Verification error:", error);
        verifyBtn.innerHTML = "❌ Error";
        verifyBtn.style.backgroundColor = "#5f6368";
        verifyBtn.disabled = false;
      }
    };
    post.appendChild(verifyBtn);
  });
}

injectTrustUI();

const observer = new MutationObserver(() => injectTrustUI());
observer.observe(document.body, { childList: true, subtree: true });