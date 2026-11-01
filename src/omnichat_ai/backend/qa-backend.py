from fastapi import FastAPI

from omnichat_ai.backend.dto import QARequest

app = FastAPI()

import re
import unicodedata

MAX_LENGTH = 5000

def basic_sanitize(query: str):
    if not isinstance(query, str):
        return None

    query = unicodedata.normalize("NFKC", query)
    query = query.strip()

    if not query:
        return None

    if len(query) > MAX_LENGTH:
        return None

    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", query):
        return None

    return query


@app.post("/chat")
async def root(req:QARequest):

    return {"message": "Hello World"}