from typing import Any

import httpx


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
        self.client = client or httpx.Client(timeout=timeout)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        response = self.client.post(
            f"{self.base_url}{path}", json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


class OllamaEmbeddings(OllamaBackend):
    def embed(self, texts: list[str]) -> list[list[float]]:
        answer = self.post("/embeddings", {"model": self.model, "input": texts})
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
