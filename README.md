# 🎬 CineMatch — AI-Powered Movie Recommender

A full-stack movie recommendation system that combines **TF-IDF content-based filtering** with real-time movie data from the **OMDB API**. Built with a FastAPI backend and a Streamlit frontend, CineMatch helps you discover your next favorite movie through intelligent, AI-driven similarity analysis.

---

## ✨ Features

| Feature | Description |
|---|---|
| **TF-IDF Recommendations** | Content-based filtering using TF-IDF vectorization and cosine similarity on a 45,000+ movie dataset |
| **OMDB Integration** | Live movie details, posters, ratings, and metadata fetched from the OMDB API |
| **Genre Discovery** | Browse similar movies by genre, powered by the local dataset |
| **Keyword Search** | Search any movie by title with real-time OMDB results and smart suggestions |
| **Home Feed** | Curated movie grids — Trending, Popular, Top Rated, Now Playing, Upcoming |
| **Dark / Light Mode** | Toggle between dark and light themes with a full design system |
| **Response Caching** | In-memory + disk-persisted OMDB cache to minimize API calls |
| **Chatbot (Coming Soon)** | AI movie assistant placeholder for future development |

---

## 🏗️ Architecture

```
┌──────────────────────┐       ┌──────────────────────┐
│   Streamlit Frontend │◄─────►│   FastAPI Backend     │
│       (app.py)       │  HTTP │      (main.py)        │
└──────────────────────┘       └──────────┬───────────┘
                                          │
                        ┌─────────────────┼─────────────────┐
                        │                 │                 │
                  ┌─────▼─────┐   ┌───────▼──────┐  ┌──────▼──────┐
                  │  TF-IDF   │   │  OMDB API    │  │  Local CSV  │
                  │  Engine   │   │  (Posters,   │  │  (45K+      │
                  │ (Pickles) │   │   Ratings)   │  │   Movies)   │
                  └───────────┘   └──────────────┘  └─────────────┘
```

- **Frontend** — Streamlit app with custom CSS design system (glassmorphism, Font Awesome icons, Inter font)
- **Backend** — FastAPI REST API serving recommendations, search, and movie details
- **ML Engine** — Pre-trained TF-IDF vectorizer + sparse cosine similarity matrix (pickled)
- **Data Source** — `movies_metadata.csv` (The Movies Dataset) + OMDB for live enrichment

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11**
- An **OMDB API key** — get one free at [omdbapi.com](https://www.omdbapi.com/apikey.aspx)

### 1. Clone the Repository

```bash
git clone https://github.com/juniorpawar/movie-recommendation-NLP-DL.git
cd movie-recommendation-NLP-DL
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root:

```env
OMDB_API_KEY=your_omdb_api_key_here
```

### 5. Prepare the Data

Make sure the following files are present in the project root (generated from `movies.ipynb`):

| File | Description |
|---|---|
| `movies_metadata.csv` | Source dataset with 45K+ movies |
| `df.pkl` | Preprocessed DataFrame (pickle) |
| `indices.pkl` | Title → index mapping |
| `tfidf.pkl` | Fitted TF-IDF vectorizer |
| `tfidf_matrix.pkl` | Precomputed TF-IDF sparse matrix |

> **Note:** Run the `movies.ipynb` notebook to generate the pickle files if they're missing.

### 6. Run the Application

**Start the FastAPI backend:**

```bash
uvicorn main:app --reload --port 8000
```

**Start the Streamlit frontend** (in a separate terminal):

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501` with the API at `http://localhost:8000`.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/home?category=popular&limit=24` | Home feed (trending, popular, top_rated, now_playing, upcoming) |
| `GET` | `/search?query=inception` | OMDB keyword search |
| `GET` | `/movie/id/{imdb_id}` | Movie details by IMDb ID |
| `GET` | `/movie/title?title=Inception` | Movie details by title |
| `GET` | `/recommend/tfidf?title=Inception&top_n=10` | TF-IDF similarity recommendations |
| `GET` | `/recommend/genre?imdb_id=tt1375666&limit=18` | Genre-based recommendations |
| `GET` | `/movie/search?query=Inception` | Bundle: details + TF-IDF recs + genre recs |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit, Custom CSS, Font Awesome, Google Fonts (Inter) |
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **ML / NLP** | Scikit-learn (TF-IDF), SciPy (sparse matrices), NumPy |
| **Data** | Pandas, The Movies Dataset (45K+ movies) |
| **External API** | OMDB API (movie posters, ratings, metadata) |
| **HTTP Client** | HTTPX (async) |
| **Runtime** | Python 3.11 |

---

## 📁 Project Structure

```
movie-rec/
├── .env                    # OMDB API key (not committed)
├── .gitignore              # Ignored files
├── .python-version         # Python version (3.11)
├── .streamlit/
│   └── config.toml         # Streamlit server config
├── app.py                  # Streamlit frontend (397 lines)
├── main.py                 # FastAPI backend + ML engine (625 lines)
├── movies.ipynb            # Jupyter notebook for data preprocessing & model training
├── movies_metadata.csv     # Source dataset
├── df.pkl                  # Preprocessed DataFrame
├── indices.pkl             # Title-to-index mapping
├── tfidf.pkl               # TF-IDF vectorizer
├── tfidf_matrix.pkl        # Precomputed TF-IDF matrix
├── .omdb_cache.json        # Persistent OMDB response cache
├── packages.txt            # System-level dependencies (for deployment)
├── requirements.txt        # Python dependencies
└── runtime.txt             # Python runtime version
```

---

## 🌐 Deployment

The app is configured for deployment on platforms like **Render** or **Streamlit Community Cloud**:

- `runtime.txt` — specifies Python 3.11
- `packages.txt` — system-level dependencies (`zlib1g-dev`, `libjpeg-dev`)
- `requirements.txt` — Python packages
- `.streamlit/config.toml` — headless server mode

**Live API:** `https://movie-recommendation-nlp-dl.onrender.com/`

---

## 🧠 How It Works

1. **Data Preprocessing** (`movies.ipynb`) — Cleans the raw dataset, engineers features (genres, keywords, overview, cast, crew), and builds a combined text "soup" for each movie.

2. **TF-IDF Vectorization** — Converts the text soup into a TF-IDF sparse matrix, capturing the importance of each term relative to the corpus.

3. **Cosine Similarity** — At query time, the system computes cosine similarity between the query movie's TF-IDF vector and all other movies, returning the top-N most similar titles.

4. **OMDB Enrichment** — Recommendations are enriched with live posters, ratings, and metadata from the OMDB API, with aggressive caching to stay within rate limits.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
