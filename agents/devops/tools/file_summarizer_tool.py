# Agents/devops/tools/file_summarizer_tool.py
import logging
from pathlib import Path
from typing import Optional  # Import Optional

from google.adk.tools import FunctionTool  # Assuming this is the correct base class
from vertexai.generative_models import GenerativeModel  # For direct Gemini API calls

from .. import config as agent_config

# Initialize logger for this tool
logger = logging.getLogger(__name__)

# Configuration for the summarizer model
# Note: Model configuration is now centralized in config.py
# MAX_CONTENT_CHARS_FOR_SUMMARIZER_SINGLE_PASS = 200000


class FileSummarizerTool(FunctionTool):
    def __init__(self):
        super().__init__(
            func=self._execute  # Pass the execute method as the function for the tool
        )
        try:
            self.model = GenerativeModel(agent_config.SUMMARIZER_MODEL_NAME)
            logger.info(
                f"FileSummarizerTool initialized with model: {agent_config.SUMMARIZER_MODEL_NAME}"
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize GenerativeModel for FileSummarizerTool with model "
                f"{agent_config.SUMMARIZER_MODEL_NAME}: {e}"
            )
            self.model = None  # Ensure model is None if initialization fails

    def _execute(
        self, filepath: str, instructions: str, max_summary_length_words: Optional[int] = None
    ) -> dict:
        logger.info(
            f"Summarizing file '{filepath}' "
            f"with instructions: '{instructions}', "
            f"max_summary_length_words: {max_summary_length_words}"
        )
        if not self.model:
            return {"summary": None, "error": "Summarizer model not initialized."}

        try:
            file_size = Path(filepath).stat().st_size
            logger.info(f"File size for {filepath}: {file_size} bytes.")

            if file_size == 0:
                return {"summary": "<File is empty>", "error": None}

            with Path(filepath).open(encoding="utf-8", errors="ignore") as f:
                content = f.read()

        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
            return {"summary": None, "error": f"File not found: {filepath}"}
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return {"summary": None, "error": f"Error reading file {filepath}: {e!s}"}

        content_to_summarize = content
        if len(content) > agent_config.MAX_CONTENT_CHARS_FOR_SUMMARIZER_SINGLE_PASS:
            logger.warning(
                f"File content length ({len(content)} chars) exceeds "
                f"MAX_CONTENT_CHARS_FOR_SUMMARIZER_SINGLE_PASS "
                f"({agent_config.MAX_CONTENT_CHARS_FOR_SUMMARIZER_SINGLE_PASS}). "
                f"Will summarize only the first part."
            )
            content_to_summarize = content[
                : agent_config.MAX_CONTENT_CHARS_FOR_SUMMARIZER_SINGLE_PASS
            ]

        prompt_parts = [
            "You are an expert assistant specialized in summarizing text documents "
            "accurately and concisely.",
            "Please summarize the following document based on the provided instructions.",
            f'Instructions from user: "{instructions}"',
        ]
        if max_summary_length_words:
            prompt_parts.append(
                f"Aim for a summary of approximately {max_summary_length_words} words, "
                "but prioritize accuracy and completeness of the requested information."
            )

        prompt_parts.append("\nDocument to summarize:\n---\n")
        prompt_parts.append(content_to_summarize)
        prompt_parts.append("\n---\nEnd of Document.\n\nProvide your summary:")

        final_prompt = "\n".join(prompt_parts)

        logger.debug(f"Prompt for summarizer LLM:\n{final_prompt[:500]}... (truncated for brevity)")

        try:
            response = self.model.generate_content(final_prompt)
            summary_text = response.text

            logger.info(f"Successfully received summary from LLM for {filepath}.")
            return {"summary": summary_text.strip(), "error": None}

        except Exception as e:
            logger.error(f"Error calling summarizer LLM for {filepath}: {e}")
            return {
                "summary": None,
                "error": f"An error occurred while calling the summarization model: {e!s}",
            }
