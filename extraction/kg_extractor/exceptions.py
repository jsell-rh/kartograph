"""Custom exceptions for knowledge graph extraction."""


class ExtractionError(Exception):
    """Base exception for extraction errors."""

    pass


class PromptTooLongError(ExtractionError):
    """Raised when the prompt exceeds the model's context window (413 error)."""

    def __init__(self, message: str, chunk_size: int | None = None):
        """
        Initialize PromptTooLongError.

        Args:
            message: Error message
            chunk_size: Size of the chunk that was too large (for retry logic)
        """
        super().__init__(message)
        self.chunk_size = chunk_size
