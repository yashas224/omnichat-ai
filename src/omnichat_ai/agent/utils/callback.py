
import time
from langchain_core.callbacks import BaseCallbackHandler


class AgentMetricsCallback(BaseCallbackHandler):

    def __init__(self):
        self.llm_calls = {}
        self.total_tokens = 0
        self.average_latency = 0.0
        self.llm_errors=0
        self.total_llm_calls = 0
        self.completed_llm_calls = 0

    def on_llm_start(self, serialized, prompts, run_id, **kwargs):
        self.llm_calls[run_id] = time.perf_counter()
        self.total_llm_calls += 1

    def on_chat_model_start(
        self, serialized, messages, run_id, **kwargs
    ):
        self.llm_calls[run_id] = time.perf_counter()
        self.total_llm_calls += 1

    def on_llm_end(self, response, run_id, **kwargs):
        start = self.llm_calls.pop(run_id, None)

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

        self.total_tokens += total_tokens
        self.completed_llm_calls += 1
        self.average_latency += (
            latency - self.average_latency
        ) / self.completed_llm_calls

        print("\n--- LLM CALL METRICS ---")
        print(f"Input tokens : {input_tokens}")
        print(f"Output tokens: {output_tokens}")
        print(f"Total tokens : {total_tokens}")
        print(f"Latency      : {latency:.3f}s")

        print("\n--- CUMULATIVE AGENT METRICS ---")
        print(f"Total tokens : {self.total_tokens}")
        print(f"Avg latency  : {self.average_latency:.3f}s")

    def on_llm_error(self, error, run_id, **kwargs):
        self.llm_calls.pop(run_id, None)
        self.llm_errors+=1
        print(f"LLM error: {error}")

    def get_metrics(self):
        return {
            "total_tokens": self.total_tokens,
            "average_latency": self.average_latency,
            "llm_errors": self.llm_errors,
            "total_llm_calls": self.total_llm_calls,
        }

callback=AgentMetricsCallback()
