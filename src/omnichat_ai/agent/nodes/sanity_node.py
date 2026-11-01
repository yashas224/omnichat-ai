from omnichat_ai.agent.state.agent_state import MessagesState
from openai import OpenAI
from dotenv import load_dotenv

from omnichat_ai.agent.utils.utils import basic_sanitize
load_dotenv()
client = OpenAI()


def sanity_node(state: MessagesState):
    allow=False
    user_query=basic_sanitize(state["messages"][-1])
    if user_query: 
        response = client.moderations.create(
            model="omni-moderation-latest",
            input=user_query
        )
        result = response.results[0]
        allow=not result.flagged
        print("Flagged:", result.flagged)
        print("Categories:", result.categories)
        print("Scores:", result.category_scores)

    return {"sanity_Result":allow,"user_query":user_query,"return_result":None}


