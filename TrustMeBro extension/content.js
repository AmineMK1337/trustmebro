// Function to inject our custom UI into posts
function injectTrustUI() {
  // 1. Target the posts.
  // 'article' works for Twitter. 'div[role="article"]' works for Facebook.
  const posts = document.querySelectorAll('article, div[role="article"]');

  posts.forEach((post, index) => {
    // Prevent duplicate injections on the same post
    if (post.classList.contains("trust-post-wrapper")) return;
    post.classList.add("trust-post-wrapper");

    // 2. Create the IDM-style "Verify" Button
    const verifyBtn = document.createElement("button");
    verifyBtn.className = "trust-verify-btn";
    verifyBtn.innerHTML = "🔍 Verify";

    verifyBtn.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation(); // Stop clicking the post behind the button

      verifyBtn.innerHTML = "⏳ Analyzing...";

      // TODO: Here you will grab the post's text/image and send to your backend
      // For now, we simulate an API call taking 1.5 seconds
      setTimeout(() => {
        verifyBtn.innerHTML = "✅ Verified";
        verifyBtn.style.backgroundColor = "#1e8e3e";
      }, 1500);
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
