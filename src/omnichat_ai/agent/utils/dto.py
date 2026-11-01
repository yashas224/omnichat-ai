from pydantic import BaseModel, Field


class SubPoint(BaseModel):
    """A single point supporting the response description"""
    content: str = Field(description="The text of the sub point")
    sources: list[str] = Field(
        default_factory=list,
        description="URLs or document references backing this sub point, empty if there are none",
    )


class QAChatAgentResponse(BaseModel):
    """Conversation response of the QA chat agent"""
    description: str = Field(description="The main answer to the user's question")
    sub_points: list[SubPoint] = Field(
        default_factory=list,
        description="Supporting points that expand on the description",
    )
