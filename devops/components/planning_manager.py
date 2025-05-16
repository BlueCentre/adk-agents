# Agents/devops/components/planning_manager.py
import logging
from typing import Optional, Tuple

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

from .. import prompts as agent_prompts 
from .. import config as agent_config 

logger = logging.getLogger(__name__)

class PlanningManager:
    """Manages the state and logic for the interactive planning feature."""

    def __init__(self, console_manager=None): 
        self.pending_plan_text: Optional[str] = None
        self.is_awaiting_plan_approval: bool = False
        self.is_plan_generation_turn: bool = False 
        self._console = console_manager 

    def reset_planning_state(self):
        self.pending_plan_text = None
        self.is_awaiting_plan_approval = False
        self.is_plan_generation_turn = False
        logger.debug("PlanningManager state reset.")

    def _should_trigger_heuristic(self, user_message_content: str) -> bool:
        lower_user_message = user_message_content.lower()
        explicit_keywords = [
            "plan this", "create a plan", "show me the plan", 
            "draft a plan", "plan for me", "let's plan"
        ]
        complex_task_keywords = [
            "implement", "create new", "design a", "develop a", 
            "refactor module", "add feature", "build a new"
        ]
        if any(keyword in lower_user_message for keyword in explicit_keywords):
            logger.info("PlanningManager: Explicit planning request detected.")
            return True
        if any(keyword in lower_user_message for keyword in complex_task_keywords):
            logger.info("PlanningManager: Complex task keywords detected, suggesting planning.")
            return True
        return False

    async def handle_before_model_planning_logic(
        self, 
        user_message_content: Optional[str], 
        llm_request: LlmRequest,
    ) -> Tuple[Optional[LlmResponse], Optional[str]]: # Ensure return type is a 2-tuple
        """Handles planning logic before the main LLM call.
        Returns: 
            A tuple: (LlmResponse | None, approved_plan_text | None)
            - LlmResponse: If the planning manager fully handles the turn (e.g. sends feedback ack).
            - approved_plan_text: The text of the plan if it was just approved by the user.
        """
        if self.is_awaiting_plan_approval and user_message_content:
            user_feedback_lower = user_message_content.strip().lower()
            if user_feedback_lower == "approve":
                logger.info("PlanningManager: User approved the plan.")
                approved_plan = self.pending_plan_text # Capture before reset
                self.reset_planning_state()
                return None, approved_plan # (No LlmResponse, approved_plan_text)
            else:
                logger.info("PlanningManager: User provided feedback on the plan. Resetting.")
                self.reset_planning_state()
                response_part = genai_types.Part(
                    text="Okay, I've received your feedback. I will consider it for the next step. If you'd like me to try planning again with this new information, please let me know or re-state your goal."
                )
                # (LlmResponse to send, no approved_plan_text)
                return LlmResponse(content=genai_types.Content(parts=[response_part])), None 

        if not self.is_awaiting_plan_approval and agent_config.ENABLE_INTERACTIVE_PLANNING and user_message_content:
            if self._should_trigger_heuristic(user_message_content):
                logger.info("PlanningManager: Heuristic triggered. Preparing for plan generation.")
                self.is_plan_generation_turn = True 

                code_context_str = "" 
                planning_prompt_text = agent_prompts.PLANNING_PROMPT_TEMPLATE.format(
                    user_request=user_message_content,
                    code_context_section=code_context_str
                )
                
                llm_request.contents = [genai_types.Content(parts=[genai_types.Part(text=planning_prompt_text)], role="user")]
                
                if hasattr(llm_request, 'tools'): 
                    llm_request.tools = [] 
                else:
                    logger.warning("PlanningManager: 'LlmRequest' object has no 'tools' attribute to clear. Tools might remain active.")
                
                logger.info("PlanningManager: LLM request modified for plan generation.")
                return None, None # (No LlmResponse, no approved_plan_text yet)
        
        return None, None # Default: No planning action, no approved plan

    async def handle_after_model_planning_logic(
        self, 
        llm_response: LlmResponse,
        extract_text_fn # Callable[[LlmResponse], Optional[str]]
    ) -> Optional[LlmResponse]: 
        if self.is_plan_generation_turn: 
            self.is_plan_generation_turn = False 
            plan_text = extract_text_fn(llm_response)

            if plan_text:
                logger.info(f"PlanningManager: LLM generated plan: {plan_text[:300]}...")
                self.pending_plan_text = plan_text
                self.is_awaiting_plan_approval = True
                
                user_facing_plan_message = (
                    f"{plan_text}\n\n" 
                    "Does this plan look correct? Please type 'approve' to proceed, "
                    "or provide feedback to revise the plan."
                )
                response_part = genai_types.Part(text=user_facing_plan_message)
                usage_meta = llm_response.usage_metadata if hasattr(llm_response, 'usage_metadata') else None
                final_response = LlmResponse(content=genai_types.Content(parts=[response_part]), 
                                           usage_metadata=usage_meta)
                return final_response 
            else:
                logger.error("PlanningManager: Plan generation turn, but could not extract plan text.")
                self.reset_planning_state() 
                error_message = "I tried to generate a plan, but something went wrong. Please try rephrasing your request."
                return LlmResponse(content=genai_types.Content(parts=[genai_types.Part(text=error_message)]))
        
        return None 
