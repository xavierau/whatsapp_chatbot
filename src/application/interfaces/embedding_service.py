"""Embedding service protocol for generating text embeddings.

This module defines the interface for embedding generation following
the Dependency Inversion Principle. Different providers (Gemini, OpenAI,
local models) can be used interchangeably.
"""

from typing import Protocol


class IEmbeddingService(Protocol):
    """Protocol defining the contract for embedding generation.

    This protocol abstracts the embedding generation logic, allowing
    different implementations (Gemini, OpenAI, Sentence Transformers)
    to be used interchangeably through dependency injection.

    All methods are async to support non-blocking API calls.
    """

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for given text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If text is empty or invalid
            RuntimeError: If embedding generation fails
        """
        ...

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts (batch operation).

        This method may be more efficient than calling generate_embedding
        multiple times, depending on the provider's API.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors, one for each input text

        Raises:
            ValueError: If any text is empty or invalid
            RuntimeError: If embedding generation fails
        """
        ...

    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this service.

        Returns:
            Integer dimension of embedding vectors
        """
        ...

    def get_model_name(self) -> str:
        """Get the name/identifier of the embedding model being used.

        Returns:
            String identifier of the model
        """
        ...