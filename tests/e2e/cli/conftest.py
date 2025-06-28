import pytest
from unittest.mock import AsyncMock, MagicMock

from google.adk.sessions.session import Session
from google.adk.agents.llm_agent import LlmAgent


@pytest.fixture
def mock_services():
  """Create mock services for testing."""
  artifact_service = MagicMock()
  session_service = AsyncMock()
  credential_service = MagicMock()

  # Create a mock session
  mock_session = MagicMock(spec=Session)
  mock_session.id = "test_session_id"
  mock_session.user_id = "test_user"
  mock_session.app_name = "test_agent"
  mock_session.events = []

  session_service.create_session.return_value = mock_session
  session_service.get_session.return_value = mock_session
  session_service.append_event.return_value = None

  return artifact_service, session_service, credential_service, mock_session


@pytest.fixture
def mock_agent():
  """Create a mock agent for testing."""
  agent = MagicMock(spec=LlmAgent)
  agent.name = "test_agent"
  agent.description = "A test agent"
  agent.model = "test-model"
  agent.tools = []
  return agent


@pytest.fixture
def mock_runner():
  """Create a mock runner for testing."""
  runner = AsyncMock()

  # Mock response event
  mock_event = MagicMock()
  mock_event.author = "assistant"
  mock_event.content = MagicMock()
  mock_event.content.parts = [MagicMock()]
  mock_event.content.parts[0].text = "Test response"
  mock_event.content.parts[0].thought = False
  mock_event.usage_metadata = None

  async def async_gen():
    yield mock_event

  # Set run_async to return the actual async generator, not a coroutine
  runner.run_async.return_value = async_gen()

  return runner
