class OllamaEmbeddings:
    def __init__(self, model: str, base_url: str, timeout: float) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
