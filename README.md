# Resume JD Matcher

End-to-end website for matching one or more job descriptions against resumes you provide.

This version no longer retrieves resumes from the sample dataset. Users can:

- Paste one or more job descriptions.
- Paste one or more resume texts.
- Upload one or more resume PDFs and extract text automatically.
- Rank each resume against each job description with sentence embeddings.
- Optionally generate explanations with Groq when `GROQ_API_KEY` is configured.

## Project Structure

```text
Resume JD Matcher/
  backend/
    app/
      main.py
      matcher.py
      schemas.py
    requirements.txt
    .env.example
  frontend/
    src/
      App.vue
      main.js
      styles.css
    package.json
    tailwind.config.js
```

## Backend Setup

Open a terminal in `backend/`.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Optional `backend/.env`:

```text
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
EMBEDDING_MODEL=all-MiniLM-L6-v2
FRONTEND_ORIGIN=http://localhost:5173
```

Start the API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://localhost:8000/health
```

## Frontend Setup

Open a second terminal in `frontend/`.

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## API Endpoints

### `POST /match`

JSON-only matching for pasted JD and resume text.

```json
{
  "job_descriptions": [
    {
      "id": "jd-1",
      "title": "Data Analyst",
      "text": "We need a Data Analyst with Python, SQL, and dashboarding..."
    }
  ],
  "resumes": [
    {
      "id": "resume-1",
      "name": "Candidate 1",
      "text": "Candidate resume text..."
    }
  ],
  "top_k": 5,
  "explain": true
}
```

### `POST /match/upload`

Multipart form endpoint used by the website. It accepts:

- `job_descriptions_json`: JSON array of JD objects.
- `resume_texts_json`: JSON array of pasted resume objects.
- `resume_files`: one or more PDF files.
- `top_k`: number of matches to return per JD.
- `explain`: `true` or `false`.

## Notes

- The first backend request can be slow because the embedding model loads into memory.
- PDF extraction works best for text-based PDFs. Scanned image PDFs need OCR, which is not included.
- If `GROQ_API_KEY` is missing, matching still works and explanations are skipped.
- Do not commit `.env` with your API key.
