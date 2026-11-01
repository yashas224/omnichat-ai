import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage



class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    sanity_Result: bool
    user_query:str
    return_result:dict | None
    flow: str