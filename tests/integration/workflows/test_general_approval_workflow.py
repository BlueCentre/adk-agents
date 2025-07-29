"""Integration tests for the general purpose approval workflow pattern (Milestone 3.2)."""

from unittest.mock import MagicMock, patch

from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools import ToolContext
import pytest

from agents.software_engineer.enhanced_agent import (
    workflow_execution_tool,
    workflow_selector_tool,
)
from agents.software_engineer.workflows.human_in_loop_workflows import (
    create_architecture_proposal,
    create_deployment_proposal,
    create_file_edit_proposal,
    create_generic_proposal,
    create_human_approval_workflow,
    create_multi_step_proposal,
    create_security_proposal,
    setup_approval_proposal,
)


class TestHumanApprovalWorkflow:
    """Test the HumanApprovalWorkflow class and its functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock invocation context for testing."""
        context = MagicMock(spec=InvocationContext)
        context.state = {}
        return context

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context for testing."""
        context = MagicMock(spec=ToolContext)
        context.state = {}
        return context

    @pytest.fixture
    def approval_workflow(self):
        """Create a HumanApprovalWorkflow instance for testing."""
        return create_human_approval_workflow()

    def test_human_approval_workflow_creation(self, approval_workflow):
        """Test that HumanApprovalWorkflow can be created successfully."""
        assert approval_workflow is not None
        assert approval_workflow.name == "human_approval_workflow"
        assert "approval_workflow" in approval_workflow.output_key

    @pytest.mark.asyncio
    async def test_human_approval_workflow_run_no_proposal(self, approval_workflow, mock_context):
        """Test workflow behavior when no proposal is provided."""
        # Arrange
        mock_context.state = {}

        # Act
        events = []
        async for event in approval_workflow.run(mock_context):
            events.append(event)

        # Assert
        assert len(events) == 1
        assert events[0].author == "human_approval_workflow"
        assert "No proposal found" in events[0].content.parts[0].text

    def test_file_edit_proposal_presentation(self, approval_workflow):
        """Test file edit proposal presentation generation."""
        # Arrange
        proposal = {
            "type": "file_edit",
            "proposed_filepath": "test.py",
            "proposed_content": "def hello(): return 'world'",
            "diff": "+def hello(): return 'world'",
            "impact_analysis": "Low impact change - adds new function",
        }

        # Act
        presentation = approval_workflow._generate_proposal_presentation(proposal)

        # Assert
        assert "📝 File Edit Proposal" in presentation
        assert "test.py" in presentation
        assert "def hello(): return 'world'" in presentation
        assert "+def hello(): return 'world'" in presentation
        assert "Low impact change" in presentation

    def test_deployment_proposal_presentation(self, approval_workflow):
        """Test deployment proposal presentation generation."""
        # Arrange
        proposal = {
            "type": "deployment",
            "environment": "production",
            "deployment_steps": [
                "Build application",
                "Run tests",
                "Deploy to production",
            ],
            "rollback_plan": "Restore previous version from backup",
            "risks": ["Potential downtime", "Database migration required"],
        }

        # Act
        presentation = approval_workflow._generate_proposal_presentation(proposal)

        # Assert
        assert "🚀 Deployment Proposal" in presentation
        assert "production" in presentation
        assert "Build application" in presentation
        assert "Run tests" in presentation
        assert "Deploy to production" in presentation
        assert "Restore previous version" in presentation
        assert "Potential downtime" in presentation
        assert "Database migration required" in presentation

    def test_architecture_proposal_presentation(self, approval_workflow):
        """Test architecture change proposal presentation generation."""
        # Arrange
        proposal = {
            "type": "architecture_change",
            "change_description": "Migrate from monolith to microservices",
            "affected_components": ["User Service", "Payment Service", "Database"],
            "trade_offs": "Increased complexity but better scalability",
        }

        # Act
        presentation = approval_workflow._generate_proposal_presentation(proposal)

        # Assert
        assert "🏗️ Architecture Change Proposal" in presentation
        assert "monolith to microservices" in presentation
        assert "User Service" in presentation
        assert "Payment Service" in presentation
        assert "Database" in presentation
        assert "Increased complexity but better scalability" in presentation

    def test_security_proposal_presentation(self, approval_workflow):
        """Test security operation proposal presentation generation."""
        # Arrange
        proposal = {
            "type": "security_operation",
            "operation_type": "Privilege Escalation",
            "security_implications": "Grants admin access to production systems",
            "access_changes": ["Add user to admin group", "Grant database access"],
        }

        # Act
        presentation = approval_workflow._generate_proposal_presentation(proposal)

        # Assert
        assert "🔒 Security Operation Proposal" in presentation
        assert "Privilege Escalation" in presentation
        assert "Grants admin access" in presentation
        assert "Add user to admin group" in presentation
        assert "Grant database access" in presentation

    def test_multi_step_proposal_presentation(self, approval_workflow):
        """Test multi-step plan proposal presentation generation."""
        # Arrange
        proposal = {
            "type": "multi_step_plan",
            "plan_description": "Complete system migration to new infrastructure",
            "steps": [
                "Backup current system",
                "Set up new infrastructure",
                "Migrate data",
                "Switch traffic",
                "Verify functionality",
            ],
            "estimated_duration": "4-6 hours",
        }

        # Act
        presentation = approval_workflow._generate_proposal_presentation(proposal)

        # Assert
        assert "📋 Multi-Step Plan Proposal" in presentation
        assert "Complete system migration" in presentation
        assert "Backup current system" in presentation
        assert "Set up new infrastructure" in presentation
        assert "Migrate data" in presentation
        assert "4-6 hours" in presentation

    def test_generic_proposal_presentation(self, approval_workflow):
        """Test generic proposal presentation generation."""
        # Arrange
        proposal = {
            "type": "generic",
            "title": "Critical System Change",
            "description": "This change requires careful review",
            "details": "Additional implementation details here",
        }

        # Act
        presentation = approval_workflow._generate_proposal_presentation(proposal)

        # Assert
        assert "📄 Action Proposal" in presentation
        assert "Critical System Change" in presentation
        assert "This change requires careful review" in presentation
        assert "Additional implementation details" in presentation


class TestProposalCreationHelpers:
    """Test the proposal creation helper functions."""

    def test_create_file_edit_proposal(self):
        """Test file edit proposal creation."""
        proposal = create_file_edit_proposal(
            filepath="example.py",
            content="print('hello')",
            diff="+print('hello')",
            impact_analysis="Low impact test change",
        )

        assert proposal["type"] == "file_edit"
        assert proposal["proposed_filepath"] == "example.py"
        assert proposal["proposed_content"] == "print('hello')"
        assert proposal["diff"] == "+print('hello')"
        assert proposal["impact_analysis"] == "Low impact test change"

    def test_create_deployment_proposal(self):
        """Test deployment proposal creation."""
        proposal = create_deployment_proposal(
            environment="staging",
            deployment_steps=["Build", "Test", "Deploy"],
            rollback_plan="Revert to previous version",
            risks=["Brief downtime"],
        )

        assert proposal["type"] == "deployment"
        assert proposal["environment"] == "staging"
        assert proposal["deployment_steps"] == ["Build", "Test", "Deploy"]
        assert proposal["rollback_plan"] == "Revert to previous version"
        assert proposal["risks"] == ["Brief downtime"]

    def test_create_architecture_proposal(self):
        """Test architecture proposal creation."""
        proposal = create_architecture_proposal(
            change_description="Add caching layer",
            affected_components=["API", "Database"],
            trade_offs="Faster responses but more complexity",
        )

        assert proposal["type"] == "architecture_change"
        assert proposal["change_description"] == "Add caching layer"
        assert proposal["affected_components"] == ["API", "Database"]
        assert proposal["trade_offs"] == "Faster responses but more complexity"

    def test_create_security_proposal(self):
        """Test security proposal creation."""
        proposal = create_security_proposal(
            operation_type="Access Grant",
            security_implications="Grants elevated privileges",
            access_changes=["Add to security group"],
        )

        assert proposal["type"] == "security_operation"
        assert proposal["operation_type"] == "Access Grant"
        assert proposal["security_implications"] == "Grants elevated privileges"
        assert proposal["access_changes"] == ["Add to security group"]

    def test_create_multi_step_proposal(self):
        """Test multi-step proposal creation."""
        proposal = create_multi_step_proposal(
            plan_description="Database migration plan",
            steps=["Backup", "Migrate", "Verify"],
            estimated_duration="2 hours",
        )

        assert proposal["type"] == "multi_step_plan"
        assert proposal["plan_description"] == "Database migration plan"
        assert proposal["steps"] == ["Backup", "Migrate", "Verify"]
        assert proposal["estimated_duration"] == "2 hours"

    def test_create_generic_proposal(self):
        """Test generic proposal creation."""
        proposal = create_generic_proposal(
            title="Test Action",
            description="This is a test action",
            details="Additional details",
        )

        assert proposal["type"] == "generic"
        assert proposal["title"] == "Test Action"
        assert proposal["description"] == "This is a test action"
        assert proposal["details"] == "Additional details"


class TestWorkflowIntegration:
    """Test integration with workflow_selector_tool and workflow_execution_tool."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context for testing."""
        context = MagicMock(spec=ToolContext)
        context.state = {}
        return context

    def test_workflow_selector_detects_approval_requirement(self, mock_tool_context):
        """Test that workflow_selector_tool correctly identifies tasks requiring approval."""
        # Test deployment scenario
        result = workflow_selector_tool(
            tool_context=mock_tool_context,
            task_description="Deploy the application to production environment",
        )

        assert result["selected_workflow"] == "human_in_loop"
        assert result["task_characteristics"]["requires_approval"] is True
        assert result["task_characteristics"]["task_type"] == "deployment"

        # Test security scenario
        result = workflow_selector_tool(
            tool_context=mock_tool_context,
            task_description="Grant critical security permissions to user",
        )

        assert result["selected_workflow"] == "human_in_loop"
        assert result["task_characteristics"]["requires_approval"] is True

    def test_workflow_selector_normal_tasks(self, mock_tool_context):
        """Test that workflow_selector_tool correctly identifies non-approval tasks."""
        result = workflow_selector_tool(
            tool_context=mock_tool_context, task_description="Review code for potential bugs"
        )

        assert result["selected_workflow"] != "human_in_loop"
        assert result["task_characteristics"]["requires_approval"] is False

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    @patch("builtins.print")
    def test_workflow_execution_human_approval_approved(
        self, _mock_print, mock_approval, mock_tool_context
    ):
        """Test successful execution of human approval workflow with approval."""
        # Arrange
        mock_approval.return_value = True

        proposal_data = create_deployment_proposal(
            environment="production",
            deployment_steps=["Build app", "Deploy"],
        )

        # Act
        result = workflow_execution_tool(
            tool_context=mock_tool_context,
            workflow_type="human_in_loop",
            task_description="Deploy to production",
            proposal_data=proposal_data,
        )

        # Assert
        assert result["status"] == "completed"
        assert result["workflow_type"] == "human_in_loop"
        assert result["approved"] is True
        assert result["proposal_type"] == "deployment"
        assert result["next_step"] == "execute_approved_action"
        assert mock_tool_context.state["last_approval_outcome"] == "approved"
        assert mock_tool_context.state["workflow_state"] == "approval_completed"

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    @patch("builtins.print")
    def test_workflow_execution_human_approval_rejected(
        self, _mock_print, mock_approval, mock_tool_context
    ):
        """Test execution of human approval workflow with rejection."""
        # Arrange
        mock_approval.return_value = False

        proposal_data = create_security_proposal(
            operation_type="Admin Access",
            security_implications="Grants full system access",
        )

        # Act
        result = workflow_execution_tool(
            tool_context=mock_tool_context,
            workflow_type="human_in_loop",
            task_description="Grant admin access",
            proposal_data=proposal_data,
        )

        # Assert
        assert result["status"] == "completed"
        assert result["workflow_type"] == "human_in_loop"
        assert result["approved"] is False
        assert result["proposal_type"] == "security_operation"
        assert result["next_step"] == "handle_rejection"
        assert mock_tool_context.state["last_approval_outcome"] == "rejected"

    @patch("builtins.print")
    def test_workflow_execution_no_proposal_data(self, _mock_print, mock_tool_context):
        """Test execution with no proposal data creates generic proposal."""
        # Act
        with patch(
            "agents.software_engineer.enhanced_agent.human_in_the_loop_approval"
        ) as mock_approval:
            mock_approval.return_value = True

            result = workflow_execution_tool(
                tool_context=mock_tool_context,
                workflow_type="human_in_loop",
                task_description="Critical system change",
            )

        # Assert
        assert result["status"] == "completed"
        assert result["proposal_type"] == "generic"
        assert "pending_proposal" in mock_tool_context.state
        proposal = mock_tool_context.state["pending_proposal"]
        assert proposal["type"] == "generic"
        assert "Critical system change" in proposal["title"]

    def test_workflow_execution_unknown_workflow(self, mock_tool_context):
        """Test handling of unknown workflow types."""
        result = workflow_execution_tool(
            tool_context=mock_tool_context,
            workflow_type="unknown_workflow",
            task_description="Some task",
        )

        assert result["status"] == "error"
        assert "Unknown workflow type" in result["message"]
        assert result["workflow_type"] == "unknown_workflow"


class TestEndToEndWorkflow:
    """End-to-end integration tests simulating real usage scenarios."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context for testing."""
        context = MagicMock(spec=ToolContext)
        context.state = {}
        return context

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    @patch("builtins.print")
    def test_deployment_approval_workflow_end_to_end(
        self, _mock_print, mock_approval, mock_tool_context
    ):
        """Test complete deployment approval workflow from selection to execution."""
        # Arrange
        mock_approval.return_value = True
        task_description = "Deploy version 2.0 to production environment"

        # Step 1: Workflow selection
        workflow_selection = workflow_selector_tool(
            tool_context=mock_tool_context, task_description=task_description
        )

        # Step 2: Create deployment proposal
        proposal_data = create_deployment_proposal(
            environment="production",
            deployment_steps=[
                "Build version 2.0",
                "Run integration tests",
                "Deploy to production",
                "Verify deployment",
            ],
            rollback_plan="Rollback to version 1.9 if issues occur",
            risks=["Brief service interruption", "Potential data migration issues"],
        )

        # Step 3: Execute approval workflow
        execution_result = workflow_execution_tool(
            tool_context=mock_tool_context,
            workflow_type=workflow_selection["selected_workflow"],
            task_description=task_description,
            proposal_data=proposal_data,
        )

        # Assert workflow selection
        assert workflow_selection["selected_workflow"] == "human_in_loop"
        assert workflow_selection["task_characteristics"]["requires_approval"] is True
        assert workflow_selection["task_characteristics"]["task_type"] == "deployment"

        # Assert workflow execution
        assert execution_result["status"] == "completed"
        assert execution_result["approved"] is True
        assert execution_result["workflow_type"] == "human_in_loop"
        assert execution_result["proposal_type"] == "deployment"

        # Assert state changes
        assert mock_tool_context.state["workflow_state"] == "approval_completed"
        assert mock_tool_context.state["last_approval_outcome"] == "approved"
        assert mock_tool_context.state["workflow_next_step"] == "execute_approved_action"

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    @patch("builtins.print")
    def test_architecture_review_workflow_end_to_end(
        self, _mock_print, mock_approval, mock_tool_context
    ):
        """Test complete architecture review workflow with rejection scenario."""
        # Arrange
        mock_approval.return_value = False
        task_description = "Redesign the database architecture for better performance"

        # Step 1: Workflow selection (architecture changes should trigger approval)
        workflow_selection = workflow_selector_tool(
            tool_context=mock_tool_context, task_description=task_description
        )

        # Step 2: Create architecture proposal
        proposal_data = create_architecture_proposal(
            change_description="Migrate from relational to NoSQL database",
            affected_components=[
                "User Management Service",
                "Data Access Layer",
                "Reporting System",
                "API Gateway",
            ],
            trade_offs="Better performance and scalability but requires significant refactoring",
        )

        # Step 3: Execute approval workflow
        execution_result = workflow_execution_tool(
            tool_context=mock_tool_context,
            workflow_type=workflow_selection["selected_workflow"],
            task_description=task_description,
            proposal_data=proposal_data,
        )

        # Assert workflow selection
        assert workflow_selection["selected_workflow"] == "human_in_loop"
        assert workflow_selection["task_characteristics"]["complexity"] == "high"

        # Assert workflow execution (rejected)
        assert execution_result["status"] == "completed"
        assert execution_result["approved"] is False
        assert execution_result["proposal_type"] == "architecture_change"
        assert execution_result["next_step"] == "handle_rejection"

        # Assert state changes
        assert mock_tool_context.state["last_approval_outcome"] == "rejected"

    def test_setup_approval_proposal_function(self):
        """Test the setup_approval_proposal helper function."""
        # Arrange
        mock_context = MagicMock(spec=InvocationContext)
        mock_context.state = {}

        proposal_data = create_multi_step_proposal(
            plan_description="System maintenance plan",
            steps=["Stop services", "Update system", "Restart services"],
        )

        # Act
        setup_approval_proposal(proposal_data, mock_context)

        # Assert
        assert mock_context.state["pending_proposal"] == proposal_data
        assert mock_context.state["workflow_state"] == "awaiting_approval"


# User verification test scenarios
class TestUserVerificationScenarios:
    """Tests that match the user verification steps from the milestone."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context for testing."""
        context = MagicMock(spec=ToolContext)
        context.state = {}
        return context

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    @patch("builtins.print")
    def test_user_verification_deployment_approval(
        self, _mock_print, mock_approval, mock_tool_context
    ):
        """Test deployment task approval scenario for user verification."""
        # Simulate: Ask the agent to perform a deployment task
        mock_approval.return_value = True

        task_description = "Propose a new architecture for the database"

        # Workflow should be selected as human_in_loop
        workflow_selection = workflow_selector_tool(
            tool_context=mock_tool_context, task_description=task_description
        )

        # Create architecture proposal
        proposal_data = create_architecture_proposal(
            change_description="Implement microservices architecture",
            affected_components=["Database", "API", "Frontend"],
            trade_offs="Better scalability but increased complexity",
        )

        # Execute workflow
        result = workflow_execution_tool(
            tool_context=mock_tool_context,
            workflow_type=workflow_selection["selected_workflow"],
            task_description=task_description,
            proposal_data=proposal_data,
        )

        # Verify: Agent presents detailed proposal and requests approval
        assert workflow_selection["selected_workflow"] == "human_in_loop"
        assert result["status"] == "completed"
        assert result["approved"] is True

        # Verify: Agent indicates it is proceeding with approved plan
        assert result["next_step"] == "execute_approved_action"

    @patch("agents.software_engineer.enhanced_agent.human_in_the_loop_approval")
    @patch("builtins.print")
    def test_user_verification_rejection_scenario(
        self, _mock_print, mock_approval, mock_tool_context
    ):
        """Test rejection scenario for user verification."""
        # Simulate: User rejects the proposal
        mock_approval.return_value = False

        task_description = "Deploy critical security updates to production"

        # Execute deployment workflow
        proposal_data = create_deployment_proposal(
            environment="production",
            deployment_steps=["Apply security patches", "Restart services"],
            risks=["Service interruption during restart"],
        )

        result = workflow_execution_tool(
            tool_context=mock_tool_context,
            workflow_type="human_in_loop",
            task_description=task_description,
            proposal_data=proposal_data,
        )

        # Verify: Agent indicates the plan was cancelled
        assert result["approved"] is False
        assert result["next_step"] == "handle_rejection"
        assert mock_tool_context.state["last_approval_outcome"] == "rejected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
