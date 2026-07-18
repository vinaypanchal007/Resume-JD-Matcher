from pydantic import BaseModel, Field


class TextDocument(BaseModel):
    id: str = Field(..., min_length=1)
    title: str | None = None
    name: str | None = None
    text: str = Field(..., min_length=20)


class MatchRequest(BaseModel):
    job_descriptions: list[TextDocument] = Field(..., min_length=1)
    resumes: list[TextDocument] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=25)
    explain: bool = True


class MatchItem(BaseModel):
    resume_id: str
    resume_name: str
    score: float
    matched_keywords: list[str]
    explanation: str | None = None
    resume_preview: str


class JobMatchGroup(BaseModel):
    jd_id: str
    jd_title: str
    matches: list[MatchItem]


class MatchResponse(BaseModel):
    results: list[JobMatchGroup]


class HealthResponse(BaseModel):
    status: str
    embedding_model: str
    explanations_enabled: bool
