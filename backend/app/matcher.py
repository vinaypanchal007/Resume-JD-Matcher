import os
import re
from functools import lru_cache
from io import BytesIO

from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity


load_dotenv()


def clean_text(text: str) -> str:
    replacements = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\u2014": "-",
        "\xa0": " ",
        "\u200b": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()


def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return clean_text("\n".join(pages))


def keyword_overlap(jd_text: str, resume_text: str, limit: int = 12) -> list[str]:
    jd_words = {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z+#.\-]{2,}", jd_text)
        if word.lower() not in ENGLISH_STOP_WORDS
    }
    resume_words = {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z+#.\-]{2,}", resume_text)
        if word.lower() not in ENGLISH_STOP_WORDS
    }
    return sorted(jd_words & resume_words)[:limit]


class ResumeMatcher:
    def __init__(self) -> None:
        self.embed_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.embed_model = SentenceTransformer(self.embed_model_name)
        self.groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        if groq_api_key == "your_groq_api_key_here":
            groq_api_key = ""
        self.client = Groq(api_key=groq_api_key) if groq_api_key else None

    @property
    def explanations_enabled(self) -> bool:
        return self.client is not None

    def explain_match(self, jd_text: str, resume_text: str, score: float, overlap: list[str]) -> str | None:
        if not self.client:
            return None

        prompt = f"""
Job Description:
{jd_text[:4000]}

Resume:
{resume_text[:4000]}

Similarity score: {score:.2f} (0 = unrelated, 1 = perfect match)
Shared keywords: {", ".join(overlap) if overlap else "none detected"}

In 2-3 sentences, explain whether this resume is a strong match for the job.
Reference specific skills or experience from the resume and mention any important gaps.
Use only plain ASCII characters.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception:
            self.client = None
            return None

    def match(
        self,
        jd_texts: list[dict],
        resumes: list[dict],
        top_k: int = 5,
        explain: bool = True,
    ) -> list[dict]:
        if not jd_texts:
            raise ValueError("Add at least one job description.")
        if not resumes:
            raise ValueError("Add at least one resume by pasting text or uploading a PDF.")

        jd_payloads = [
            {"id": item["id"], "title": item["title"], "text": clean_text(item["text"])}
            for item in jd_texts
            if clean_text(item["text"])
        ]
        resume_payloads = [
            {"id": item["id"], "name": item["name"], "text": clean_text(item["text"])}
            for item in resumes
            if clean_text(item["text"])
        ]

        if not jd_payloads:
            raise ValueError("Every job description is empty.")
        if not resume_payloads:
            raise ValueError("Every resume is empty or the uploaded PDFs had no extractable text.")

        jd_vecs = self.embed_model.encode([item["text"] for item in jd_payloads], show_progress_bar=False)
        resume_vecs = self.embed_model.encode([item["text"] for item in resume_payloads], show_progress_bar=False)
        score_matrix = cosine_similarity(jd_vecs, resume_vecs)

        results = []
        for jd_index, jd in enumerate(jd_payloads):
            ranked_indexes = score_matrix[jd_index].argsort()[::-1][:top_k]
            matches = []
            for resume_index in ranked_indexes:
                resume = resume_payloads[int(resume_index)]
                score = float(score_matrix[jd_index][resume_index])
                overlap = keyword_overlap(jd["text"], resume["text"])
                explanation = self.explain_match(jd["text"], resume["text"], score, overlap) if explain else None
                matches.append(
                    {
                        "resume_id": resume["id"],
                        "resume_name": resume["name"],
                        "score": round(score, 3),
                        "matched_keywords": overlap,
                        "explanation": explanation,
                        "resume_preview": resume["text"][:1200],
                    }
                )
            results.append(
                {
                    "jd_id": jd["id"],
                    "jd_title": jd["title"],
                    "matches": matches,
                }
            )

        return results


@lru_cache(maxsize=1)
def get_matcher() -> ResumeMatcher:
    return ResumeMatcher()
