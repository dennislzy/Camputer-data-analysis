# Camputer Data Analysis

An intelligent camp-pricing analysis system built with **LangGraph + FastAPI**. The system combines user comments and camp statistics, runs them through a multi-stage LLM analysis pipeline, and produces a complete **pricing strategy report** to help organizers set more competitive prices for their camps/events.

---

## ✨ Features

- **Multi-stage analysis pipeline (LangGraph Workflow)**: A stateful graph workflow chains three analysis nodes together — comments → statistics → final recommendation — so the reasoning stays traceable at every step.
- **Semantic comment search (RAG)**: Uses a FAISS vector store + OpenAI Embeddings to semantically retrieve the comments most relevant to a given query.
- **Statistics extraction**: Fetches category-level camp statistics (registration rates, price distribution, discount strategy, etc.) from a backend API, then has an LLM distill them into structured key numbers.
- **Pricing strategy generation**: Combines the comment analysis and statistics into a full report — market insights, recommended price range, discount strategy, risk controls, and expected outcomes.
- **Hahow course scraper (supporting tool)**: Uses Selenium to scrape course listings (title, instructor, rating, price, etc.) from the Hahow platform, which can serve as external market-comparison data.

---

## 🏗️ Architecture

```
                     ┌────────────────────┐
                     │   FastAPI /test/    │
                     │   {category_name}   │
                     └─────────┬──────────┘
                               │ build initial State
                               ▼
                 ┌─────────────────────────────┐
                 │   LangGraph StateGraph        │
                 │                                │
                 │  ① content_analysis            │
                 │     └ semantic comment search   │
                 │       (FAISS) + LLM summary     │
                 │              │                 │
                 │              ▼                 │
                 │  ② statistics_analysis         │
                 │     └ fetch backend stats API   │
                 │       + LLM key-figure extract  │
                 │              │                 │
                 │              ▼                 │
                 │  ③ final_result                │
                 │     └ combine comments + stats  │
                 │       + LLM pricing strategy     │
                 └─────────────────────────────┘
                               │
                               ▼
                  Return final pricing analysis report (Markdown text)
```

---

## 📁 Project Structure

```
Camputer-data-analysis-main/
├── main.py                        # FastAPI entry point; defines the LangGraph workflow and API routes
├── node/                          # LangGraph analysis nodes
│   ├── state.py                   # Shared workflow state (AnalysisState)
│   ├── comment_node.py            # Comment retrieval + content analysis node
│   ├── statistics_node.py         # Statistics extraction node
│   ├── final_result_node.py       # Final synthesis + pricing recommendation node
│   ├── category_node.py           # Fetches the list of camp categories
│   ├── hahow_node.py              # Hahow course scraper (LangChain tool)
│   └── comment_faiss_db/          # FAISS index files for comment vectors
├── vectorDatabase/
│   └── FaissVector.py             # Generic FAISS vector store wrapper (CustomVectorStore)
├── hahow_data/
│   └── base_config.py             # Hahow scraping details (page scrolling, data extraction, etc.)
├── comment_faiss_db/               # FAISS index files (root-level copy)
├── data/                          # Sample / cached data (JSON)
│   ├── interests_data.json
│   ├── recommendations_data.json
│   └── ...
└── README.md
```

---

## ⚙️ Requirements

- Python 3.12+
- Chrome / Chromium (required for the Selenium scraper)
- A valid OpenAI API key
- A backend service (defaulting to `http://localhost:8080`) exposing:
  - `GET /comments/category/{category_id}` — comment data for a category
  - `GET /api/analytics/category-stats/{category_name}` — statistics for a category
  - `GET /api/camp-categories/distinct-categories` — list of camp categories


## 🚀 Getting Started

1. **Install dependencies**

   ```bash
   pip install fastapi uvicorn typer langgraph langchain-core langchain-openai langchain-community faiss-cpu selenium requests
   ```

2. **Set the environment variable** (OpenAI API key)

   ```bash
   export OPEN_AI_KEY="your-openai-api-key"
   ```

3. **Start the backend data service**

   Make sure a service is running on `http://localhost:8080` that can serve the comment / statistics / category endpoints.

4. **Run the FastAPI app**

   ```bash
   python main.py
   ```

   The service listens on `http://127.0.0.1:7000` by default.

5. **Call the analysis API**

   ```bash
   curl http://127.0.0.1:7000/test/programming
   ```

   Replace `programming` with the camp category you want to analyze. The API returns a complete pricing strategy report as Markdown text.

---

## 📡 API Reference

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Health check, returns a welcome message |
| `GET` | `/test/{category_name}` | Runs the full LangGraph analysis pipeline for the given camp category and returns the final pricing strategy report |

`{category_name}` is the camp category name (e.g. "programming", "art"), used to:
- Filter comments by category for the semantic search
- Query the backend statistics API for that category's market data

---

## ⚠️ Notes

- The web scraper (Hahow) relies on specific CSS selectors, which may need updating if the target site changes its layout.
- The quality of the LLM analysis depends heavily on how complete the backend's comment and statistics data are; sparse data may lead to less reliable results.
- The backend service address (`localhost:8080`) is currently hardcoded in the code — consider making it configurable via environment variables for production use.
- `comment_faiss_db/` contains a pre-built vector index. If the comment data schema changes, it's recommended to clear and rebuild the index.

---

## 📄 License

No license has been specified yet — add one (e.g. MIT License) based on your needs.
