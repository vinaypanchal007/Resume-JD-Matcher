import json
import os
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.matcher import ResumeMatcher, extract_pdf_text, get_matcher
from app.schemas import HealthResponse, MatchRequest, MatchResponse


frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://resume-jd-matcher-rho.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app = FastAPI(
    title="Resume JD Matcher API",
    version="2.0.0",
    description="Match one or more job descriptions against pasted resumes or uploaded resume PDFs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allowed_origins)),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def matcher_dependency() -> ResumeMatcher:
    try:
        return get_matcher()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Matcher failed to initialize: {exc}") from exc


def _normalize_jds(items: list) -> list[dict]:
    normalized = []
    for index, item in enumerate(items, start=1):
        normalized.append(
            {
                "id": item.id,
                "title": item.title or f"Job description {index}",
                "text": item.text,
            }
        )
    return normalized


def _normalize_resumes(items: list) -> list[dict]:
    normalized = []
    for index, item in enumerate(items, start=1):
        normalized.append(
            {
                "id": item.id,
                "name": item.name or item.title or f"Resume {index}",
                "text": item.text,
            }
        )
    return normalized


@app.get("/health", response_model=HealthResponse)
def health(
    matcher: ResumeMatcher = Depends(matcher_dependency),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        embedding_model="Scikit-Learn TF-IDF",
        explanations_enabled=matcher.explanations_enabled,
    )


@app.post("/match", response_model=MatchResponse)
def match_resumes(
    request: MatchRequest,
    matcher: ResumeMatcher = Depends(matcher_dependency),
) -> MatchResponse:
    try:
        results = matcher.match(
            jd_texts=_normalize_jds(request.job_descriptions),
            resumes=_normalize_resumes(request.resumes),
            top_k=request.top_k,
            explain=request.explain,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MatchResponse(results=results)


@app.post("/match/upload", response_model=MatchResponse)
async def match_uploaded_resumes(
    job_descriptions_json: str = Form(...),
    resume_texts_json: str = Form("[]"),
    top_k: int = Form(5),
    explain: bool = Form(True),
    resume_files: list[UploadFile] = File(default=[]),
    matcher: ResumeMatcher = Depends(matcher_dependency),
) -> MatchResponse:
    try:
        job_descriptions = json.loads(job_descriptions_json)
        resume_texts = json.loads(resume_texts_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON in submitted form data.") from exc

    resumes = list(resume_texts)
    for upload in resume_files:
        if not upload.filename:
            continue
        if not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{upload.filename} is not a PDF file.")
        text = extract_pdf_text(await upload.read())
        resumes.append(
            {
                "id": f"pdf-{uuid4().hex}",
                "name": upload.filename,
                "text": text,
            }
        )

    try:
        results = matcher.match(
            jd_texts=[
                {
                    "id": str(item.get("id") or f"jd-{index}"),
                    "title": str(item.get("title") or f"Job description {index}"),
                    "text": str(item.get("text") or ""),
                }
                for index, item in enumerate(job_descriptions, start=1)
            ],
            resumes=[
                {
                    "id": str(item.get("id") or f"resume-{index}"),
                    "name": str(item.get("name") or item.get("title") or f"Resume {index}"),
                    "text": str(item.get("text") or ""),
                }
                for index, item in enumerate(resumes, start=1)
            ],
            top_k=top_k,
            explain=explain,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MatchResponse(results=results)
