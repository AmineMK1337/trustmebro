// Function to inject our custom UI into posts
function injectTrustUI() {
  // 1. Target the posts.
  // We added 'div[data-pagelet^="FeedUnit"]' to catch Facebook main feeds better.
  const rawPosts = document.querySelectorAll(
    'article, div[role="article"], div[data-pagelet^="FeedUnit"]',
  );

  rawPosts.forEach((post, index) => {
    // --- FACEBOOK COMMENT EXCEPTION ---
    // If the element is a Facebook 'article', check if it is nested inside another 'article' or feed unit.
    // If it has a parent that is also a post, that means it's a comment! We skip it.
    if (
      post.tagName.toLowerCase() === "div" &&
      post.getAttribute("role") === "article"
    ) {
      let parent = post.parentElement;
      let isComment = false;

      while (parent) {
        if (
          parent.getAttribute("role") === "article" ||
          (parent.getAttribute("data-pagelet") &&
            parent.getAttribute("data-pagelet").startsWith("FeedUnit"))
        ) {
          isComment = true;
          break;
        }
        parent = parent.parentElement;
      }

      if (isComment) return; // Stop processing this element, it's a comment!
    }
    // ----------------------------------

    // Prevent duplicate injections on the same post
    if (post.classList.contains("trust-post-wrapper")) return;
    post.classList.add("trust-post-wrapper");

    // 2. Create the IDM-style "Verify" Button
    const verifyBtn = document.createElement("button");
    verifyBtn.className = "trust-verify-btn";
    verifyBtn.innerHTML = "🔍 Verify";

    verifyBtn.onclick = async (e) => {
      e.preventDefault();
      e.stopPropagation();

      verifyBtn.innerHTML = "⏳ Scraping & Analyzing...";

      // --- 1. SCRAPE THE POST DATA ---
      const postText = post.innerText || "";

      // Scrape Images
      const imageNodes = post.querySelectorAll("img");
      const imageUrls = [];
      imageNodes.forEach((img) => {
        if (img.src && !img.src.includes("emoji") && img.clientWidth > 100) {
          imageUrls.push(img.src);
        }
      });

      // Scrape Videos
      // --- Scrape Videos (AGGRESSIVE MODE) ---
      const videoNodes = post.querySelectorAll("video");
      const videoUrls = [];

      videoNodes.forEach((vid) => {
        // Check currentSrc first (where modern browsers hide the real stream), then src, then <source> tags
        const src =
          vid.currentSrc ||
          vid.src ||
          (vid.querySelector("source") && vid.querySelector("source").src);
        if (src) {
          videoUrls.push(src);
        }
      });

      // --- Find Specific Post URL ---
      let specificPostUrl = window.location.href; // Fallback to current page

      // X/Twitter trick: Timestamps are links that contain "/status/"
      const twitterLinks = post.querySelectorAll('a[href*="/status/"]');
      if (twitterLinks.length > 0) {
        specificPostUrl = twitterLinks[0].href;
      }
      // Facebook trick: Look for links with /posts/ or /videos/
      else {
        const fbLinks = post.querySelectorAll(
          'a[href*="/posts/"], a[href*="/videos/"]',
        );
        if (fbLinks.length > 0) {
          specificPostUrl = fbLinks[0].href;
        }
      }

      // Package it up for the backend
      const payload = {
        postId: Math.random().toString(36).substring(7),
        contextUrl: specificPostUrl, // <-- NOW SENDS THE SPECIFIC URL!
        text: postText,
        imageUrls: imageUrls,
        videoUrls: videoUrls,
        timestamp: new Date().toISOString(),
      };

      // --- 2. SEND TO PYTHON BACKEND ---
      try {
        const response = await fetch("http://127.0.0.1:5000/verify", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const result = await response.json();

        // --- 3. UPDATE UI BASED ON BACKEND RESPONSE ---
        // This perfectly matches the Hackathon PDF requirements (Status, Score, Reasoning)
        if (result.status === "Verified") {
          verifyBtn.innerHTML = `✅ Verified (${result.score}%)`;
          verifyBtn.style.backgroundColor = "#1e8e3e"; // Green
        } else {
          verifyBtn.innerHTML = `⚠️ Suspicious (${result.score}%)`;
          verifyBtn.style.backgroundColor = "#d93025"; // Red
        }

        // Add a hover tooltip with the AI's reasoning
        verifyBtn.title = result.reasoning;
      } catch (error) {
        console.error("Backend connection failed:", error);
        verifyBtn.innerHTML = "❌ Server Error";
        verifyBtn.style.backgroundColor = "#555";
      }
    };
    post.appendChild(verifyBtn);

    // 3. Simulate Checking the Database for existing evaluations
    // For the demo, let's randomly mock that 1 in 4 posts are already in your DB
    const isAlreadyEvaluated = index % 4 === 0;

    if (isAlreadyEvaluated) {
      // Generate a random mock score between 10 and 99
      const score = Math.floor(Math.random() * 90) + 10;

      const badge = document.createElement("div");
      badge.className = `trust-score-badge ${score > 50 ? "trust-score-high" : "trust-score-low"}`;
      badge.innerText = score;
      badge.title =
        score > 50
          ? "Previously verified as mostly authentic"
          : "Warning: Flagged as suspicious";

      post.appendChild(badge);
    }
  });
}

// Run the injection once when the page first loads
injectTrustUI();

// 4. Handle Infinite Scrolling (MutationObserver)
// This watches the DOM for changes so when new posts load, they get the UI too
const observer = new MutationObserver((mutations) => {
  // Debounce or call directly depending on performance needs
  injectTrustUI();
});

observer.observe(document.body, {
  childList: true,
  subtree: true,
});
