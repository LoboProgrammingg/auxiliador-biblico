class InvalidReference(Exception):
    def __init__(self, ref: str) -> None:
        super().__init__(f"referência não encontrada: {ref}")
        self.ref = ref
