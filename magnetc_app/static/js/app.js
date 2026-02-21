const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const feedbackEl = document.getElementById("feedback");
const resultsSection = document.getElementById("results-section");
const resultsCountEl = document.getElementById("results-count");
const resultsEl = document.getElementById("results");
const searchButton = document.getElementById("search-button");

function escapeHtml(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

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
      const title = escapeHtml(r.title || "Untitled");

      let magnet = r.magnet || "";
      if (magnet && !magnet.startsWith("magnet:")) {
        magnet = "";
      }

      let url = r.url || "#";
      // Basic protocol check
      if (url !== "#" && !/^https?:\/\//i.test(url)) {
        url = "#";
      }

      const qualities = Array.isArray(r.qualities) ? r.qualities.map(escapeHtml) : [];
      const infoText = escapeHtml((r.info_text || "").toString().slice(0, 800));
      const source = escapeHtml(r.source || "Unknown Source");

      const qualityLabel =
        qualities.length > 0 ? qualities.join(", ") : "Unknown quality";

      return `
        <article class="result-card">
          <h3 class="result-title">${title}</h3>
          <div class="result-meta">
            <span class="pill badge-source">${source}</span>
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

// Scanner Logic
const scannerForm = document.getElementById("scanner-form");
const jobsListEl = document.getElementById("jobs-list");
const scanResultsEl = document.getElementById("scan-results-grid");

if (scannerForm) {
  scannerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const site = document.getElementById("scan-site").value;
    const genre = document.getElementById("scan-genre").value;
    const yearFrom = document.getElementById("scan-year-from").value;
    const yearTo = document.getElementById("scan-year-to").value;
    const interval = document.getElementById("scan-interval").value;

    const feedback = document.getElementById("scan-feedback");
    feedback.textContent = "Scheduling scan...";

    try {
      const res = await fetch("/api/scan/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          site,
          interval,
          filters: { genre, year_from: yearFrom, year_to: yearTo }
        })
      });
      const data = await res.json();
      feedback.textContent = `Scan started! ID: ${data.scan_id}`;
      feedback.className = "feedback success";
      loadJobs();
    } catch (err) {
      console.error(err);
      feedback.textContent = "Failed to start scan.";
      feedback.className = "feedback error";
    }
  });
}

async function loadJobs() {
  if (!jobsListEl) return;
  try {
    const res = await fetch("/api/scan/jobs");
    const data = await res.json();
    jobsListEl.innerHTML = data.jobs.map(j => `
      <li>
        <span>#${j.id} ${j.scan_type} (${j.schedule_interval})</span>
        <span class="status-badge status-${j.status}">${j.status}</span>
      </li>
    `).join("");
  } catch (e) { console.error(e); }
}

async function loadScanResults() {
  if (!scanResultsEl) return;
  try {
    const res = await fetch("/api/scan/results?limit=50");
    const data = await res.json();

    // Reuse render logic or similar
    scanResultsEl.innerHTML = data.results.map(r => `
      <article class="result-card">
        <h3 class="result-title">${escapeHtml(r.title)}</h3>
        <div class="result-meta">
          <span class="pill badge-source">${escapeHtml(r.source)}</span>
          <span class="pill">${escapeHtml(r.quality)}</span>
        </div>
        <div class="result-links">
          ${r.magnet ? `<a href="${r.magnet}">Magnet</a>` : ''}
        </div>
      </article>
    `).join("");
  } catch (e) { console.error(e); }
}

// Initial load
if (document.getElementById("tab-scanner")) {
  loadJobs();
  loadScanResults();
  // Poll jobs every 5s
  setInterval(loadJobs, 5000);
}
