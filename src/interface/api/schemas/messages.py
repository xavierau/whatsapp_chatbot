"""Message API schemas."""

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Request schema for incoming messages.

    Attributes:
        user_id: Unique identifier for the user
        session_id: Unique identifier for the conversation session
        message: The message content from the user
    """

    user_id: str = Field(..., min_length=1, description="Unique identifier for the user")
    session_id: str = Field(..., min_length=1, description="Unique identifier for the conversation session")
    message: str = Field(..., min_length=1, description="The message content from the user")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "session_id": "session_67890",
                "message": "Hello, I need help with my notes",
            }
        }


class MessageResponse(BaseModel):
    """Response schema for message replies.

    Attributes:
        response: The generated response from the conversation agent
        session_id: The conversation session identifier
        metadata: Optional metadata about the response generation
    """

    response: str = Field(..., description="The generated response from the conversation agent")
    session_id: str = Field(..., description="The conversation session identifier")
    metadata: dict | None = Field(None, description="Optional metadata about the response generation")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "response": "I can help you with your notes! What would you like to do?",
                "session_id": "session_67890",
                "metadata": {
                    "model": "gemini/gemini-2.0-flash-exp",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            }
        }
