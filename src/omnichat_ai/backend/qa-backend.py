from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, Path
import json

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from omnichat_ai.backend.dto import QARequest
from omnichat_ai.agent.graph import agent
from omnichat_ai.agent.utils.callback import callback
import re
import unicodedata

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent=agent
    yield

app = FastAPI(lifespan=lifespan)

def to_jsonable(value):
    return value.model_dump() if isinstance(value, BaseModel) else str(value)

@app.post("/chat/{flow}/{user_id}")
async def root(req:QARequest,
               flow: Annotated[str, Path(title="Agent Flow selected")],
               user_id: Annotated[str, Path(title="The ID of the user", min_length=5)]):
    config = {"configurable": {"thread_id": str(user_id)},"metadata": {"user_id": user_id}}
    # Sync generator so Starlette runs it in a threadpool instead of blocking the event loop
    def event_stream():
        # subgraphs=True because the LLM calls happen inside qa_agent, a nested graph
        for part in app.state.agent.stream(
                {"messages":[req.user_query]}
                ,config=config,
                stream_mode=["updates", "messages"]
                ,version="v2"
                ,subgraphs=True
                ):
            event = {
                "type": part["type"],
                "namespace": part["ns"],
                "data": part["data"]
            }
            yield f"data: {json.dumps(event, default=to_jsonable)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.delete("/chat/{user_id}", status_code=204)
async def clear_chat(user_id: Annotated[str, Path(title="The ID of the user", min_length=5)]):
    # Removes the conversation the agent remembers for this user, including the nested qa_agent's
    app.state.agent.checkpointer.delete_thread(str(user_id))

@app.get("/metrics/{user_id}")
async def metrics(user_id: Annotated[str, Path(title="The ID of the user", min_length=5)]):
    return callback.get_metrics(user_id)