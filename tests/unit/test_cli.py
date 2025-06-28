"""
Tests for cli.py module to ensure comprehensive code coverage.
"""

import json
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import mock_open
from unittest.mock import patch

from pydantic import ValidationError
import pytest

from src.wrapper.adk.cli.cli import InputFile
from src.wrapper.adk.cli.cli import run_cli
from src.wrapper.adk.cli.cli import run_input_file


class TestInputFile:
  """Test the InputFile Pydantic model."""

  def test_valid_input_file(self):
    """Test that a valid input file passes validation."""
    valid_data = {
        'queries': ['What is the weather?', 'Tell me a joke'],
        'state': {'user_id': '123', 'session': 'abc'},
    }
    input_file = InputFile(**valid_data)
    assert input_file.queries == ['What is the weather?', 'Tell me a joke']
    assert input_file.state == {'user_id': '123', 'session': 'abc'}

  def test_missing_queries(self):
    """Test that missing queries raises validation error."""
    invalid_data = {'state': {'user_id': '123'}}
    with pytest.raises(ValidationError):
      InputFile(**invalid_data)

  def test_invalid_queries_type(self):
    """Test that invalid queries type raises validation error."""
    invalid_data = {'queries': 'not a list', 'state': {}}
    with pytest.raises(ValidationError):
      InputFile(**invalid_data)

  def test_required_state(self):
    """Test that state is required when not provided."""
    invalid_data = {'queries': ['What is the weather?']}
    with pytest.raises(ValidationError):
      InputFile(**invalid_data)

  def test_empty_state_allowed(self):
    """Test that empty state dict is allowed."""
    valid_data = {'queries': ['What is the weather?'], 'state': {}}
    input_file = InputFile(**valid_data)
    assert input_file.queries == ['What is the weather?']
    assert input_file.state == {}


class TestRunInputFile:
  """Test the run_input_file function."""

  @pytest.mark.asyncio
  @patch(
      'builtins.open',
      new_callable=mock_open,
      read_data='{"queries": ["test query"], "state": {}}',
  )
  @patch('src.wrapper.adk.cli.cli.Runner')
  @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
  async def test_run_input_file_success(
      self, mock_close_runner, mock_runner_class, mock_file
  ):
    """Test successful execution of run_input_file."""
    # Mock services
    mock_session = Mock()
    mock_session.app_name = 'test_app'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'
    mock_session_service = Mock()
    mock_session_service.create_session = AsyncMock(return_value=mock_session)

    # Mock agent
    mock_agent = Mock()
    mock_agent.name = 'TestAgent'

    # Mock runner
    mock_runner = Mock()
    mock_runner_class.return_value = mock_runner

    # Mock async generator for runner.run_async
    async def mock_run_async(*args, **kwargs):
      mock_event = Mock()
      mock_event.author = 'assistant'
      mock_event.content = Mock()
      mock_part = Mock()
      mock_part.text = 'Test response'
      mock_part.thought = False
      mock_event.content.parts = [mock_part]
      mock_event.usage_metadata = Mock()
      mock_event.usage_metadata.prompt_token_count = 10
      mock_event.usage_metadata.candidates_token_count = 20
      mock_event.usage_metadata.total_token_count = 30
      yield mock_event

    mock_runner.run_async = mock_run_async

    result = await run_input_file(
        root_agent=mock_agent,
        artifact_service=Mock(),
        session_service=mock_session_service,
        credential_service=Mock(),
        app_name='test_app',
        user_id='test_user',
        input_path='/path/to/input.json',
    )

    # Verify file was opened
    mock_file.assert_called_once_with(
        '/path/to/input.json', 'r', encoding='utf-8'
    )

    # Verify session was created
    mock_session_service.create_session.assert_called_once()

    # Verify result
    assert result == mock_session

  @pytest.mark.asyncio
  async def test_run_input_file_missing_file(self):
    """Test run_input_file with missing file."""
    with patch('builtins.open', side_effect=FileNotFoundError()):
      with pytest.raises(FileNotFoundError):
        await run_input_file(
            root_agent=Mock(),
            artifact_service=Mock(),
            session_service=Mock(),
            credential_service=Mock(),
            app_name='test_app',
            user_id='test_user',
            input_path='/nonexistent/path.json',
        )

  @pytest.mark.asyncio
  async def test_run_input_file_invalid_json(self):
    """Test run_input_file with invalid JSON."""
    with patch(
        'builtins.open', new_callable=mock_open, read_data='invalid json'
    ):
      with pytest.raises(ValidationError):
        await run_input_file(
            root_agent=Mock(),
            artifact_service=Mock(),
            session_service=Mock(),
            credential_service=Mock(),
            app_name='test_app',
            user_id='test_user',
            input_path='/path/to/invalid.json',
        )

  @pytest.mark.asyncio
  async def test_run_input_file_validation_error(self):
    """Test run_input_file with validation error."""
    with patch(
        'builtins.open', new_callable=mock_open, read_data='{"invalid": "data"}'
    ):
      with pytest.raises(ValidationError):
        await run_input_file(
            root_agent=Mock(),
            artifact_service=Mock(),
            session_service=Mock(),
            credential_service=Mock(),
            app_name='test_app',
            user_id='test_user',
            input_path='/path/to/invalid.json',
        )


class TestRunCli:
  """Test the run_cli function."""

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent')
  @patch('src.wrapper.adk.cli.cli.AgentLoader')
  @patch('src.wrapper.adk.cli.cli.InMemorySessionService')
  @patch('src.wrapper.adk.cli.cli.InMemoryArtifactService')
  @patch('src.wrapper.adk.cli.cli.InMemoryCredentialService')
  @patch('src.wrapper.adk.cli.cli.run_input_file')
  async def test_run_cli_with_input_file(
      self,
      mock_run_input_file,
      mock_credential_service_class,
      mock_artifact_service_class,
      mock_session_service_class,
      mock_agent_loader_class,
      mock_load_dotenv,
  ):
    """Test run_cli with input file."""
    # Setup mocks
    mock_session = Mock()
    mock_session.app_name = 'test_agent'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'

    mock_session_service = Mock()
    mock_session_service.create_session = AsyncMock(return_value=mock_session)
    mock_session_service_class.return_value = mock_session_service

    mock_artifact_service = Mock()
    mock_artifact_service_class.return_value = mock_artifact_service

    mock_credential_service = Mock()
    mock_credential_service_class.return_value = mock_credential_service

    mock_agent = Mock()
    mock_agent.name = 'TestAgent'
    mock_agent_loader = Mock()
    mock_agent_loader.load_agent.return_value = mock_agent
    mock_agent_loader_class.return_value = mock_agent_loader

    mock_run_input_file.return_value = mock_session

    await run_cli(
        agent_module_name='test_agent',
        input_file='/path/to/input.json',
    )

    # Verify environment loading
    mock_load_dotenv.assert_called_once_with('test_agent')

    # Verify agent loading
    mock_agent_loader.load_agent.assert_called_once_with('test_agent')

    # Verify input file processing
    mock_run_input_file.assert_called_once()
    call_args = mock_run_input_file.call_args
    assert call_args[1]['app_name'] == 'test_agent'
    assert call_args[1]['user_id'] == 'test_user'
    assert call_args[1]['input_path'] == '/path/to/input.json'

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent')
  @patch('src.wrapper.adk.cli.cli.AgentLoader')
  @patch('src.wrapper.adk.cli.cli.InMemorySessionService')
  @patch('src.wrapper.adk.cli.cli.InMemoryArtifactService')
  @patch('src.wrapper.adk.cli.cli.InMemoryCredentialService')
  @patch('src.wrapper.adk.cli.cli.run_interactively_with_tui')
  @patch('src.wrapper.adk.cli.cli.click.echo')
  async def test_run_cli_tui_mode(
      self,
      mock_echo,
      mock_run_tui,
      mock_credential_service_class,
      mock_artifact_service_class,
      mock_session_service_class,
      mock_agent_loader_class,
      mock_load_dotenv,
  ):
    """Test run_cli with TUI mode."""
    # Setup mocks
    mock_session = Mock()
    mock_session.app_name = 'test_agent'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'

    mock_session_service = Mock()
    mock_session_service.create_session = AsyncMock(return_value=mock_session)
    mock_session_service_class.return_value = mock_session_service

    mock_artifact_service = Mock()
    mock_artifact_service_class.return_value = mock_artifact_service

    mock_credential_service = Mock()
    mock_credential_service_class.return_value = mock_credential_service

    mock_agent = Mock()
    mock_agent.name = 'TestAgent'
    mock_agent_loader = Mock()
    mock_agent_loader.load_agent.return_value = mock_agent
    mock_agent_loader_class.return_value = mock_agent_loader

    await run_cli(
        agent_module_name='test_agent',
        tui=True,
        ui_theme='dark',
    )

    # Verify TUI was called
    mock_run_tui.assert_called_once()
    call_args = mock_run_tui.call_args
    assert call_args[1]['ui_theme'] == 'dark'

    # Verify welcome message
    mock_echo.assert_called_with('Running agent TestAgent, type exit to exit.')


class TestRunCliIntegration:
  """Integration tests for run_cli function with error scenarios."""

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent')
  @patch('src.wrapper.adk.cli.cli.AgentLoader')
  async def test_run_cli_agent_load_error(
      self, mock_agent_loader_class, mock_load_dotenv
  ):
    """Test run_cli when agent loading fails."""
    mock_agent_loader = Mock()
    mock_agent_loader.load_agent.side_effect = Exception('Agent not found')
    mock_agent_loader_class.return_value = mock_agent_loader

    with pytest.raises(Exception, match='Agent not found'):
      await run_cli(agent_module_name='nonexistent_agent')

    # Agent loading happens before load_dotenv, so when it fails,
    # load_dotenv is never called
    mock_load_dotenv.assert_not_called()
    mock_agent_loader.load_agent.assert_called_once_with('nonexistent_agent')

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent')
  @patch('src.wrapper.adk.cli.cli.AgentLoader')
  @patch('src.wrapper.adk.cli.cli.InMemorySessionService')
  @patch('src.wrapper.adk.cli.cli.InMemoryArtifactService')
  @patch('src.wrapper.adk.cli.cli.InMemoryCredentialService')
  @patch('src.wrapper.adk.cli.cli.run_interactively')
  @patch('builtins.open', new_callable=mock_open)
  @patch('builtins.input', return_value='test_session_id')
  @patch('builtins.print')
  async def test_run_cli_with_session_saving(
      self,
      mock_print,
      mock_input,
      mock_file,
      mock_run_interactively,
      mock_credential_service_class,
      mock_artifact_service_class,
      mock_session_service_class,
      mock_agent_loader_class,
      mock_load_dotenv,
  ):
    """Test run_cli with session saving enabled."""
    # Setup mocks
    mock_session = Mock()
    mock_session.app_name = 'test_agent'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'
    mock_session.model_dump_json = Mock(return_value='{"session": "data"}')

    mock_session_service = Mock()
    mock_session_service.create_session = AsyncMock(return_value=mock_session)
    mock_session_service.get_session = AsyncMock(return_value=mock_session)
    mock_session_service_class.return_value = mock_session_service

    mock_artifact_service = Mock()
    mock_artifact_service_class.return_value = mock_artifact_service

    mock_credential_service = Mock()
    mock_credential_service_class.return_value = mock_credential_service

    mock_agent = Mock()
    mock_agent.name = 'TestAgent'
    mock_agent_loader = Mock()
    mock_agent_loader.load_agent.return_value = mock_agent
    mock_agent_loader_class.return_value = mock_agent_loader

    await run_cli(
        agent_module_name='test_agent',
        save_session=True,
    )

    # Verify session was saved
    mock_input.assert_called_once_with('Session ID to save: ')
    mock_file.assert_called_once_with(
        'test_session_id.session.json', 'w', encoding='utf-8'
    )
    mock_file().write.assert_called_once_with('{"session": "data"}')
    mock_print.assert_called_with(
        'Session saved to', 'test_session_id.session.json'
    )

    # Verify session was fetched for saving
    mock_session_service.get_session.assert_called_once_with(
        app_name='test_agent',
        user_id='test_user',
        session_id='test_session',
    )
