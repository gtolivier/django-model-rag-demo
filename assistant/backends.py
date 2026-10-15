import httpx


class OllamaEmbeddings:
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

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.post(
            f"{self.base_url}/embeddings",
            json={"model": self.model, "input": texts},
            timeout=self.timeout,
        )
        response.raise_for_status()
        embeddings_in_input_order = sorted(
            response.json()["data"], key=lambda item: item["index"]
        )
        return [item["embedding"] for item in embeddings_in_input_order]
