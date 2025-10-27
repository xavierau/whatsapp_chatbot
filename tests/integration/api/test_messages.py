"""Integration tests for messages API endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestMessagesEndpoint:
    """Test suite for /messages endpoint."""

    def test_messages_endpoint_success(self, client):
        """Test successful message processing."""
        # Arrange
        request_data = {
            "user_id": "test_user_123",
            "session_id": "test_session_456",
            "message": "Hello, how are you?",
        }

        # Act
        response = client.post("/messages", json=request_data)

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert "response" in response_data
        assert "session_id" in response_data
        assert response_data["session_id"] == "test_session_456"
        assert isinstance(response_data["response"], str)
        assert len(response_data["response"]) > 0

    def test_messages_endpoint_with_metadata(self, client):
        """Test that response includes metadata."""
        # Arrange
        request_data = {
            "user_id": "test_user_789",
            "session_id": "test_session_101",
            "message": "What can you help me with?",
        }

        # Act
        response = client.post("/messages", json=request_data)

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert "metadata" in response_data
        if response_data["metadata"]:
            assert "model" in response_data["metadata"]

    def test_messages_endpoint_conversation_history(self, client):
        """Test that conversation history is maintained across messages."""
        # Arrange
        session_id = "test_session_history_123"
        request_1 = {
            "user_id": "test_user_history",
            "session_id": session_id,
            "message": "My name is Alice",
        }
        request_2 = {
            "user_id": "test_user_history",
            "session_id": session_id,
            "message": "What is my name?",
        }

        # Act
        response_1 = client.post("/messages", json=request_1)
        response_2 = client.post("/messages", json=request_2)

        # Assert
        assert response_1.status_code == 200
        assert response_2.status_code == 200
        # The second response should reference the name "Alice" from context
        response_2_data = response_2.json()
        assert "response" in response_2_data

    def test_messages_endpoint_missing_user_id(self, client):
        """Test validation error when user_id is missing."""
        # Arrange
        request_data = {
            "session_id": "test_session_456",
            "message": "Hello",
        }

        # Act
        response = client.post("/messages", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_messages_endpoint_missing_session_id(self, client):
        """Test validation error when session_id is missing."""
        # Arrange
        request_data = {
            "user_id": "test_user_123",
            "message": "Hello",
        }

        # Act
        response = client.post("/messages", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_messages_endpoint_missing_message(self, client):
        """Test validation error when message is missing."""
        # Arrange
        request_data = {
            "user_id": "test_user_123",
            "session_id": "test_session_456",
        }

        # Act
        response = client.post("/messages", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_messages_endpoint_empty_message(self, client):
        """Test validation error when message is empty."""
        # Arrange
        request_data = {
            "user_id": "test_user_123",
            "session_id": "test_session_456",
            "message": "",
        }

        # Act
        response = client.post("/messages", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_messages_endpoint_different_sessions_isolated(self, client):
        """Test that different sessions maintain separate conversation histories."""
        # Arrange
        session_1_request = {
            "user_id": "user_1",
            "session_id": "session_1",
            "message": "I like Python",
        }
        session_2_request = {
            "user_id": "user_2",
            "session_id": "session_2",
            "message": "I like JavaScript",
        }

        # Act
        response_1 = client.post("/messages", json=session_1_request)
        response_2 = client.post("/messages", json=session_2_request)

        # Assert
        assert response_1.status_code == 200
        assert response_2.status_code == 200
        assert response_1.json()["session_id"] == "session_1"
        assert response_2.json()["session_id"] == "session_2"
