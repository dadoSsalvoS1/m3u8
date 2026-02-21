const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const feedbackEl = document.getElementById("feedback");
const resultsSection = document.getElementById("results-section");
const resultsCountEl = document.getElementById("results-count");
const resultsEl = document.getElementById("results");
const searchButton = document.getElementById("search-button");

function setLoading(isLoading) {
  if (!searchButton) return;
  if (isLoading) {
    searchButton.classList.add("loading");
    searchButton.setAttribute("disabled", "true");
  } else {
    searchButton.classList.remove("loading");
    searchButton.removeAttribute("disabled");
  }
}

function setFeedback(message, type = "") {
  if (!feedbackEl) return;
  feedbackEl.textContent = message || "";
  feedbackEl.className = "feedback";
  if (type) {
    feedbackEl.classList.add(type);
  }
}

function renderResults(results) {
  if (!resultsEl || !resultsSection || !resultsCountEl) return;

  if (!results || results.length === 0) {
    resultsSection.classList.add("hidden");
    resultsEl.innerHTML = "";
    resultsCountEl.textContent = "";
    return;
  }

  resultsSection.classList.remove("hidden");
  resultsCountEl.textContent = `${results.length} magnet link(s) found`;

  const html = results
    .map((r) => {
      const title = r.title || "Untitled";
      const magnet = r.magnet || "";
      const url = r.url || "#";
      const qualities = Array.isArray(r.qualities) ? r.qualities : [];
      const infoText = (r.info_text || "").toString().slice(0, 800);

      const qualityLabel =
        qualities.length > 0 ? qualities.join(", ") : "Unknown quality";

      return `
        <article class="result-card">
          <h3 class="result-title">${title}</h3>
          <div class="result-meta">
            <span class="pill">${qualityLabel}</span>
            <span class="pill badge-muted">Magnet link</span>
          </div>
          <div class="result-links">
            ${
              magnet
                ? `<a href="${magnet}">Open magnet</a>`
                : `<span>No magnet link</span>`
            }
            <a href="${url}" target="_blank" rel="noreferrer">Open source page</a>
          </div>
          <div class="result-info">
            <code>${infoText}</code>
          </div>
        </article>
      `;
    })
    .join("");

  resultsEl.innerHTML = html;
}

async function handleSearch(event) {
  event.preventDefault();

  const query = (queryInput?.value || "").trim();
  if (!query) {
    setFeedback("Please enter a movie name before searching.", "error");
    return;
  }

  setLoading(true);
  setFeedback("Searching...", "success");
  resultsEl.innerHTML = "";
  resultsSection.classList.add("hidden");
  resultsCountEl.textContent = "";

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });

    const data = await response.json();
    if (!response.ok) {
      const message = data.error || "Unexpected error while searching.";
      setFeedback(message, "error");
      return;
    }

    if (!data.results || data.results.length === 0) {
      setFeedback("No results found for this query.", "success");
      renderResults([]);
      return;
    }

    setFeedback("", "");
    renderResults(data.results);
  } catch (error) {
    console.error(error);
    setFeedback("Network error, please try again.", "error");
  } finally {
    setLoading(false);
  }
}

if (form) {
  form.addEventListener("submit", handleSearch);
}
