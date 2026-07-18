import os
import re
from functools import lru_cache
from io import BytesIO

from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader
from sklearn.feature_extraction.text import (
    ENGLISH_STOP_WORDS,
    TfidfVectorizer,
)
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
    def __init__(self):
        self.groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

        groq_key = os.getenv("GROQ_API_KEY", "").strip()

        if groq_key == "your_groq_api_key_here":
            groq_key = ""

        self.client = Groq(api_key=groq_key) if groq_key else None

    @property
    def explanations_enabled(self):
        return self.client is not None

    def explain_match(
        self,
        jd_text: str,
        resume_text: str,
        score: float,
        overlap: list[str],
    ):
        if not self.client:
            return None

        prompt = f"""
Job Description:
{jd_text[:4000]}

Resume:
{resume_text[:4000]}

Similarity Score: {score:.2f}

Matched Keywords:
{", ".join(overlap) if overlap else "None"}

Explain in 2-3 sentences whether this candidate is a good fit.
Mention strengths and missing skills.
Use plain ASCII characters only.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            return response.choices[0].message.content

        except Exception:
            return None

    def match(
        self,
        jd_texts: list[dict],
        resumes: list[dict],
        top_k: int = 5,
        explain: bool = True,
    ):

        if not jd_texts:
            raise ValueError("Add at least one job description.")

        if not resumes:
            raise ValueError(
                "Add at least one resume by pasting text or uploading a PDF."
            )

        jd_payloads = [
            {
                "id": item["id"],
                "title": item["title"],
                "text": clean_text(item["text"]),
            }
            for item in jd_texts
            if clean_text(item["text"])
        ]

        resume_payloads = [
            {
                "id": item["id"],
                "name": item["name"],
                "text": clean_text(item["text"]),
            }
            for item in resumes
            if clean_text(item["text"])
        ]

        if not jd_payloads:
            raise ValueError("Every job description is empty.")

        if not resume_payloads:
            raise ValueError(
                "Every resume is empty or uploaded PDFs had no extractable text."
            )

        corpus = (
            [jd["text"] for jd in jd_payloads]
            + [resume["text"] for resume in resume_payloads]
        )

        vectorizer = TfidfVectorizer(stop_words="english")

        vectors = vectorizer.fit_transform(corpus)

        jd_vectors = vectors[: len(jd_payloads)]
        resume_vectors = vectors[len(jd_payloads) :]

        score_matrix = cosine_similarity(jd_vectors, resume_vectors)

        results = []

        for jd_index, jd in enumerate(jd_payloads):

            ranked = score_matrix[jd_index].argsort()[::-1][:top_k]

            matches = []

            for idx in ranked:

                resume = resume_payloads[int(idx)]

                score = float(score_matrix[jd_index][idx])

                overlap = keyword_overlap(
                    jd["text"],
                    resume["text"],
                )

                explanation = (
                    self.explain_match(
                        jd["text"],
                        resume["text"],
                        score,
                        overlap,
                    )
                    if explain
                    else None
                )

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
def get_matcher():
    return ResumeMatcher()
