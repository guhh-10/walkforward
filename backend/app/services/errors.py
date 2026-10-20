class DomainError(Exception):
    """Business-rule failure; the API layer maps it to {detail, code}."""

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


class NotFoundError(DomainError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(404, code, detail)


class ValidationDomainError(DomainError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(422, code, detail)
