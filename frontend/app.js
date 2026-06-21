// Backend API base URL — intentionally EMPTY (relative URLs).
//
// All API calls below use paths like "/auth/login", "/movies/genres", etc.
// Because API_BASE is "", the browser resolves these relative to whatever
// host/port it loaded the page from (e.g. http://13.201.137.187/auth/login).
// Those requests hit nginx on the SAME port the page came from, and nginx's
// reverse-proxy rules (see frontend/nginx.conf) forward them internally to
// the backend container over Docker's private network.
//
// Why this matters: the browser NEVER talks to the backend directly. The
// backend needs no public port, no Security Group rule, and no hardcoded IP.
// The exact same files work on localhost, on any EC2 IP, or behind any
// hostname — with zero configuration.
const API_BASE = "";

let authToken = localStorage.getItem("authToken") || null;
let userEmail = localStorage.getItem("userEmail") || null;
let selectedMovies = []; // [{id, title}]
let selectedGenres = []; // ["Action", ...]
let allGenres = [];

// ---------- DOM refs ----------
const authSection = document.getElementById("auth-section");
const appSection = document.getElementById("app-section");
const userEmailLabel = document.getElementById("user-email");
const logoutBtn = document.getElementById("logout-btn");

const loginPanel = document.getElementById("login-panel");
const signupPanel = document.getElementById("signup-panel");
const tabBtns = document.querySelectorAll(".tab-btn");

const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");
const loginError = document.getElementById("login-error");
const loginBtn = document.getElementById("login-btn");

const signupEmail = document.getElementById("signup-email");
const signupPassword = document.getElementById("signup-password");
const signupError = document.getElementById("signup-error");
const signupBtn = document.getElementById("signup-btn");

const movieSearch = document.getElementById("movie-search");
const selectedMoviesDiv = document.getElementById("selected-movies");
const genreTagsDiv = document.getElementById("genre-tags");
const recommendBtn = document.getElementById("recommend-btn");
const resultsPanel = document.getElementById("results-panel");
const resultsList = document.getElementById("results-list");
const watchlistList = document.getElementById("watchlist-list");

// ---------- Helpers ----------
async function api(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && authToken) headers["Authorization"] = `Bearer ${authToken}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = "Something went wrong";
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

function showApp() {
  authSection.classList.add("hidden");
  appSection.classList.remove("hidden");
  userEmailLabel.textContent = userEmail;
  userEmailLabel.classList.remove("hidden");
  logoutBtn.classList.remove("hidden");
  loadGenres();
  loadWatchlist();
}

function showAuth() {
  authSection.classList.remove("hidden");
  appSection.classList.add("hidden");
  userEmailLabel.classList.add("hidden");
  logoutBtn.classList.add("hidden");
}

// ---------- Tabs ----------
tabBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    tabBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    if (btn.dataset.tab === "login") {
      loginPanel.classList.remove("hidden");
      signupPanel.classList.add("hidden");
    } else {
      signupPanel.classList.remove("hidden");
      loginPanel.classList.add("hidden");
    }
  });
});

// ---------- Auth ----------
loginBtn.addEventListener("click", async () => {
  loginError.textContent = "";
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: { email: loginEmail.value.trim(), password: loginPassword.value },
    });
    authToken = data.access_token;
    userEmail = loginEmail.value.trim();
    localStorage.setItem("authToken", authToken);
    localStorage.setItem("userEmail", userEmail);
    showApp();
  } catch (err) {
    loginError.textContent = err.message;
  }
});

signupBtn.addEventListener("click", async () => {
  signupError.textContent = "";
  const password = signupPassword.value;
  if (password.length < 8) {
    signupError.textContent = "Password must be at least 8 characters long";
    return;
  }
  try {
    await api("/auth/signup", {
      method: "POST",
      body: { email: signupEmail.value.trim(), password },
    });
    // auto-login after signup
    const data = await api("/auth/login", {
      method: "POST",
      body: { email: signupEmail.value.trim(), password },
    });
    authToken = data.access_token;
    userEmail = signupEmail.value.trim();
    localStorage.setItem("authToken", authToken);
    localStorage.setItem("userEmail", userEmail);
    showApp();
  } catch (err) {
    signupError.textContent = err.message;
  }
});

logoutBtn.addEventListener("click", () => {
  authToken = null;
  userEmail = null;
  localStorage.removeItem("authToken");
  localStorage.removeItem("userEmail");
  selectedMovies = [];
  selectedGenres = [];
  showAuth();
});

// ---------- Movie search (selected movies as chips) ----------

// Looks up whatever text is currently in the search box and, if it
// matches a movie, adds it as a selected chip. Returns true if a movie
// was found and added (or already selected), false otherwise.
async function tryAddMovieFromSearchBox({ alertIfNotFound = true } = {}) {
  const query = movieSearch.value.trim();
  if (!query) return false;

  try {
    const matches = await api(`/movies?search=${encodeURIComponent(query)}&limit=1`);
    if (matches.length === 0) {
      if (alertIfNotFound) alert(`No movie found matching "${query}"`);
      return false;
    }
    const movie = matches[0];
    if (!selectedMovies.find((m) => m.id === movie.id)) {
      selectedMovies.push(movie);
      renderSelectedMovies();
    }
    movieSearch.value = "";
    return true;
  } catch (err) {
    alert(err.message);
    return false;
  }
}

movieSearch.addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  await tryAddMovieFromSearchBox();
});

function renderSelectedMovies() {
  selectedMoviesDiv.innerHTML = "";
  selectedMovies.forEach((m) => {
    const tag = document.createElement("span");
    tag.className = "tag selected";
    tag.textContent = `${m.title} ✕`;
    tag.addEventListener("click", () => {
      selectedMovies = selectedMovies.filter((sm) => sm.id !== m.id);
      renderSelectedMovies();
    });
    selectedMoviesDiv.appendChild(tag);
  });
}

// ---------- Genres ----------
async function loadGenres() {
  try {
    allGenres = await api("/movies/genres");
    renderGenreTags();
  } catch (err) {
    console.error(err);
  }
}

function renderGenreTags() {
  genreTagsDiv.innerHTML = "";
  allGenres.forEach((genre) => {
    const tag = document.createElement("span");
    tag.className = "tag" + (selectedGenres.includes(genre) ? " selected" : "");
    tag.textContent = genre;
    tag.addEventListener("click", () => {
      if (selectedGenres.includes(genre)) {
        selectedGenres = selectedGenres.filter((g) => g !== genre);
      } else {
        selectedGenres.push(genre);
      }
      renderGenreTags();
    });
    genreTagsDiv.appendChild(tag);
  });
}

// ---------- Recommendations ----------
recommendBtn.addEventListener("click", async () => {
  // If the person typed a movie but never pressed Enter, try to add it now
  // rather than ignoring it silently.
  if (movieSearch.value.trim()) {
    await tryAddMovieFromSearchBox({ alertIfNotFound: false });
  }

  if (selectedMovies.length === 0 && selectedGenres.length === 0) {
    alert("Pick at least one movie or genre first — type a movie title or tap a genre below.");
    return;
  }
  try {
    const results = await api("/movies/recommend", {
      method: "POST",
      body: {
        movie_titles: selectedMovies.map((m) => m.title),
        genres: selectedGenres,
        top_n: 10,
      },
    });
    renderResults(results);
  } catch (err) {
    alert(err.message);
  }
});

// Returns an <img> if the movie has a poster_url, otherwise a plain
// placeholder box — so the layout stays consistent either way.
function posterHtml(movie) {
  if (movie.poster_url) {
    return `<img src="${movie.poster_url}" alt="${movie.title} poster" class="poster">`;
  }
  return `<div class="poster poster-placeholder">No poster</div>`;
}

function renderResults(movies) {
  resultsPanel.classList.remove("hidden");
  resultsList.innerHTML = "";
  if (movies.length === 0) {
    resultsList.innerHTML = '<span style="color:var(--text-dim)">No recommendations found.</span>';
    return;
  }
  movies.forEach((movie) => {
    const card = document.createElement("div");
    card.className = "movie-card";
    card.innerHTML = `
      ${posterHtml(movie)}
      <div class="movie-info">
        <div class="movie-title">${movie.title}</div>
        <div class="movie-meta">${movie.year || ""} · ${movie.genres || ""}</div>
      </div>
    `;
    const addBtn = document.createElement("button");
    addBtn.className = "small";
    addBtn.textContent = "+ Watchlist";
    addBtn.addEventListener("click", async () => {
      try {
        await api("/watchlist", {
          method: "POST",
          auth: true,
          body: { movie_id: movie.id },
        });
        addBtn.textContent = "Added";
        addBtn.disabled = true;
        loadWatchlist();
      } catch (err) {
        alert(err.message);
      }
    });
    card.appendChild(addBtn);
    resultsList.appendChild(card);
  });
}

// ---------- Watchlist ----------
async function loadWatchlist() {
  try {
    const items = await api("/watchlist", { auth: true });
    renderWatchlist(items);
  } catch (err) {
    watchlistList.innerHTML = `<span style="color:var(--danger)">${err.message}</span>`;
  }
}

function renderWatchlist(items) {
  watchlistList.innerHTML = "";
  if (items.length === 0) {
    watchlistList.innerHTML = '<span style="color:var(--text-dim)">Your watchlist is empty. Get some recommendations above and add a few.</span>';
    return;
  }
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "movie-card";
    card.innerHTML = `
      ${posterHtml(item.movie)}
      <div class="movie-info">
        <div class="movie-title">${item.movie.title}</div>
        <div class="movie-meta">${item.movie.year || ""} · ${item.movie.genres || ""}</div>
      </div>
    `;
    const removeBtn = document.createElement("button");
    removeBtn.className = "secondary small";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", async () => {
      try {
        await api(`/watchlist/${item.id}`, { method: "DELETE", auth: true });
        loadWatchlist();
      } catch (err) {
        alert(err.message);
      }
    });
    card.appendChild(removeBtn);
    watchlistList.appendChild(card);
  });
}

// ---------- Init ----------
if (authToken && userEmail) {
  showApp();
} else {
  showAuth();
}
