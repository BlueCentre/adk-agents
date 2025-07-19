# Agents/devops/components/planning_manager.py
import logging
from typing import Optional, Tuple

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

from .. import config as agent_config
from .. import prompts as agent_prompts

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
        
        # Explicit planning requests - these always trigger
        explicit_keywords = [
            "plan this", "create a plan", "show me the plan", 
            "draft a plan", "plan for me", "let's plan", "make a plan"
        ]
        
        # Check for explicit planning requests first
        if any(keyword in lower_user_message for keyword in explicit_keywords):
            logger.info("PlanningManager: Explicit planning request detected.")
            return True
        
        # Simple exploration tasks that should NOT trigger planning
        simple_exploration_patterns = [
            r"read\s+.*file",
            r"show\s+.*file", 
            r"list\s+.*",
            r"find\s+.*",
            r"search\s+.*",
            r"explain\s+.*",
            r"what\s+is.*",
            r"how\s+does.*work",
            r"check\s+.*status",
            r"view\s+.*log"
        ]
        
        # If it's a simple exploration, don't trigger planning
        import re
        for pattern in simple_exploration_patterns:
            if re.search(pattern, lower_user_message):
                logger.info(f"PlanningManager: Simple exploration detected ({pattern}), skipping planning.")
                return False
        
        # Complex implementation task indicators - these should trigger planning
        complex_implementation_keywords = [
            "implement and", "create and deploy", "build and test", "design and implement",
            "refactor entire", "migrate from", "upgrade from", "convert to",
            "generate comprehensive", "create full", "build complete"
        ]
        
        # Multi-step modification indicators
        modification_sequences = [
            r"(add|create|implement).*then.*(test|deploy|document)",
            r"(refactor|modify).*and.*(update|change|add)",
            r"(analyze|review).*then.*(implement|create|modify)",
            r"(setup|configure).*and.*(deploy|test|monitor)"
        ]
        
        # Check for complex implementation tasks
        if any(keyword in lower_user_message for keyword in complex_implementation_keywords):
            logger.info("PlanningManager: Complex implementation task detected, triggering planning.")
            return True
            
        # Check for modification sequences that suggest multi-step work
        for pattern in modification_sequences:
            if re.search(pattern, lower_user_message):
                logger.info(f"PlanningManager: Multi-step modification sequence detected ({pattern}), triggering planning.")
                return True
        
        # Refined multi-step indicators - only if combined with action verbs
        multi_step_indicators = [
            "start by", "then", "after that", "next", "finally", "first", "second", "third",
            "step 1", "step 2", "step 3", "and then", "followed by", "subsequently"
        ]
        
        action_verbs = ["implement", "create", "build", "develop", "design", "refactor", 
                       "generate", "deploy", "configure", "setup", "migrate", "convert"]
        
        # Only trigger on multi-step if we have both indicators AND action verbs
        has_multi_step = any(indicator in lower_user_message for indicator in multi_step_indicators)
        has_action_verbs = any(verb in lower_user_message for verb in action_verbs)
        
        if has_multi_step and has_action_verbs:
            found_indicators = [ind for ind in multi_step_indicators if ind in lower_user_message]
            found_verbs = [verb for verb in action_verbs if verb in lower_user_message]
            logger.info(f"PlanningManager: Multi-step implementation task detected (indicators: {found_indicators}, verbs: {found_verbs}), triggering planning.")
            return True
            
        # Check for multiple deliverables (suggests complex project)
        deliverable_keywords = ["report", "analysis", "implementation", "documentation", "enhancement", "system", "application", "service"]
        found_deliverables = [word for word in deliverable_keywords if word in lower_user_message]
        if len(found_deliverables) >= 2:
            logger.info(f"PlanningManager: Multiple deliverables detected ({found_deliverables}), triggering planning.")
            return True
        
        # Don't trigger for simple combinations anymore
        logger.info("PlanningManager: No complex task patterns detected, proceeding without planning.")
        return False

    def _is_plan_related_feedback(self, user_message: str) -> bool:
        """Determine if a user message is feedback on the current plan vs a new unrelated request.
        
        Args:
            user_message: The user's message to analyze
            
        Returns:
            True if it appears to be feedback on the plan, False if it's a new request
        """
        lower_message = user_message.lower().strip()
        
        # Explicit approval
        if lower_message == "approve":
            return True
            
        # Explicit plan feedback indicators
        plan_feedback_keywords = [
            "plan", "step", "phase", "approach", "methodology", "strategy",
            "add", "remove", "change", "modify", "revise", "update",
            "shorter", "longer", "simpler", "more detailed",
            "before", "after", "instead", "also include", "don't include",
            "different approach", "alternative", "better way"
        ]
        
        # Check if message mentions planning concepts
        if any(keyword in lower_message for keyword in plan_feedback_keywords):
            return True
            
        # Check for modification language
        modification_patterns = [
            "make it", "can you", "could you", "please", "try to",
            "instead of", "rather than", "what if", "how about"
        ]
        
        if any(pattern in lower_message for pattern in modification_patterns):
            # Could be feedback, but check if it's about something completely unrelated
            unrelated_keywords = [
                "k8s", "kubernetes", "cluster", "pod", "deployment", "service",
                "database", "db", "server", "api", "endpoint", "url",
                "user", "login", "password", "auth", "security",
                "weather", "time", "date", "location", "email",
                "what is", "how do i", "where is", "when", "who",
                "status", "health", "monitoring", "metrics"
            ]
            
            # If it mentions unrelated concepts, it's probably a new request
            if any(keyword in lower_message for keyword in unrelated_keywords):
                return False
                
            return True  # Assume it's plan feedback if it has modification language but no unrelated keywords
            
        # Short questions are probably new requests
        if len(user_message.split()) <= 8 and any(word in lower_message for word in ["what", "how", "where", "when", "who", "why"]):
            return False
            
        # If it doesn't look like plan feedback, treat it as a new request
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
        try:
            if self.is_awaiting_plan_approval and user_message_content:
                user_feedback_lower = user_message_content.strip().lower()
                if user_feedback_lower == "approve":
                    logger.info("PlanningManager: User approved the plan.")
                    approved_plan = self.pending_plan_text # Capture before reset
                    self.reset_planning_state()
                    return None, approved_plan # (No LlmResponse, approved_plan_text)
                elif self._is_plan_related_feedback(user_message_content):
                    logger.info("PlanningManager: User provided feedback on the plan. Resetting planning state.")
                    self.reset_planning_state()
                    response_part = genai_types.Part(
                        text="Okay, I've received your feedback. I will consider it for the next step. If you'd like me to try planning again with this new information, please let me know or re-state your goal."
                    )
                    # (LlmResponse to send, no approved_plan_text)
                    return LlmResponse(content=genai_types.Content(parts=[response_part])), None 
                else:
                    # This appears to be a completely different request, not plan feedback
                    logger.info("PlanningManager: User message appears to be a new request, not plan feedback. Resetting planning state and allowing normal processing.")
                    self.reset_planning_state()
                    # Return None to allow normal processing of the new request
                    return None, None

            if not self.is_awaiting_plan_approval and agent_config.ENABLE_INTERACTIVE_PLANNING and user_message_content:
                if self._should_trigger_heuristic(user_message_content):
                    logger.info("PlanningManager: Heuristic triggered. Preparing for plan generation.")
                    self.is_plan_generation_turn = True 

                    # Try to gather relevant code context for planning
                    code_context_str = ""
                    try:
                        # Check if this looks like a request about a specific codebase
                        if any(keyword in user_message_content.lower() for keyword in 
                               ["codebase", "code", "file", "function", "class", "module", "analyze", "agent"]):
                            logger.info("PlanningManager: Request mentions code/codebase, attempting to retrieve context.")
                            
                            # This is a simplified context gathering approach
                            # In a full implementation, you'd want to use the RAG tools if available
                            code_context_str = "\n--- RELEVANT CODE CONTEXT ---\n"
                            code_context_str += "Note: Planning system detected this is a code-related request.\n"
                            code_context_str += "The agent has access to tools like 'codebase_search', 'read_file', and 'index_directory_tool'\n"
                            code_context_str += "to analyze and understand the codebase structure during plan execution.\n"
                            code_context_str += "--- END RELEVANT CODE CONTEXT ---\n"
                            
                    except Exception as e:
                        logger.warning(f"PlanningManager: Error gathering code context: {e}")
                        code_context_str = ""
                    
                    # Ensure parameters are not None before formatting
                    safe_user_request = user_message_content or ""
                    safe_code_context = code_context_str or ""
                    
                    try:
                        planning_prompt_text = agent_prompts.PLANNING_PROMPT_TEMPLATE.format(
                            user_request=safe_user_request,
                            code_context_section=safe_code_context
                        )
                    except Exception as format_error:
                        logger.error(f"PlanningManager: Failed to format planning prompt template: {format_error}")
                        logger.error(f"user_request type: {type(safe_user_request)}, value: {repr(safe_user_request)}")
                        logger.error(f"code_context_section type: {type(safe_code_context)}, value: {repr(safe_code_context)}")
                        # Fallback to a simple prompt without template formatting
                        planning_prompt_text = f"Create a comprehensive plan for this request: {safe_user_request}"
                    
                    try:
                        llm_request.contents = [genai_types.Content(parts=[genai_types.Part(text=planning_prompt_text)], role="user")]
                        
                        if hasattr(llm_request, 'tools'): 
                            llm_request.tools = [] 
                        else:
                            logger.warning("PlanningManager: 'LlmRequest' object has no 'tools' attribute to clear. Tools might remain active.")
                        
                        logger.info("PlanningManager: LLM request modified for plan generation with enhanced context.")
                        return None, None # (No LlmResponse, no approved_plan_text yet)
                    except Exception as request_error:
                        logger.error(f"PlanningManager: Error modifying LLM request: {request_error}")
                        # Reset state and allow normal processing
                        self.reset_planning_state()
                        return None, None
            
            return None, None # Default: No planning action, no approved plan
            
        except Exception as e:
            logger.error(f"PlanningManager: Unexpected error in handle_before_model_planning_logic: {e}", exc_info=True)
            # Reset state to prevent stuck conditions
            self.reset_planning_state()
            return None, None

    async def handle_after_model_planning_logic(
        self, 
        llm_response: LlmResponse,
        extract_text_fn # Callable[[LlmResponse], Optional[str]]
    ) -> Optional[LlmResponse]: 
        try:
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
            
        except Exception as e:
            logger.error(f"PlanningManager: Unexpected error in handle_after_model_planning_logic: {e}", exc_info=True)
            # Reset state to prevent stuck conditions
            self.reset_planning_state()
            error_message = f"I encountered an error while processing the planning response: {str(e)}. Please try again."
            return LlmResponse(content=genai_types.Content(parts=[genai_types.Part(text=error_message)]))
