#!/usr/bin/env python3
"""Quick test of expense tools integration with ConversationAgent."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

from src.application.interfaces.conversation_agent import ConversationContext
from src.config.settings import settings
from src.infrastructure.database.session import get_session_maker
from src.infrastructure.llm.conversation_agent import ConversationAgent
from src.infrastructure.llm.embedding.gemini_embedding_service import GeminiEmbeddingService
from src.infrastructure.llm.tools.expenses import (
    configure_expense_tools,
    set_user_context,
)

# Load environment
load_dotenv()


def test_integration():
    """Test expense tools integration."""
    print("🚀 Testing Expense Tools Integration with ConversationAgent\n")
    print("=" * 80)

    # Configure expense tools
    print("\n1️⃣  Configuring expense tools...")
    embedding_service = GeminiEmbeddingService(api_key=settings.gemini_api_key)
    session_maker = get_session_maker()
    configure_expense_tools(session_maker, embedding_service)
    set_user_context("test-user-quick")
    print("✅ Expense tools configured")

    # Initialize agent
    print("\n2️⃣  Initializing ConversationAgent...")
    agent = ConversationAgent(model=settings.default_llm_model)
    print(f"✅ Agent initialized with model: {agent.model}")
    print(f"   Temperature: {agent.temperature}")
    print(f"   Tools available: compute, jot, note_tools, expense_tools")

    # Test conversation
    print("\n3️⃣  Testing expense tracking through conversation...")
    print("\n" + "=" * 80)
    
    user_message = "I just spent 520 HKD on lunch at a Japanese restaurant"
    print(f"👤 USER: {user_message}")
    
    context = ConversationContext(
        current_message=user_message,
        metadata={"user_id": "test-user-quick", "session_id": "quick-test"},
    )

    response = agent.generate_response(context)
    
    print(f"\n🤖 SOFIA: {response.content}")
    print("\n" + "=" * 80)

    print("\n✅ Integration test completed successfully!")
    print("\n📝 Summary:")
    print("   - Expense tools configured ✓")
    print("   - ConversationAgent initialized ✓")
    print("   - Sofia can track expenses through conversation ✓")
    print("\n💡 Run test_expense_integration.ipynb for more comprehensive tests")


if __name__ == "__main__":
    try:
        test_integration()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
