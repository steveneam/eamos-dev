class RuntimeCompositionError(RuntimeError):
    """A configured runtime dependency failed a fail-closed startup check."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
