import os
import json
import pickle
import asyncio
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


# =========================
# ENV
# =========================
load_dotenv()
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
OMDB_BASE = "https://www.omdbapi.com/"

if not OMDB_API_KEY:
    raise RuntimeError("OMDB_API_KEY missing. Put it in .env as OMDB_API_KEY=xxxx")


# =========================
# FASTAPI APP
# =========================
app = FastAPI(title="Movie Recommender API", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# PICKLE GLOBALS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DF_PATH = os.path.join(BASE_DIR, "df.pkl")
INDICES_PATH = os.path.join(BASE_DIR, "indices.pkl")
TFIDF_MATRIX_PATH = os.path.join(BASE_DIR, "tfidf_matrix.pkl")
TFIDF_PATH = os.path.join(BASE_DIR, "tfidf.pkl")
CACHE_PATH = os.path.join(BASE_DIR, ".omdb_cache.json")

df: Optional[pd.DataFrame] = None
indices_obj: Any = None
tfidf_matrix: Any = None
tfidf_obj: Any = None

TITLE_TO_IDX: Optional[Dict[str, int]] = None
TITLE_TO_IMDB: Optional[Dict[str, str]] = None

# In-memory OMDB response cache
_omdb_cache: Dict[str, dict] = {}


# =========================
# MODELS
# =========================
class MovieCard(BaseModel):
    imdb_id: str
    title: str
    poster_url: Optional[str] = None
    year: Optional[str] = None
    imdb_rating: Optional[str] = None


class MovieDetails(BaseModel):
    imdb_id: str
    title: str
    plot: Optional[str] = None
    year: Optional[str] = None
    released: Optional[str] = None
    poster_url: Optional[str] = None
    genres: List[str] = []
    director: Optional[str] = None
    actors: Optional[str] = None
    runtime: Optional[str] = None
    imdb_rating: Optional[str] = None
    rated: Optional[str] = None


class TFIDFRecItem(BaseModel):
    title: str
    score: float
    movie: Optional[MovieCard] = None


class SearchBundleResponse(BaseModel):
    query: str
    movie_details: MovieDetails
    tfidf_recommendations: List[TFIDFRecItem]
    genre_recommendations: List[MovieCard]


# =========================
# UTILS
# =========================
def _norm_title(t: str) -> str:
    return str(t).strip().lower()


def _clean(val: Optional[str]) -> Optional[str]:
    """Return None for OMDB 'N/A' values."""
    if not val or val == "N/A":
        return None
    return val


def _parse_genres_omdb(genre_str: Optional[str]) -> List[str]:
    """Parse OMDB comma-separated genre string into list."""
    if not genre_str or genre_str == "N/A":
        return []
    return [g.strip() for g in genre_str.split(",") if g.strip()]


# =========================
# OMDB API HELPERS
# =========================
async def omdb_get(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safe OMDB GET:
    - Network errors -> 502
    - OMDB API errors -> 502 with detail
    """
    q = dict(params)
    q["apikey"] = OMDB_API_KEY

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(OMDB_BASE, params=q)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"OMDB request error: {type(e).__name__} | {repr(e)}",
        )

    data = r.json()
    if data.get("Response") == "False":
        raise HTTPException(
            status_code=502,
            detail=f"OMDB error: {data.get('Error', 'Unknown')}",
        )
    return data


async def omdb_search(query: str, page: int = 1) -> Dict[str, Any]:
    """Search OMDB for multiple movies by keyword."""
    return await omdb_get({"s": query, "type": "movie", "page": page})


async def omdb_details_by_id(imdb_id: str) -> Dict[str, Any]:
    """Fetch full movie details from OMDB by IMDb ID (cached)."""
    cache_key = f"id:{imdb_id}"
    if cache_key in _omdb_cache:
        return _omdb_cache[cache_key]
    data = await omdb_get({"i": imdb_id, "plot": "full"})
    _omdb_cache[cache_key] = data
    return data


async def omdb_details_by_title(title: str) -> Dict[str, Any]:
    """Fetch full movie details from OMDB by title (cached)."""
    cache_key = f"t:{_norm_title(title)}"
    if cache_key in _omdb_cache:
        return _omdb_cache[cache_key]
    data = await omdb_get({"t": title, "type": "movie", "plot": "full"})
    _omdb_cache[cache_key] = data
    return data


def omdb_to_details(data: dict) -> MovieDetails:
    return MovieDetails(
        imdb_id=data.get("imdbID", ""),
        title=data.get("Title", ""),
        plot=_clean(data.get("Plot")),
        year=_clean(data.get("Year")),
        released=_clean(data.get("Released")),
        poster_url=_clean(data.get("Poster")),
        genres=_parse_genres_omdb(data.get("Genre")),
        director=_clean(data.get("Director")),
        actors=_clean(data.get("Actors")),
        runtime=_clean(data.get("Runtime")),
        imdb_rating=_clean(data.get("imdbRating")),
        rated=_clean(data.get("Rated")),
    )


def omdb_to_card(data: dict) -> MovieCard:
    return MovieCard(
        imdb_id=data.get("imdbID", ""),
        title=data.get("Title", ""),
        poster_url=_clean(data.get("Poster")),
        year=_clean(data.get("Year")),
        imdb_rating=_clean(data.get("imdbRating")),
    )


def omdb_search_item_to_card(item: dict) -> MovieCard:
    """Convert an item from OMDB ?s= search results to a MovieCard."""
    return MovieCard(
        imdb_id=item.get("imdbID", ""),
        title=item.get("Title", ""),
        poster_url=_clean(item.get("Poster")),
        year=_clean(item.get("Year")),
        imdb_rating=None,  # search results don't include rating
    )


async def fetch_card_for_title(title: str) -> Optional[MovieCard]:
    """Fetch a MovieCard from OMDB by title. Returns None on failure."""
    try:
        imdb_id = TITLE_TO_IMDB.get(_norm_title(title)) if TITLE_TO_IMDB else None
        if imdb_id:
            data = await omdb_details_by_id(imdb_id)
        else:
            data = await omdb_details_by_title(title)
        return omdb_to_card(data)
    except Exception:
        return None


async def fetch_cards_batch(titles: List[str]) -> List[Optional[MovieCard]]:
    """Fetch MovieCards for multiple titles in parallel (with caching)."""
    tasks = [fetch_card_for_title(t) for t in titles]
    return await asyncio.gather(*tasks)


# =========================
# TF-IDF Helpers (UNCHANGED — your models are safe)
# =========================
def build_title_to_idx_map(indices: Any) -> Dict[str, int]:
    """
    indices.pkl can be:
    - dict(title -> index)
    - pandas Series (index=title, value=index)
    We normalize into TITLE_TO_IDX.
    """
    title_to_idx: Dict[str, int] = {}

    if isinstance(indices, dict):
        for k, v in indices.items():
            title_to_idx[_norm_title(k)] = int(v)
        return title_to_idx

    # pandas Series or similar mapping
    try:
        for k, v in indices.items():
            title_to_idx[_norm_title(k)] = int(v)
        return title_to_idx
    except Exception:
        raise RuntimeError(
            "indices.pkl must be dict or pandas Series-like (with .items())"
        )


def get_local_idx_by_title(title: str) -> int:
    global TITLE_TO_IDX
    if TITLE_TO_IDX is None:
        raise HTTPException(status_code=500, detail="TF-IDF index map not initialized")
    key = _norm_title(title)
    if key in TITLE_TO_IDX:
        return int(TITLE_TO_IDX[key])
    raise HTTPException(
        status_code=404, detail=f"Title not found in local dataset: '{title}'"
    )


def tfidf_recommend_titles(
    query_title: str, top_n: int = 10
) -> List[Tuple[str, float]]:
    """
    Returns list of (title, score) from local df using cosine similarity on TF-IDF matrix.
    Safe against missing columns/rows.
    """
    global df, tfidf_matrix
    if df is None or tfidf_matrix is None:
        raise HTTPException(status_code=500, detail="TF-IDF resources not loaded")

    idx = get_local_idx_by_title(query_title)

    # query vector
    qv = tfidf_matrix[idx]
    scores = (tfidf_matrix @ qv.T).toarray().ravel()

    # sort descending
    order = np.argsort(-scores)

    out: List[Tuple[str, float]] = []
    for i in order:
        if int(i) == int(idx):
            continue
        try:
            title_i = str(df.iloc[int(i)]["title"])
        except Exception:
            continue
        out.append((title_i, float(scores[int(i)])))
        if len(out) >= top_n:
            break
    return out


# =========================
# LOCAL DATA HELPERS
# =========================
def get_local_movies_by_category(category: str, limit: int = 24) -> pd.DataFrame:
    """Get movies from local dataset sorted by category."""
    global df
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset not loaded")

    if category in ("popular", "trending", "now_playing"):
        return df.nlargest(limit, "popularity")
    elif category == "top_rated":
        return df.nlargest(limit, "vote_average")
    elif category == "upcoming":
        # No release dates in df, use popularity as fallback
        return df.nlargest(limit, "popularity")
    else:
        return df.nlargest(limit, "popularity")


def get_local_movies_by_genre(
    genre_name: str, limit: int = 18, exclude_title: str = ""
) -> pd.DataFrame:
    """Get movies from local dataset filtered by genre."""
    global df
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset not loaded")

    genre_lower = genre_name.strip().lower()
    mask = df["genres"].str.lower().str.contains(genre_lower, na=False)
    filtered = df[mask]

    if exclude_title:
        filtered = filtered[
            filtered["title"].str.lower() != _norm_title(exclude_title)
        ]

    return filtered.nlargest(limit, "popularity")


# =========================
# STARTUP: LOAD PICKLES + BUILD IMDB MAPPING
# =========================
@app.on_event("startup")
def load_pickles():
    global df, indices_obj, tfidf_matrix, tfidf_obj, TITLE_TO_IDX, TITLE_TO_IMDB, _omdb_cache

    # Load df
    with open(DF_PATH, "rb") as f:
        df = pickle.load(f)

    # Ensure numeric columns are actually numeric (they may be stored as strings)
    for col in ("popularity", "vote_average"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Load indices
    with open(INDICES_PATH, "rb") as f:
        indices_obj = pickle.load(f)

    # Load TF-IDF matrix (usually scipy sparse)
    with open(TFIDF_MATRIX_PATH, "rb") as f:
        tfidf_matrix = pickle.load(f)

    # Load tfidf vectorizer (optional, not used directly here)
    with open(TFIDF_PATH, "rb") as f:
        tfidf_obj = pickle.load(f)

    # Build normalized map
    TITLE_TO_IDX = build_title_to_idx_map(indices_obj)

    # Build title -> imdb_id mapping from source CSV
    try:
        csv_path = os.path.join(BASE_DIR, "movies_metadata.csv")
        if os.path.exists(csv_path):
            meta_df = pd.read_csv(
                csv_path, low_memory=False, usecols=["title", "imdb_id"]
            )
            TITLE_TO_IMDB = {}
            for _, row in meta_df.dropna(subset=["title", "imdb_id"]).iterrows():
                key = _norm_title(str(row["title"]))
                TITLE_TO_IMDB[key] = str(row["imdb_id"])
            print(f"[startup] Built title->imdb_id map: {len(TITLE_TO_IMDB)} entries")
    except Exception as e:
        print(f"[startup] Warning: Could not build title->imdb_id mapping: {e}")
        TITLE_TO_IMDB = {}

    # Load disk cache for OMDB responses
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r") as f:
                _omdb_cache = json.load(f)
            print(f"[startup] Loaded OMDB cache: {len(_omdb_cache)} entries")
        except Exception:
            _omdb_cache = {}

    # Sanity check
    if df is None or "title" not in df.columns:
        raise RuntimeError("df.pkl must contain a DataFrame with a 'title' column")


@app.on_event("shutdown")
def save_cache():
    """Persist OMDB cache to disk on shutdown."""
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(_omdb_cache, f)
        print(f"[shutdown] Saved OMDB cache: {len(_omdb_cache)} entries")
    except Exception:
        pass


# =========================
# ROUTES
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- HOME FEED (LOCAL DATA + OMDB POSTERS) ----------
@app.get("/home", response_model=List[MovieCard])
async def home(
    category: str = Query("popular"),
    limit: int = Query(24, ge=1, le=50),
):
    """
    Home feed powered by local dataset.
    Categories: trending, popular, top_rated, now_playing, upcoming
    Posters fetched from OMDB (cached).
    """
    if category not in {"trending", "popular", "top_rated", "upcoming", "now_playing"}:
        raise HTTPException(status_code=400, detail="Invalid category")

    try:
        local_movies = get_local_movies_by_category(category, limit=limit)
        titles = local_movies["title"].tolist()

        # Fetch posters from OMDB in parallel (all cached after first load)
        cards = await fetch_cards_batch(titles)

        result: List[MovieCard] = []
        for i, title in enumerate(titles):
            card = cards[i]
            if card:
                result.append(card)
            else:
                # Fallback: return local data without poster
                imdb_id = (
                    TITLE_TO_IMDB.get(_norm_title(title), "")
                    if TITLE_TO_IMDB
                    else ""
                )
                result.append(
                    MovieCard(imdb_id=imdb_id, title=title, poster_url=None)
                )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Home route failed: {e}")


# ---------- OMDB KEYWORD SEARCH (MULTIPLE RESULTS) ----------
@app.get("/search")
async def search_movies(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1, le=100),
):
    """
    Returns OMDB search results.
    Shape: {"Search": [...], "totalResults": "N", "Response": "True"}
    """
    return await omdb_search(query=query, page=page)


# ---------- MOVIE DETAILS ----------
@app.get("/movie/id/{imdb_id}", response_model=MovieDetails)
async def movie_details_route(imdb_id: str):
    """Get movie details by IMDb ID (e.g. tt0114709)."""
    data = await omdb_details_by_id(imdb_id)
    return omdb_to_details(data)


@app.get("/movie/title", response_model=MovieDetails)
async def movie_details_by_title_route(
    title: str = Query(..., min_length=1),
):
    """Get movie details by exact title."""
    data = await omdb_details_by_title(title)
    return omdb_to_details(data)


# ---------- GENRE RECOMMENDATIONS (LOCAL DATA) ----------
@app.get("/recommend/genre", response_model=List[MovieCard])
async def recommend_genre(
    imdb_id: str = Query(...),
    limit: int = Query(18, ge=1, le=50),
):
    """
    Given an IMDb ID:
    - fetch details from OMDB to get genres
    - find similar movies from local dataset by genre
    - return with OMDB posters (cached)
    """
    details_data = await omdb_details_by_id(imdb_id)
    genres = _parse_genres_omdb(details_data.get("Genre"))
    if not genres:
        return []

    # Use first genre for discovery
    genre_df = get_local_movies_by_genre(
        genres[0], limit=limit, exclude_title=details_data.get("Title", "")
    )

    titles = genre_df["title"].tolist()
    cards = await fetch_cards_batch(titles)

    result: List[MovieCard] = []
    for i, title in enumerate(titles):
        card = cards[i]
        if card and card.imdb_id != imdb_id:
            result.append(card)
        elif card is None:
            imdb = (
                TITLE_TO_IMDB.get(_norm_title(title), "")
                if TITLE_TO_IMDB
                else ""
            )
            if imdb != imdb_id:
                result.append(MovieCard(imdb_id=imdb, title=title, poster_url=None))

    return result[:limit]


# ---------- TF-IDF ONLY ----------
@app.get("/recommend/tfidf")
async def recommend_tfidf(
    title: str = Query(..., min_length=1),
    top_n: int = Query(10, ge=1, le=50),
):
    recs = tfidf_recommend_titles(title, top_n=top_n)
    return [{"title": t, "score": s} for t, s in recs]


# ---------- BUNDLE: Details + TF-IDF recs + Genre recs ----------
@app.get("/movie/search", response_model=SearchBundleResponse)
async def search_bundle(
    query: str = Query(..., min_length=1),
    tfidf_top_n: int = Query(12, ge=1, le=30),
    genre_limit: int = Query(12, ge=1, le=30),
):
    """
    Bundle endpoint: movie details + TF-IDF recs + genre recs.
    Uses OMDB for details and posters, local data for recommendations.
    """
    # Try to find the movie — first by OMDB title search
    try:
        details_data = await omdb_details_by_title(query)
    except HTTPException:
        raise HTTPException(
            status_code=404, detail=f"No movie found for query: {query}"
        )

    details = omdb_to_details(details_data)

    # 1) TF-IDF recommendations (never crash endpoint)
    tfidf_items: List[TFIDFRecItem] = []
    recs: List[Tuple[str, float]] = []
    try:
        recs = tfidf_recommend_titles(details.title, top_n=tfidf_top_n)
    except Exception:
        try:
            recs = tfidf_recommend_titles(query, top_n=tfidf_top_n)
        except Exception:
            recs = []

    if recs:
        rec_titles = [t for t, _ in recs]
        cards = await fetch_cards_batch(rec_titles)
        for i, (title, score) in enumerate(recs):
            tfidf_items.append(
                TFIDFRecItem(title=title, score=score, movie=cards[i])
            )

    # 2) Genre recommendations (local data)
    genre_recs: List[MovieCard] = []
    if details.genres:
        genre_df = get_local_movies_by_genre(
            details.genres[0], limit=genre_limit, exclude_title=details.title
        )
        genre_titles = genre_df["title"].tolist()
        genre_cards = await fetch_cards_batch(genre_titles)
        for i, title in enumerate(genre_titles):
            card = genre_cards[i]
            if card and card.imdb_id != details.imdb_id:
                genre_recs.append(card)
            elif card is None:
                imdb = (
                    TITLE_TO_IMDB.get(_norm_title(title), "")
                    if TITLE_TO_IMDB
                    else ""
                )
                genre_recs.append(
                    MovieCard(imdb_id=imdb, title=title, poster_url=None)
                )

    return SearchBundleResponse(
        query=query,
        movie_details=details,
        tfidf_recommendations=tfidf_items,
        genre_recommendations=genre_recs[:genre_limit],
    )
