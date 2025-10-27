"""Test suite for ConversationAgent DSPy module.

This test suite follows TDD principles and tests:
1. Module initialization and configuration
2. Response generation with and without history
3. Error handling and edge cases
4. Conversation context management
5. DSPy signature validation
6. Tool integration (compute and jot)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.application.interfaces.conversation_agent import (
    ConversationContext,
    Message,
    AgentResponse,
)


class TestMessage:
    """Test the Message dataclass."""

    def test_message_creation_with_valid_data(self) -> None:
        """Test creating a valid message."""
        message = Message(role="user", content="Hello, how are you?")
        assert message.role == "user"
        assert message.content == "Hello, how are you?"
        assert message.metadata is None

    def test_message_with_metadata(self) -> None:
        """Test creating a message with metadata."""
        metadata = {"timestamp": "2025-10-25T10:00:00Z", "user_id": "12345"}
        message = Message(role="assistant", content="I'm doing well!", metadata=metadata)
        assert message.metadata == metadata

    def test_message_immutability(self) -> None:
        """Test that messages are immutable."""
        message = Message(role="user", content="Test")
        with pytest.raises(AttributeError):
            message.role = "assistant"  # type: ignore

    def test_message_with_empty_role_raises_error(self) -> None:
        """Test that empty role raises ValueError."""
        with pytest.raises(ValueError, match="Message role cannot be empty"):
            Message(role="", content="Test content")

    def test_message_with_empty_content_raises_error(self) -> None:
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            Message(role="user", content="")

    def test_message_with_invalid_role_raises_error(self) -> None:
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            Message(role="invalid_role", content="Test content")

    def test_message_valid_roles(self) -> None:
        """Test all valid message roles."""
        valid_roles = ["user", "assistant", "system"]
        for role in valid_roles:
            message = Message(role=role, content="Test")
            assert message.role == role


class TestConversationContext:
    """Test the ConversationContext dataclass."""

    def test_context_creation_with_only_current_message(self) -> None:
        """Test creating context with just current message."""
        context = ConversationContext(current_message="What is the weather?")
        assert context.current_message == "What is the weather?"
        assert context.history == ()
        assert context.metadata is None

    def test_context_with_history(self) -> None:
        """Test creating context with conversation history."""
        history = (
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        )
        context = ConversationContext(
            current_message="How are you?",
            history=history,
        )
        assert len(context.history) == 2
        assert context.history[0].content == "Hello"

    def test_context_with_metadata(self) -> None:
        """Test creating context with metadata."""
        metadata = {"user_id": "user123", "session_id": "sess456"}
        context = ConversationContext(
            current_message="Test",
            metadata=metadata,
        )
        assert context.metadata == metadata

    def test_context_immutability(self) -> None:
        """Test that context is immutable."""
        context = ConversationContext(current_message="Test")
        with pytest.raises(AttributeError):
            context.current_message = "Modified"  # type: ignore

    def test_context_with_empty_message_raises_error(self) -> None:
        """Test that empty current message raises ValueError."""
        with pytest.raises(ValueError, match="Current message cannot be empty"):
            ConversationContext(current_message="")


class TestAgentResponse:
    """Test the AgentResponse dataclass."""

    def test_response_creation_with_content_only(self) -> None:
        """Test creating response with just content."""
        response = AgentResponse(content="This is my response")
        assert response.content == "This is my response"
        assert response.reasoning is None
        assert response.metadata is None

    def test_response_with_reasoning(self) -> None:
        """Test creating response with reasoning."""
        response = AgentResponse(
            content="Paris is the capital",
            reasoning="I know this from geography knowledge",
        )
        assert response.reasoning == "I know this from geography knowledge"

    def test_response_with_metadata(self) -> None:
        """Test creating response with metadata."""
        metadata = {"model": "gemini-2.5-flash", "tokens": 150}
        response = AgentResponse(content="Test response", metadata=metadata)
        assert response.metadata == metadata

    def test_response_immutability(self) -> None:
        """Test that response is immutable."""
        response = AgentResponse(content="Test")
        with pytest.raises(AttributeError):
            response.content = "Modified"  # type: ignore

    def test_response_with_empty_content_raises_error(self) -> None:
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Response content cannot be empty"):
            AgentResponse(content="")


class TestConversationAgentModule:
    """Test the ConversationAgent DSPy module implementation."""

    @pytest.fixture
    def mock_dspy_lm(self) -> Mock:
        """Create a mock DSPy language model."""
        mock_lm = Mock()
        mock_lm.return_value = ["This is a test response from the LLM"]
        return mock_lm

    @pytest.fixture
    def sample_context_no_history(self) -> ConversationContext:
        """Create a sample context without history."""
        return ConversationContext(
            current_message="What is the capital of France?",
            metadata={"user_id": "test_user"},
        )

    @pytest.fixture
    def sample_context_with_history(self) -> ConversationContext:
        """Create a sample context with conversation history."""
        history = (
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi! How can I help you?"),
            Message(role="user", content="Tell me about Paris"),
            Message(role="assistant", content="Paris is the capital of France..."),
        )
        return ConversationContext(
            current_message="What is its population?",
            history=history,
            metadata={"user_id": "test_user"},
        )

    def test_agent_initialization(self) -> None:
        """Test that ConversationAgent can be initialized."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        agent = ConversationAgent()
        assert agent is not None

    def test_agent_implements_interface(self) -> None:
        """Test that ConversationAgent implements IConversationAgent."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent
        from src.application.interfaces.conversation_agent import IConversationAgent

        agent = ConversationAgent()
        assert isinstance(agent, IConversationAgent)

    def test_agent_configuration(self) -> None:
        """Test agent configuration with custom parameters."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        agent = ConversationAgent()
        agent.configure(temperature=0.5, max_tokens=500)
        # Configuration should be stored and applied
        assert agent.temperature == 0.5
        assert agent.max_tokens == 500

    def test_agent_configuration_with_invalid_temperature_raises_error(self) -> None:
        """Test that invalid temperature raises ValueError."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        agent = ConversationAgent()
        with pytest.raises(ValueError, match="temperature"):
            agent.configure(temperature=3.0)  # temperature must be 0.0-2.0

    def test_agent_configuration_with_invalid_max_tokens_raises_error(self) -> None:
        """Test that invalid max_tokens raises ValueError."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        agent = ConversationAgent()
        with pytest.raises(ValueError, match="max_tokens"):
            agent.configure(max_tokens=-100)  # max_tokens must be positive

    @patch("src.infrastructure.llm.conversation_agent.dspy")
    def test_generate_response_without_history(
        self, mock_dspy: Mock, sample_context_no_history: ConversationContext
    ) -> None:
        """Test generating response without conversation history."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        # Mock the DSPy prediction
        mock_prediction = Mock()
        mock_prediction.response = "Paris is the capital of France."
        mock_prediction.reasoning = "This is a well-known geographical fact."

        mock_dspy.LM = Mock()
        mock_dspy.ReAct = Mock(return_value=Mock(return_value=mock_prediction))
        mock_dspy.context = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))

        agent = ConversationAgent()
        response = agent.generate_response(sample_context_no_history)

        assert isinstance(response, AgentResponse)
        assert response.content == "Paris is the capital of France."
        assert response.reasoning == "This is a well-known geographical fact."

    @patch("src.infrastructure.llm.conversation_agent.dspy")
    def test_generate_response_with_history(
        self, mock_dspy: Mock, sample_context_with_history: ConversationContext
    ) -> None:
        """Test generating response with conversation history."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        # Mock the DSPy prediction
        mock_prediction = Mock()
        mock_prediction.response = (
            "The population of Paris is approximately 2.2 million in the city proper."
        )
        mock_prediction.reasoning = (
            "Based on the context about Paris, the user is asking about its population."
        )

        mock_dspy.LM = Mock()
        mock_dspy.ReAct = Mock(return_value=Mock(return_value=mock_prediction))
        mock_dspy.context = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))

        agent = ConversationAgent()
        response = agent.generate_response(sample_context_with_history)

        assert isinstance(response, AgentResponse)
        assert "population" in response.content.lower()
        assert response.reasoning is not None

    def test_generate_response_with_invalid_context_raises_error(self) -> None:
        """Test that invalid context raises ValueError."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        agent = ConversationAgent()
        with pytest.raises(ValueError):
            agent.generate_response(None)  # type: ignore

    @patch("src.infrastructure.llm.conversation_agent.dspy")
    def test_generate_response_handles_llm_failure(
        self, mock_dspy: Mock, sample_context_no_history: ConversationContext
    ) -> None:
        """Test that LLM failures are handled gracefully."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        # Mock DSPy components
        mock_dspy.LM = Mock()

        # Create a mock generator that raises an error when called
        mock_generator = Mock(side_effect=RuntimeError("LLM API error"))
        mock_dspy.ReAct = Mock(return_value=mock_generator)

        # Mock context manager properly - it should not swallow exceptions
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=None)
        mock_context.__exit__ = Mock(return_value=False)  # False = don't suppress exceptions
        mock_dspy.context = Mock(return_value=mock_context)

        agent = ConversationAgent()
        with pytest.raises(RuntimeError, match="LLM API error|Failed to generate response"):
            agent.generate_response(sample_context_no_history)

    def test_conversation_signature_structure(self) -> None:
        """Test that the DSPy signature is properly structured."""
        from src.infrastructure.llm.conversation_agent import ConversationSignature

        # Verify the signature has the required fields
        assert hasattr(ConversationSignature, "__annotations__")
        annotations = ConversationSignature.__annotations__

        # Check for expected input fields
        assert "current_message" in annotations
        assert "conversation_history" in annotations

        # Check for expected output fields
        assert "response" in annotations
        # Note: reasoning is added by dspy.ReAct, not the signature itself


class TestConversationSignature:
    """Test the Pydantic-based DSPy signature."""

    def test_signature_is_dspy_signature(self) -> None:
        """Test that ConversationSignature extends dspy.Signature."""
        from src.infrastructure.llm.conversation_agent import ConversationSignature
        import dspy

        assert issubclass(ConversationSignature, dspy.Signature)

    def test_signature_has_docstring(self) -> None:
        """Test that signature has proper documentation."""
        from src.infrastructure.llm.conversation_agent import ConversationSignature

        assert ConversationSignature.__doc__ is not None
        assert len(ConversationSignature.__doc__) > 0

    def test_signature_field_descriptions(self) -> None:
        """Test that signature fields have proper descriptions."""
        from src.infrastructure.llm.conversation_agent import ConversationSignature

        # Get field info from the signature class
        fields = ConversationSignature.model_fields

        # Verify input fields have descriptions
        assert "current_message" in fields
        assert "conversation_history" in fields

        # Verify output fields have descriptions
        assert "response" in fields
        # Note: reasoning is added by dspy.ReAct wrapper, not the signature


class TestToolsIntegration:
    """Test the tools integrated with ConversationAgent."""

    def test_compute_tool_exists(self) -> None:
        """Test that compute tool is available."""
        from src.infrastructure.llm.tools import compute

        assert compute is not None
        assert callable(compute)

    def test_jot_tool_exists(self) -> None:
        """Test that jot tool is available."""
        from src.infrastructure.llm.tools import jot

        assert jot is not None
        assert callable(jot)

    def test_compute_tool_basic_calculation(self) -> None:
        """Test compute tool with a basic calculation."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        # Note: This will fail without proper DSPy setup, but tests the interface
        result = compute("What is 2 + 2?")
        assert isinstance(result, str)

    def test_jot_tool_records_note(self) -> None:
        """Test jot tool records a note."""
        from src.infrastructure.llm.tools.thinking import jot

        note = "Planning to solve this in 3 steps"
        result = jot(note)
        assert note in result

    def test_jot_tool_rejects_empty_note(self) -> None:
        """Test jot tool rejects empty notes."""
        from src.infrastructure.llm.tools.thinking import jot

        result = jot("")
        assert "Error" in result
        assert "empty" in result.lower()

    def test_agent_has_tools_initialized(self) -> None:
        """Test that ConversationAgent initializes with tools."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        agent = ConversationAgent()
        # The agent should have tools registered
        assert hasattr(agent, "_generator")

    @patch("src.infrastructure.llm.conversation_agent.compute")
    @patch("src.infrastructure.llm.conversation_agent.jot")
    def test_agent_tools_are_registered(
        self, mock_jot: Mock, mock_compute: Mock
    ) -> None:
        """Test that tools are properly registered with the agent."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        # Mock the tools
        mock_compute.return_value = "42"
        mock_jot.return_value = "Note recorded"

        agent = ConversationAgent()
        # Tools should be available to the ReAct generator
        assert agent._generator is not None


class TestComputeTool:
    """Test the compute tool in detail."""

    def test_compute_tool_signature(self) -> None:
        """Test compute tool has correct signature."""
        from src.infrastructure.llm.tools.program_of_thought import ComputationSignature
        import dspy

        assert issubclass(ComputationSignature, dspy.Signature)

    def test_compute_tool_has_problem_field(self) -> None:
        """Test ComputationSignature has problem field."""
        from src.infrastructure.llm.tools.program_of_thought import ComputationSignature

        fields = ComputationSignature.model_fields
        assert "problem" in fields

    def test_compute_tool_has_result_field(self) -> None:
        """Test ComputationSignature has result field."""
        from src.infrastructure.llm.tools.program_of_thought import ComputationSignature

        fields = ComputationSignature.model_fields
        assert "result" in fields

    def test_compute_tool_has_documentation(self) -> None:
        """Test compute tool has proper documentation."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        assert compute.__doc__ is not None
        assert "statistical" in compute.__doc__.lower()
        assert "financial" in compute.__doc__.lower()
        assert "engineering" in compute.__doc__.lower()

    def test_compute_tool_callable(self) -> None:
        """Test that compute tool is callable."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        assert callable(compute)

    def test_compute_tool_returns_string(self) -> None:
        """Test that compute tool returns a string."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        result = compute("What is 2 + 2?")
        assert isinstance(result, str)

    @pytest.mark.skip(reason="Requires LLM configuration - integration test")
    def test_compute_simple_arithmetic(self) -> None:
        """Test compute with simple arithmetic."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        result = compute("Calculate 15 + 27")
        assert "42" in result

    @pytest.mark.skip(reason="Requires LLM configuration - integration test")
    def test_compute_statistical_analysis(self) -> None:
        """Test compute with statistical analysis."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        result = compute("Calculate the mean and standard deviation of [10, 20, 30, 40, 50]")
        assert "30" in result  # mean
        # Standard deviation should be present

    @pytest.mark.skip(reason="Requires LLM configuration - integration test")
    def test_compute_financial_calculation(self) -> None:
        """Test compute with financial calculations."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        result = compute(
            "Calculate the future value of $1000 invested at 5% annual interest for 10 years with annual compounding"
        )
        assert result  # Should contain the calculation result

    @pytest.mark.skip(reason="Requires LLM configuration - integration test")
    def test_compute_engineering_problem(self) -> None:
        """Test compute with engineering calculations."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        result = compute("Calculate the force required to accelerate a 50kg object at 2 m/s²")
        assert "100" in result  # F = ma = 50 * 2

    @pytest.mark.skip(reason="Requires LLM configuration - integration test")
    def test_compute_summation_series(self) -> None:
        """Test compute with summation series."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        result = compute("Calculate the sum of integers from 1 to 100")
        assert "5050" in result  # Sum formula: n(n+1)/2

    @pytest.mark.skip(reason="Requires LLM configuration - integration test")
    def test_compute_infinite_series(self) -> None:
        """Test compute with infinite series approximation."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        result = compute("Approximate the sum of the infinite series 1/2^n for n from 1 to 20")
        assert result  # Should converge to approximately 1

    @pytest.mark.skip(reason="Requires LLM configuration - integration test")
    def test_compute_calculus_derivative(self) -> None:
        """Test compute with calculus derivative."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        result = compute("Find the derivative of x^2 + 3x + 2 at x=5")
        assert result  # derivative is 2x + 3, at x=5 should be 13

    @pytest.mark.skip(reason="Requires LLM configuration - integration test")
    def test_compute_with_complex_expression(self) -> None:
        """Test compute with complex mathematical expression."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        result = compute("Calculate (25 * 4) + (100 / 5) - (10 ** 2)")
        assert result  # (100) + (20) - (100) = 20

    def test_compute_handles_error_gracefully(self) -> None:
        """Test that compute handles errors gracefully."""
        from src.infrastructure.llm.tools.program_of_thought import compute

        # Even with an error, should return a string (not raise)
        result = compute("This is not a valid computational problem!!@@##")
        assert isinstance(result, str)


class TestJotTool:
    """Test the jot tool in detail."""

    def test_jot_returns_recorded_note(self) -> None:
        """Test that jot returns the recorded note."""
        from src.infrastructure.llm.tools.thinking import jot

        test_note = "Step 1: Analyze the problem"
        result = jot(test_note)
        assert test_note in result

    def test_jot_handles_whitespace_only_note(self) -> None:
        """Test that jot rejects whitespace-only notes."""
        from src.infrastructure.llm.tools.thinking import jot

        result = jot("   ")
        assert "Error" in result

    def test_jot_has_documentation(self) -> None:
        """Test jot tool has proper documentation."""
        from src.infrastructure.llm.tools.thinking import jot

        assert jot.__doc__ is not None
        assert "multi-hop" in jot.__doc__.lower()
        assert "reasoning" in jot.__doc__.lower()

    def test_jot_callable(self) -> None:
        """Test that jot tool is callable."""
        from src.infrastructure.llm.tools.thinking import jot

        assert callable(jot)

    def test_jot_with_planning_note(self) -> None:
        """Test jot with a planning note."""
        from src.infrastructure.llm.tools.thinking import jot

        plan = "Plan: 1) Gather requirements 2) Design solution 3) Implement 4) Test"
        result = jot(plan)
        assert plan in result
        assert isinstance(result, str)

    def test_jot_with_intermediate_finding(self) -> None:
        """Test jot with intermediate findings."""
        from src.infrastructure.llm.tools.thinking import jot

        finding = "Found that variable X correlates with Y at 0.85 correlation coefficient"
        result = jot(finding)
        assert finding in result

    def test_jot_with_multi_hop_reasoning(self) -> None:
        """Test jot with multi-hop reasoning scenario."""
        from src.infrastructure.llm.tools.thinking import jot

        # Simulate multi-hop reasoning steps
        step1 = jot("Step 1: Identified that user needs data analysis")
        assert "Step 1" in step1

        step2 = jot("Step 2: Will use compute tool for statistical calculations")
        assert "Step 2" in step2

        step3 = jot("Step 3: Present results in user-friendly format")
        assert "Step 3" in step3

    def test_jot_with_hypothesis(self) -> None:
        """Test jot with hypothesis tracking."""
        from src.infrastructure.llm.tools.thinking import jot

        hypothesis = "Hypothesis: The performance issue is caused by N+1 query problem"
        result = jot(hypothesis)
        assert "Hypothesis" in result

    def test_jot_with_decision_point(self) -> None:
        """Test jot with decision points."""
        from src.infrastructure.llm.tools.thinking import jot

        decision = "Decision: Will use approach A instead of B because of lower complexity"
        result = jot(decision)
        assert "Decision" in result

    def test_jot_with_observation(self) -> None:
        """Test jot with observations."""
        from src.infrastructure.llm.tools.thinking import jot

        observation = "Observation: User prefers concise responses over detailed explanations"
        result = jot(observation)
        assert "Observation" in result

    def test_jot_empty_string_returns_error(self) -> None:
        """Test jot with empty string returns error."""
        from src.infrastructure.llm.tools.thinking import jot

        result = jot("")
        assert "Error" in result
        assert "empty" in result.lower()

    def test_jot_none_string_returns_error(self) -> None:
        """Test jot with whitespace returns error."""
        from src.infrastructure.llm.tools.thinking import jot

        result = jot("   \n\t  ")
        assert "Error" in result

    def test_jot_preserves_special_characters(self) -> None:
        """Test that jot preserves special characters."""
        from src.infrastructure.llm.tools.thinking import jot

        note = "Formula: f(x) = x^2 + 2x - 1 @ x=5 => result ≈ 34"
        result = jot(note)
        assert note in result

    def test_jot_preserves_newlines(self) -> None:
        """Test that jot preserves newlines in notes."""
        from src.infrastructure.llm.tools.thinking import jot

        note = "Multi-line plan:\n1. First step\n2. Second step\n3. Third step"
        result = jot(note)
        assert note in result

    def test_jot_with_long_note(self) -> None:
        """Test jot with a long note."""
        from src.infrastructure.llm.tools.thinking import jot

        long_note = "A" * 1000  # 1000 character note
        result = jot(long_note)
        assert long_note in result

    def test_jot_unicode_characters(self) -> None:
        """Test jot with unicode characters."""
        from src.infrastructure.llm.tools.thinking import jot

        note = "Plan: Analyze data 分析数据 📊 → Process → Report 报告"
        result = jot(note)
        assert note in result


class TestConversationAgentIntegration:
    """Integration tests for ConversationAgent (these will use actual DSPy if configured)."""

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires actual LLM configuration")
    def test_real_conversation_flow(self) -> None:
        """Test a real conversation flow with actual LLM."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        # This test would require actual DSPy configuration with a real LLM
        agent = ConversationAgent()

        # First message
        context1 = ConversationContext(current_message="Hello, what's your name?")
        response1 = agent.generate_response(context1)
        assert response1.content

        # Follow-up message with history
        history = (
            Message(role="user", content="Hello, what's your name?"),
            Message(role="assistant", content=response1.content),
        )
        context2 = ConversationContext(
            current_message="Can you help me with Python?",
            history=history,
        )
        response2 = agent.generate_response(context2)
        assert response2.content

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires actual LLM configuration")
    def test_conversation_with_computation(self) -> None:
        """Test conversation that requires computational tool."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        agent = ConversationAgent()

        context = ConversationContext(
            current_message="Calculate the mean of [10, 20, 30, 40, 50]"
        )
        response = agent.generate_response(context)

        # Should use the compute tool for this calculation
        assert response.content
        assert "30" in response.content  # Expected mean

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires actual LLM configuration")
    def test_conversation_with_multi_hop_reasoning(self) -> None:
        """Test conversation requiring multi-hop reasoning with jot tool."""
        from src.infrastructure.llm.conversation_agent import ConversationAgent

        agent = ConversationAgent()

        context = ConversationContext(
            current_message=(
                "I need to plan a project with 3 phases. "
                "Help me break it down step by step."
            )
        )
        response = agent.generate_response(context)

        # Should use jot tool to plan the breakdown
        assert response.content
        assert len(response.content) > 0
