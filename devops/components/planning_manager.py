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
        
        # Explicit planning requests
        explicit_keywords = [
            "plan this", "create a plan", "show me the plan", 
            "draft a plan", "plan for me", "let's plan", "make a plan"
        ]
        
        # Complex multi-step task indicators
        complex_task_keywords = [
            "implement", "create new", "design a", "develop a", 
            "refactor module", "add feature", "build a new",
            "analyze and", "create a", "generate a", "build and",
            "start by", "then", "first", "second", "third", "step",
            "comprehensive", "optimization", "enhancement", "improvement",
            "analyze.*create", "create.*analyze", "read.*then", "identify.*implement"
        ]
        
        # Multi-step indicators (words that suggest a sequence of actions)
        multi_step_indicators = [
            "start by", "then", "after that", "next", "finally", "first", "second", "third",
            "step 1", "step 2", "step 3", "and then", "followed by", "subsequently"
        ]
        
        # Check for explicit planning requests
        if any(keyword in lower_user_message for keyword in explicit_keywords):
            logger.info("PlanningManager: Explicit planning request detected.")
            return True
            
        # Check for complex task keywords
        if any(keyword in lower_user_message for keyword in complex_task_keywords):
            logger.info("PlanningManager: Complex task keywords detected, suggesting planning.")
            return True
            
        # Check for multi-step indicators
        if any(indicator in lower_user_message for indicator in multi_step_indicators):
            logger.info("PlanningManager: Multi-step task indicators detected, suggesting planning.")
            return True
            
        # Additional heuristic: Check for multiple action verbs (suggests complex task)
        action_verbs = ["analyze", "create", "implement", "develop", "build", "design", "refactor", 
                       "generate", "optimize", "enhance", "identify", "document", "read", "write"]
        found_verbs = [verb for verb in action_verbs if verb in lower_user_message]
        if len(found_verbs) >= 2:
            logger.info(f"PlanningManager: Multiple action verbs detected ({found_verbs}), suggesting complex multi-step task.")
            return True
            
        # Check for requests that mention multiple deliverables
        if len([word for word in ["report", "analysis", "implementation", "documentation", "enhancement"] 
               if word in lower_user_message]) >= 2:
            logger.info("PlanningManager: Multiple deliverables detected, suggesting planning.")
            return True
            
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
                
                planning_prompt_text = agent_prompts.PLANNING_PROMPT_TEMPLATE.format(
                    user_request=user_message_content,
                    code_context_section=code_context_str
                )
                
                llm_request.contents = [genai_types.Content(parts=[genai_types.Part(text=planning_prompt_text)], role="user")]
                
                if hasattr(llm_request, 'tools'): 
                    llm_request.tools = [] 
                else:
                    logger.warning("PlanningManager: 'LlmRequest' object has no 'tools' attribute to clear. Tools might remain active.")
                
                logger.info("PlanningManager: LLM request modified for plan generation with enhanced context.")
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
