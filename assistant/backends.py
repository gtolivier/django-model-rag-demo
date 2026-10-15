from collections.abc import Sequence
from typing import Any

import httpx

# Backends are built on every get_embeddings() / get_llm() call, so they share
# one client (and its connection pool) rather than each opening one.
shared_client = httpx.Client()


class OllamaBackend:
    def __init__(
        self,
        model: str,
        base_url: str,
        timeout: float,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.client = client or shared_client

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        response = self.client.post(
            f"{self.base_url}{path}", json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


class OllamaEmbeddings(OllamaBackend):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        answer = self.post("/embeddings", {"model": self.model, "input": list(texts)})
        embeddings_in_input_order = sorted(
            answer["data"], key=lambda item: item["index"]
        )
        return [item["embedding"] for item in embeddings_in_input_order]


class OllamaLLM(OllamaBackend):
    def complete(self, prompt: str, *, system: str) -> str:
        answer = self.post(
            "/chat/completions",
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        return str(answer["choices"][0]["message"]["content"])
