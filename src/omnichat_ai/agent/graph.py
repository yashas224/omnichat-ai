from langgraph.graph import StateGraph, START, END

from omnichat_ai.agent.nodes.sanity_node import sanity_node
from omnichat_ai.agent.nodes.qa_chat_node import qa_chat_node

from omnichat_ai.agent.state.agent_state import MessagesState
from omnichat_ai.db import checkpointer

def sanity_check(state: MessagesState):
    if state["sanity_Result"]:
        return "allow"
    else:
        return "blocked"
graph = StateGraph(MessagesState)

graph.add_node("sanity_node",sanity_node)
graph.add_node("qa_chat_node",qa_chat_node)

graph.set_entry_point("sanity_node")
graph.add_conditional_edges("sanity_node",sanity_check,{
    "allow":"qa_chat_node",
    "blocked":END
})

agent=graph.compile(checkpointer=checkpointer)

agent.get_graph().draw_mermaid_png(output_file_path="omnichat_graph.png")



