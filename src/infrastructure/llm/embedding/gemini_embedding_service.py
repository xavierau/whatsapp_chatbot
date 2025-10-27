"""Gemini Embedding Service implementation.

This module implements the IEmbeddingService protocol using Google's
Gemini embedding API.
"""

import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiEmbeddingService:
    """Embedding service using Google Gemini API.

    This implementation uses Google's text-embedding models to generate
    embeddings for note content. It supports both single and batch embedding
    generation.

    The service is configured with API key and model name at initialization.
    """

    # Gemini embedding dimension
    EMBEDDING_DIMENSION = 1536  # gemini-embedding-001 uses 1536 dimensions

    def __init__(self, api_key: str, model_name: str = "gemini-embedding-001") -> None:
        """Initialize Gemini embedding service.

        Args:
            api_key: Google AI API key
            model_name: Gemini embedding model name

        Raises:
            ValueError: If api_key is empty
            RuntimeError: If API configuration fails
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        self._api_key = api_key
        self._model_name = model_name

        try:
            genai.configure(api_key=api_key)
            logger.info("Gemini embedding service initialized with model: %s", model_name)
        except Exception as e:
            logger.error("Failed to configure Gemini API: %s", e)
            raise RuntimeError(f"Failed to configure Gemini API: {e}") from e

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
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        logger.debug("Generating embedding for text (length: %d chars)", len(text))

        try:
            # Use the google-generativeai library's embed_content
            result = genai.embed_content(
                model=self._model_name,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=self.EMBEDDING_DIMENSION,
            )

            embedding = result["embedding"]

            logger.debug("Generated embedding with %d dimensions", len(embedding))
            return embedding

        except Exception as e:
            logger.error("Failed to generate embedding: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to generate embedding: {e}") from e

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts (batch operation).

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors, one for each input text

        Raises:
            ValueError: If any text is empty or invalid
            RuntimeError: If embedding generation fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Validate all texts
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(f"Text at index {i} cannot be empty")

        logger.debug("Generating embeddings for %d texts", len(texts))

        try:
            result = genai.embed_content(
                model=self._model_name,
                content=texts,
                task_type="retrieval_document",
                output_dimensionality=self.EMBEDDING_DIMENSION,
            )

            embeddings = result["embedding"]

            logger.debug("Generated %d embeddings", len(embeddings))
            return embeddings

        except Exception as e:
            logger.error("Failed to generate batch embeddings: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to generate batch embeddings: {e}") from e

    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this service.

        Returns:
            Integer dimension of embedding vectors (1536 for Gemini)
        """
        return self.EMBEDDING_DIMENSION

    def get_model_name(self) -> str:
        """Get the name/identifier of the embedding model being used.

        Returns:
            String identifier of the model
        """
        return self._model_name
