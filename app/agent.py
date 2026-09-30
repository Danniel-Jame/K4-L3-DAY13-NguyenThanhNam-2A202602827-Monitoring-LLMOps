from __future__ import annotations

import os
import time
from dataclasses import dataclass

from . import metrics
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .prompt_management import resolve_prompt
from .tracing import get_langfuse_client, observe, propagate_attributes, tracing_enabled


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    ttft_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe(name="lab-agent-run", as_type="agent", capture_input=False, capture_output=False)
    def run(
        self,
        user_id: str,
        feature: str,
        session_id: str,
        message: str,
        correlation_id: str,
    ) -> AgentResult:
        langfuse_client = get_langfuse_client()
        with propagate_attributes(
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model],
            trace_name="day13-agent-request",
            environment=os.getenv("APP_ENV", "dev"),
            metadata={
                "feature": feature,
                "model": self.model,
                "correlation_id": correlation_id,
            },
        ):
            started = time.perf_counter()
            
            # CP2: Instrument retrieve() as a child observation (span)
            @observe(name="retrieval", as_type="span", capture_input=False, capture_output=False)
            def _instrumented_retrieve(msg: str) -> list[str]:
                retrieved_docs = retrieve(msg)
                langfuse_client.update_current_span(
                    metadata={
                        "query_preview": summarize_text(msg),
                        "doc_count": len(retrieved_docs)
                    }
                )
                return retrieved_docs
                
            docs = _instrumented_retrieve(message)
            
            prompt = resolve_prompt(
                langfuse_client,
                feature=feature,
                docs=docs,
                message=message,
                enabled=tracing_enabled(),
            )
            langfuse_client.update_current_span(
                metadata={
                    "doc_count": len(docs),
                    "query_preview": summarize_text(message),
                    "prompt_name": prompt.name,
                    "prompt_label": prompt.label,
                    "prompt_version": prompt.version,
                    "prompt_source": prompt.source,
                    "prompt_fetch_error": prompt.fetch_error or "",
                },
                version=prompt.version,
            )
            
            # CP2: Instrument FakeLLM.generate() as a child observation (generation)
            @observe(name="generation", as_type="generation", capture_input=False, capture_output=False)
            def _instrumented_generate(prompt_text: str):
                resp = self.llm.generate(prompt_text)
                cost = self._estimate_cost(resp.usage.input_tokens, resp.usage.output_tokens)
                langfuse_client.update_current_observation(
                    model=self.model,
                    usage={
                        "input": resp.usage.input_tokens,
                        "output": resp.usage.output_tokens,
                        "unit": "TOKENS",
                        "cost": cost
                    }
                )
                # Dùng prompt_name thay vì obj ManagedPrompt nguyên gốc để tránh lỗi serialize
                if prompt.managed_prompt:
                   langfuse_client.update_current_observation(prompt_name=prompt.managed_prompt.name, prompt_version=prompt.managed_prompt.version)
                return resp, cost
            
            with propagate_attributes(prompt=prompt.managed_prompt):
                response, cost_usd = _instrumented_generate(prompt.text)
                
            quality_score = self._heuristic_quality(message, response.text, docs)
            latency_ms = int((time.perf_counter() - started) * 1000)

        metrics.record_request(
            latency_ms=latency_ms,
            ttft_ms=response.ttft_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            ttft_ms=response.ttft_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * 3
        output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)