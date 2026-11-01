
import time
from langchain_core.callbacks import BaseCallbackHandler

def new_metrics():
    return {
        "total_tokens": 0,
        "average_latency": 0.0,
        "llm_errors": 0,
        "total_llm_calls": 0,
        "completed_llm_calls": 0,
    }

metric_db= {}
class AgentMetricsCallback(BaseCallbackHandler):

    def __init__(self):
        self.llm_calls = {}

    def _record_start(self, run_id, metadata):
        user_id = (metadata or {}).get("user_id", "unknown")
        self.llm_calls[run_id] = (time.perf_counter(), user_id)
        metric_db.setdefault(user_id, new_metrics())["total_llm_calls"] += 1

    def on_llm_start(self, serialized, prompts, run_id, metadata=None, **kwargs):
        self._record_start(run_id, metadata)

    def on_chat_model_start(
        self, serialized, messages, run_id, metadata=None, **kwargs
    ):
        self._record_start(run_id, metadata)

    def on_llm_end(self, response, run_id, **kwargs):
        start, user_id = self.llm_calls.pop(run_id, (None, "unknown"))

        latency = (
            time.perf_counter() - start
            if start is not None else 0.0
        )

        usage = {}

        if response.generations:
            message = response.generations[0][0].message
            usage = getattr(message, "usage_metadata", None) or {}

        if not usage:
            usage = (response.llm_output or {}).get(
                "token_usage", {}
            )

        input_tokens = usage.get(
            "input_tokens", usage.get("prompt_tokens", 0)
        )
        output_tokens = usage.get(
            "output_tokens", usage.get("completion_tokens", 0)
        )
        total_tokens = usage.get(
            "total_tokens", input_tokens + output_tokens
        )

        metrics = metric_db.setdefault(user_id, new_metrics())
        metrics["total_tokens"] += total_tokens
        metrics["completed_llm_calls"] += 1
        metrics["average_latency"] += (
            latency - metrics["average_latency"]
        ) / metrics["completed_llm_calls"]

        print("\n--- LLM CALL METRICS ---")
        print(f"User         : {user_id}")
        print(f"Input tokens : {input_tokens}")
        print(f"Output tokens: {output_tokens}")
        print(f"Total tokens : {total_tokens}")
        print(f"Latency      : {latency:.3f}s")

        print("\n--- CUMULATIVE USER METRICS ---")
        print(f"Total tokens : {metrics['total_tokens']}")
        print(f"Avg latency  : {metrics['average_latency']:.3f}s")

    def on_llm_error(self, error, run_id, **kwargs):
        _, user_id = self.llm_calls.pop(run_id, (None, "unknown"))
        metric_db.setdefault(user_id, new_metrics())["llm_errors"] += 1
        print(f"LLM error: {error}")

    def get_metrics(self, user_id):
        metrics = metric_db.get(user_id, new_metrics())
        return {
            "total_tokens": metrics["total_tokens"],
            "average_latency": metrics["average_latency"],
            "llm_errors": metrics["llm_errors"],
            "total_llm_calls": metrics["total_llm_calls"],
        }

callback=AgentMetricsCallback()
