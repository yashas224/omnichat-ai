
from langsmith import BaseModel


class QARequest(BaseModel):
    user_query: str