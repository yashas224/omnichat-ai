from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Path

from omnichat_ai.backend.dto import QARequest
from omnichat_ai.agent.graph import agent

import re
import unicodedata

MAX_LENGTH = 5000

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent=agent
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/chat/{flow}/{user_id}")
async def root(req:QARequest,
               flow: Annotated[str, Path(title="Agent Flow selected")],
               user_id: Annotated[str, Path(title="The ID of the user", min_length=5)]):
    config = {"configurable": {"thread_id": str(user_id)}}

    result=app.state.agent.invoke({"messages":[req.user_query]},config=config)
    return {"result": result["return_result"],"flow":flow}