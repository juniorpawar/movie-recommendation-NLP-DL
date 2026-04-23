import requests
import streamlit as st

API_BASE = "https://movie-recommendation-nlp-dl.onrender.com/" or "http://127.0.0.1:8000"

st.set_page_config(page_title="CineMatch - Movie Recommender", page_icon="🎬", layout="wide")

# ========= THEME STATE =========
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "view" not in st.session_state:
    st.session_state.view = "home"
if "selected_imdb_id" not in st.session_state:
    st.session_state.selected_imdb_id = None
 
qp_view = st.query_params.get("view")
qp_id = st.query_params.get("id")
if qp_view in ("home", "details", "chatbot"):
    st.session_state.view = qp_view
if qp_id:
    st.session_state.selected_imdb_id = str(qp_id)
    st.session_state.view = "details"

is_dark = st.session_state.theme == "dark"

# ========= CSS DESIGN SYSTEM =========
if is_dark:
    css_vars = """
    --bg-primary: #0a0a1a; --bg-secondary: #12122a; --bg-card: rgba(255,255,255,0.04);
    --bg-card-hover: rgba(255,255,255,0.08); --bg-glass: rgba(18,18,42,0.85);
    --text-primary: #eef0ff; --text-secondary: #8b8fa3; --text-muted: #5a5e73;
    --accent: #6c5ce7; --accent-hover: #7f70f0; --accent-glow: rgba(108,92,231,0.25);
    --gradient-start: #6c5ce7; --gradient-end: #00cec9;
    --border: rgba(255,255,255,0.06); --shadow: rgba(0,0,0,0.4);
    --poster-shadow: 0 8px 32px rgba(0,0,0,0.5); --fab-bg: linear-gradient(135deg,#6c5ce7,#00cec9);
    """
else:
    css_vars = """
    --bg-primary: #f5f6fa; --bg-secondary: #ffffff; --bg-card: rgba(255,255,255,0.9);
    --bg-card-hover: rgba(255,255,255,1); --bg-glass: rgba(255,255,255,0.9);
    --text-primary: #1a1a2e; --text-secondary: #555770; --text-muted: #8b8fa3;
    --accent: #6c5ce7; --accent-hover: #5a4bd1; --accent-glow: rgba(108,92,231,0.15);
    --gradient-start: #6c5ce7; --gradient-end: #00cec9;
    --border: rgba(0,0,0,0.08); --shadow: rgba(0,0,0,0.08);
    --poster-shadow: 0 8px 24px rgba(0,0,0,0.12); --fab-bg: linear-gradient(135deg,#6c5ce7,#00cec9);
    """

st.markdown(f"""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {{ {css_vars} }}
*, .stApp, .block-container, [data-testid="stSidebar"], .stMarkdown, p, span, label,
div, h1, h2, h3, h4, h5 {{ font-family: 'Inter', sans-serif !important; }}
.stApp {{ background: var(--bg-primary) !important; }}
[data-testid="stSidebar"] {{ background: var(--bg-secondary) !important; border-right: 1px solid var(--border) !important; }}
[data-testid="stSidebar"] * {{ color: var(--text-primary) !important; }}
.block-container {{ padding-top: 1rem !important; max-width: 1400px !important; }}
h1,h2,h3,h4 {{ color: var(--text-primary) !important; }}
p, li, span, label {{ color: var(--text-secondary) !important; }}
.stTextInput input {{ background: var(--bg-card) !important; color: var(--text-primary) !important;
  border: 1px solid var(--border) !important; border-radius: 12px !important; padding: 12px 16px !important; }}
.stTextInput input:focus {{ border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--accent-glow) !important; }}
.stSelectbox > div > div {{ background: var(--bg-card) !important; color: var(--text-primary) !important;
  border: 1px solid var(--border) !important; border-radius: 12px !important; }}
.stButton > button {{ background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end)) !important;
  color: white !important; border: none !important; border-radius: 10px !important; padding: 8px 20px !important;
  font-weight: 600 !important; transition: all 0.3s ease !important; }}
.stButton > button:hover {{ transform: translateY(-2px) !important;
  box-shadow: 0 6px 20px var(--accent-glow) !important; }}
hr {{ border-color: var(--border) !important; }}
.cm-hero {{ background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
  border-radius: 20px; padding: 48px 40px; margin-bottom: 28px; position: relative; overflow: hidden; }}
.cm-hero::before {{ content: ''; position: absolute; top: -50%; right: -20%; width: 400px; height: 400px;
  background: rgba(255,255,255,0.06); border-radius: 50%; }}
.cm-hero h1 {{ color: #fff !important; font-size: 2.4rem; font-weight: 800; margin: 0 0 8px 0; }}
.cm-hero p {{ color: rgba(255,255,255,0.85) !important; font-size: 1.1rem; margin: 0; }}
.cm-stats {{ display: flex; gap: 16px; margin: 24px 0; flex-wrap: wrap; }}
.cm-stat {{ background: var(--bg-card); backdrop-filter: blur(10px); border: 1px solid var(--border);
  border-radius: 16px; padding: 20px 24px; flex: 1; min-width: 180px; text-align: center;
  transition: all 0.3s ease; }}
.cm-stat:hover {{ transform: translateY(-4px); box-shadow: 0 12px 32px var(--shadow); }}
.cm-stat i {{ font-size: 1.5rem; background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; display: block; }}
.cm-stat .val {{ font-size: 1.4rem; font-weight: 700; color: var(--text-primary); }}
.cm-stat .lbl {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }}
.cm-section {{ color: var(--text-primary); font-size: 1.2rem; font-weight: 700; margin: 28px 0 16px 0;
  display: flex; align-items: center; gap: 10px; }}
.cm-section i {{ background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.cm-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px;
  padding: 10px; transition: all 0.3s ease; overflow: hidden; }}
.cm-card:hover {{ background: var(--bg-card-hover); transform: translateY(-4px);
  box-shadow: 0 12px 32px var(--shadow); border-color: var(--accent); }}
.cm-card img {{ border-radius: 12px; width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
.cm-card-title {{ font-size: 0.85rem; font-weight: 600; color: var(--text-primary); line-height: 1.2;
  height: 2.1rem; overflow: hidden; margin-top: 8px; padding: 0 4px; }}
.cm-no-poster {{ border-radius: 12px; width: 100%; aspect-ratio: 2/3; background: var(--bg-secondary);
  display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 2rem; }}
.cm-detail-card {{ background: var(--bg-card); backdrop-filter: blur(10px); border: 1px solid var(--border);
  border-radius: 20px; padding: 28px; }}
.cm-detail-card h2 {{ margin: 0 0 12px 0; font-size: 1.8rem; }}
.cm-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
.cm-tag {{ background: var(--accent-glow); color: var(--accent); border-radius: 20px;
  padding: 4px 14px; font-size: 0.78rem; font-weight: 600; display: inline-block; }}
.cm-info-row {{ color: var(--text-secondary); font-size: 0.9rem; margin: 6px 0; display: flex;
  align-items: center; gap: 8px; }}
.cm-info-row i {{ color: var(--accent); width: 16px; text-align: center; }}
.cm-fab {{ position: fixed; bottom: 28px; left: 28px; width: 56px; height: 56px; border-radius: 50%;
  background: var(--fab-bg); display: flex; align-items: center; justify-content: center;
  color: white; font-size: 1.4rem; box-shadow: 0 8px 28px var(--accent-glow); cursor: pointer;
  z-index: 9999; text-decoration: none; transition: all 0.3s ease; }}
.cm-fab:hover {{ transform: scale(1.12); box-shadow: 0 12px 36px var(--accent-glow); }}
.cm-chatbot-page {{ text-align: center; padding: 80px 20px; }}
.cm-chatbot-page i {{ font-size: 4rem; background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 24px; display: block; }}
.cm-chatbot-page h2 {{ color: var(--text-primary); }}
.cm-chatbot-page p {{ color: var(--text-secondary); max-width: 400px; margin: 0 auto; }}
.cm-brand {{ font-size: 1.3rem; font-weight: 800; background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 20px; display: block; }}
.cm-sidebar-link {{ display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 10px;
  color: var(--text-secondary) !important; text-decoration: none; transition: all 0.2s ease;
  font-weight: 500; font-size: 0.95rem; cursor: pointer; margin: 2px 0; }}
.cm-sidebar-link:hover {{ background: var(--accent-glow); color: var(--accent) !important; }}
.cm-sidebar-link.active {{ background: var(--accent-glow); color: var(--accent) !important; font-weight: 600; }}
.cm-sidebar-link i {{ width: 20px; text-align: center; }}
.cm-divider {{ border: none; border-top: 1px solid var(--border); margin: 16px 0; }}
</style>
""", unsafe_allow_html=True)

# ========= FLOATING CHATBOT FAB =========
st.markdown('<a href="?view=chatbot" target="_self" class="cm-fab"><i class="fas fa-robot"></i></a>', unsafe_allow_html=True)

# ========= NAVIGATION HELPERS =========
def goto_home():
    st.session_state.view = "home"
    st.query_params["view"] = "home"
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()

def goto_details(imdb_id: str):
    st.session_state.view = "details"
    st.session_state.selected_imdb_id = str(imdb_id)
    st.query_params["view"] = "details"
    st.query_params["id"] = str(imdb_id)
    st.rerun()

# ========= API HELPERS (UNCHANGED LOGIC) =========
@st.cache_data(ttl=30)
def api_get_json(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=25)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"

def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("No movies to show.")
        return
    rows = (len(cards) + cols - 1) // cols
    idx = 0
    for r in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break
            m = cards[idx]
            idx += 1
            imdb_id = m.get("imdb_id")
            title = m.get("title", "Untitled")
            poster = m.get("poster_url")
            with colset[c]:
                if poster:
                    st.markdown(f'<div class="cm-card"><img src="{poster}" alt="{title}"><div class="cm-card-title">{title}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="cm-card"><div class="cm-no-poster"><i class="fas fa-film"></i></div><div class="cm-card-title">{title}</div></div>', unsafe_allow_html=True)
                if st.button("View", key=f"{key_prefix}_{r}_{c}_{idx}_{imdb_id}"):
                    if imdb_id:
                        goto_details(imdb_id)

def to_cards_from_tfidf_items(tfidf_items):
    cards = []
    for x in tfidf_items or []:
        movie = x.get("movie") or {}
        if movie.get("imdb_id"):
            cards.append({"imdb_id": movie["imdb_id"], "title": movie.get("title") or x.get("title") or "Untitled", "poster_url": movie.get("poster_url")})
    return cards

def parse_omdb_search_to_cards(data, keyword: str, limit: int = 24):
    keyword_l = keyword.strip().lower()
    if isinstance(data, dict) and "Search" in data:
        raw_items = []
        for m in data.get("Search") or []:
            title = (m.get("Title") or "").strip()
            imdb_id = m.get("imdbID")
            poster = m.get("Poster")
            if not title or not imdb_id:
                continue
            raw_items.append({"imdb_id": imdb_id, "title": title, "poster_url": poster if poster and poster != "N/A" else None, "year": m.get("Year", "")})
    elif isinstance(data, list):
        raw_items = []
        for m in data:
            imdb_id = m.get("imdb_id") or m.get("imdbID")
            title = (m.get("title") or m.get("Title") or "").strip()
            poster_url = m.get("poster_url") or m.get("Poster")
            if poster_url == "N/A":
                poster_url = None
            if not title or not imdb_id:
                continue
            raw_items.append({"imdb_id": imdb_id, "title": title, "poster_url": poster_url, "year": m.get("year") or m.get("Year", "")})
    else:
        return [], []
    matched = [x for x in raw_items if keyword_l in x["title"].lower()]
    final_list = matched if matched else raw_items
    suggestions = []
    for x in final_list[:10]:
        year = str(x.get("year") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["imdb_id"]))
    cards = [{"imdb_id": x["imdb_id"], "title": x["title"], "poster_url": x["poster_url"]} for x in final_list[:limit]]
    return suggestions, cards

# ========= SIDEBAR =========
with st.sidebar:
    st.markdown('<span class="cm-brand"><i class="fa-solid fa-clapperboard"></i> CineMatch</span>', unsafe_allow_html=True)

    # Theme toggle
    theme_icon = "fa-sun" if is_dark else "fa-moon"
    theme_label = "Light Mode" if is_dark else "Dark Mode"
    if st.button(f"{'☀️' if is_dark else '🌙'}  {theme_label}", key="theme_toggle", use_container_width=True):
        st.session_state.theme = "light" if is_dark else "dark"
        st.rerun()

    st.markdown('<hr class="cm-divider">', unsafe_allow_html=True)

    if st.button("🏠  Home", key="nav_home", use_container_width=True):
        goto_home()

    st.markdown('<hr class="cm-divider">', unsafe_allow_html=True)
    st.markdown(f'<div style="color:var(--text-muted);font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;padding:0 14px;margin-bottom:8px;">Browse</div>', unsafe_allow_html=True)

    home_category = st.selectbox("Category", ["trending", "popular", "top_rated", "now_playing", "upcoming"], index=0, label_visibility="collapsed")
    grid_cols = st.slider("Grid columns", 4, 8, 6)

# ========= VIEW: CHATBOT (COMING SOON) =========
if st.session_state.view == "chatbot":
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Back to Home", key="chat_back"):
            goto_home()
    st.markdown("""
    <div class="cm-chatbot-page">
        <i class="fas fa-robot"></i>
        <h2>AI Assistant</h2>
        <p>Our intelligent movie recommendation chatbot is currently under development. Stay tuned for personalized conversations about your favorite films!</p>
        <div style="margin-top:32px;">
            <div class="cm-tag" style="font-size:0.9rem;padding:8px 20px;">Coming Soon</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ========= VIEW: HOME =========
if st.session_state.view == "home":
    # Hero
    st.markdown("""
    <div class="cm-hero">
        <h1><i class="fas fa-clapperboard"></i> CineMatch</h1>
        <p>Discover your next favorite movie with AI-powered recommendations</p>
    </div>
    """, unsafe_allow_html=True)

    # Stats bar
    st.markdown("""
    <div class="cm-stats">
        <div class="cm-stat"><div class="val">45,000+</div><div class="lbl">Movies in Database</div></div>
        <div class="cm-stat"><div class="val">TF-IDF</div><div class="lbl">AI Engine</div></div>
        <div class="cm-stat"><div class="val">20+</div><div class="lbl">Genre Categories</div></div>
        <div class="cm-stat"><div class="val">Instant</div><div class="lbl">Recommendations</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Search
    st.markdown('<div class="cm-section"><i class="fas fa-magnifying-glass"></i> Search Movies</div>', unsafe_allow_html=True)
    typed = st.text_input("Search", placeholder="Search for any movie... e.g. Inception, Batman, Titanic", label_visibility="collapsed")
    st.divider()

    if typed.strip():
        if len(typed.strip()) < 2:
            st.caption("Type at least 2 characters for suggestions.")
        else:
            data, err = api_get_json("/search", params={"query": typed.strip()})
            if err or data is None:
                st.error(f"Search failed: {err}")
            else:
                suggestions, cards = parse_omdb_search_to_cards(data, typed.strip(), limit=24)
                if suggestions:
                    labels = ["-- Select a movie --"] + [s[0] for s in suggestions]
                    selected = st.selectbox("Suggestions", labels, index=0)
                    if selected != "-- Select a movie --":
                        label_to_id = {s[0]: s[1] for s in suggestions}
                        goto_details(label_to_id[selected])
                else:
                    st.info("No suggestions found. Try another keyword.")
                st.markdown('<div class="cm-section"><i class="fas fa-grid"></i> Results</div>', unsafe_allow_html=True)
                poster_grid(cards, cols=grid_cols, key_prefix="search_results")
        st.stop()

    # Home feed
    cat_icons = {"trending": "fa-fire", "popular": "fa-star", "top_rated": "fa-trophy", "now_playing": "fa-play-circle", "upcoming": "fa-clock"}
    cat_icon = cat_icons.get(home_category, "fa-film")
    cat_display = home_category.replace("_", " ").title()
    st.markdown(f'<div class="cm-section"><i class="fas {cat_icon}"></i> {cat_display}</div>', unsafe_allow_html=True)

    home_cards, err = api_get_json("/home", params={"category": home_category, "limit": 24})
    if err or not home_cards:
        st.error(f"Home feed failed: {err or 'Unknown error'}")
        st.stop()
    poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")

# ========= VIEW: DETAILS =========
elif st.session_state.view == "details":
    imdb_id = st.session_state.selected_imdb_id
    if not imdb_id:
        st.warning("No movie selected.")
        if st.button("Back to Home"):
            goto_home()
        st.stop()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="cm-section"><i class="fas fa-circle-info"></i> Movie Details</div>', unsafe_allow_html=True)
    with col2:
        if st.button("Back to Home", key="detail_back"):
            goto_home()

    data, err = api_get_json(f"/movie/id/{imdb_id}")
    if err or not data:
        st.error(f"Could not load details: {err or 'Unknown error'}")
        st.stop()

    left, right = st.columns([1, 2.4], gap="large")
    with left:
        if data.get("poster_url"):
            st.markdown(f'<div class="cm-card"><img src="{data["poster_url"]}" style="border-radius:12px;width:100%;"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="cm-card"><div class="cm-no-poster" style="height:400px;"><i class="fas fa-film"></i></div></div>', unsafe_allow_html=True)

    with right:
        genres = data.get("genres", [])
        genre_tags = "".join([f'<span class="cm-tag">{g}</span>' for g in genres]) if genres else '<span class="cm-tag">N/A</span>'
        rating = data.get("imdb_rating") or "N/A"
        year = data.get("year") or "N/A"
        runtime = data.get("runtime") or "N/A"
        director = data.get("director") or "N/A"
        actors = data.get("actors") or "N/A"
        rated = data.get("rated") or "N/A"
        plot = data.get("plot") or "No overview available."

        st.markdown(f"""
        <div class="cm-detail-card">
            <h2>{data.get("title","")}</h2>
            <div class="cm-meta">{genre_tags}</div>
            <div class="cm-info-row"><i class="fas fa-star"></i> <strong>{rating}</strong>/10 IMDb</div>
            <div class="cm-info-row"><i class="fas fa-calendar"></i> {year} &nbsp;&bull;&nbsp; {runtime} &nbsp;&bull;&nbsp; {rated}</div>
            <div class="cm-info-row"><i class="fas fa-video"></i> {director}</div>
            <div class="cm-info-row"><i class="fas fa-users"></i> {actors}</div>
            <hr class="cm-divider">
            <div style="color:var(--text-secondary);font-size:0.95rem;line-height:1.6;">{plot}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="cm-section"><i class="fas fa-wand-magic-sparkles"></i> Recommendations</div>', unsafe_allow_html=True)

    title = (data.get("title") or "").strip()
    if title:
        bundle, err2 = api_get_json("/movie/search", params={"query": title, "tfidf_top_n": 12, "genre_limit": 12})
        if not err2 and bundle:
            st.markdown('<div class="cm-section"><i class="fas fa-brain"></i> Similar Movies (AI)</div>', unsafe_allow_html=True)
            poster_grid(to_cards_from_tfidf_items(bundle.get("tfidf_recommendations")), cols=grid_cols, key_prefix="details_tfidf")
            st.markdown('<div class="cm-section"><i class="fas fa-masks-theater"></i> More Like This</div>', unsafe_allow_html=True)
            poster_grid(bundle.get("genre_recommendations", []), cols=grid_cols, key_prefix="details_genre")
        else:
            st.info("Showing Genre recommendations (fallback).")
            genre_only, err3 = api_get_json("/recommend/genre", params={"imdb_id": imdb_id, "limit": 18})
            if not err3 and genre_only:
                poster_grid(genre_only, cols=grid_cols, key_prefix="details_genre_fallback")
            else:
                st.warning("No recommendations available right now.")
    else:
        st.warning("No title available to compute recommendations.")
