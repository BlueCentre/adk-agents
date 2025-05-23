"""Intelligent summarization for context-aware compression techniques."""

import logging
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum, auto
import json

logger = logging.getLogger(__name__)

class ContentType(Enum):
    """Types of content for specialized summarization."""
    CODE = auto()
    DOCUMENTATION = auto()
    TOOL_OUTPUT = auto()
    ERROR_MESSAGE = auto()
    LOG_OUTPUT = auto()
    CONFIGURATION = auto()
    CONVERSATION = auto()
    GENERIC = auto()

@dataclass
class SummarizationContext:
    """Context information for intelligent summarization."""
    current_task: str = ""
    relevant_keywords: List[str] = None
    error_context: bool = False
    code_context: bool = False
    urgency_level: str = "normal"  # low, normal, high, critical
    target_length: int = 500
    preserve_details: List[str] = None

    def __post_init__(self):
        if self.relevant_keywords is None:
            self.relevant_keywords = []
        if self.preserve_details is None:
            self.preserve_details = []

class IntelligentSummarizer:
    """Implements intelligent, context-aware summarization."""
    
    def __init__(self):
        # Content type detection patterns
        self.content_patterns = {
            ContentType.CODE: [
                r'def\s+\w+\s*\(', r'class\s+\w+', r'function\s+\w+\s*\(',
                r'import\s+\w+', r'from\s+\w+\s+import', r'=>', r'\{\s*\}',
                r'console\.log', r'print\s*\(', r'return\s+'
            ],
            ContentType.ERROR_MESSAGE: [
                r'error:', r'exception:', r'traceback', r'failed', r'ERROR',
                r'FATAL', r'CRITICAL', r'warning:', r'WARNING', r'stderr'
            ],
            ContentType.LOG_OUTPUT: [
                r'\d{4}-\d{2}-\d{2}', r'\[\d{2}:\d{2}:\d{2}\]', r'INFO:',
                r'DEBUG:', r'WARN:', r'log', r'timestamp'
            ],
            ContentType.CONFIGURATION: [
                r'".*":\s*".*"', r'config', r'settings', r'\.json$', r'\.yaml$',
                r'\.toml$', r'environment', r'ENV'
            ],
            ContentType.TOOL_OUTPUT: [
                r'command:', r'output:', r'result:', r'status:', r'exit_code'
            ]
        }
        
        # Importance keywords for content preservation
        self.high_importance_keywords = [
            'error', 'fail', 'exception', 'critical', 'bug', 'issue', 'problem',
            'warning', 'deprecated', 'security', 'vulnerability', 'auth',
            'config', 'setup', 'install', 'deploy', 'build', 'test', 'main',
            'api', 'endpoint', 'database', 'connection', 'timeout'
        ]
        
        # Technical keywords that should be preserved
        self.technical_keywords = [
            'function', 'class', 'method', 'variable', 'parameter', 'argument',
            'return', 'import', 'module', 'package', 'library', 'framework',
            'async', 'await', 'promise', 'callback', 'event', 'listener'
        ]
    
    def summarize_content(
        self,
        content: str,
        context: SummarizationContext,
        content_type: Optional[ContentType] = None
    ) -> str:
        """Main entry point for intelligent summarization."""
        
        if not content or not content.strip():
            return ""
        
        # Auto-detect content type if not provided
        if content_type is None:
            content_type = self._detect_content_type(content)
        
        logger.debug(f"INTELLIGENT SUMMARIZATION: Content type: {content_type.name}, Target length: {context.target_length}")
        
        # If content is already short enough, return as-is
        if len(content) <= context.target_length:
            logger.debug(f"  Content already within target length ({len(content)} <= {context.target_length})")
            return content
        
        # Apply content-type specific summarization
        summary = self._summarize_by_type(content, content_type, context)
        
        # Post-process to ensure quality and length
        summary = self._post_process_summary(summary, context)
        
        # Log summarization metrics
        compression_ratio = len(summary) / len(content) if content else 0
        logger.info(f"  📝 SUMMARIZED: {len(content):,} → {len(summary):,} chars (ratio: {compression_ratio:.2f})")
        
        return summary
    
    def summarize_code_snippet(
        self,
        code: str,
        file_path: str,
        context: SummarizationContext
    ) -> str:
        """Specialized summarization for code snippets."""
        
        if not code or len(code) <= context.target_length:
            return code
        
        logger.debug(f"INTELLIGENT SUMMARIZATION: Code snippet from {file_path}")
        
        # Extract key elements from code
        functions = self._extract_functions(code)
        classes = self._extract_classes(code)
        imports = self._extract_imports(code)
        key_variables = self._extract_key_variables(code, context.relevant_keywords)
        
        # Build structured summary
        summary_parts = []
        
        # File header
        summary_parts.append(f"# Code from {file_path}")
        
        # Imports (always preserve)
        if imports:
            summary_parts.append("## Imports:")
            summary_parts.extend(imports[:5])  # Limit to 5 most important imports
        
        # Classes
        if classes:
            summary_parts.append("## Classes:")
            for class_info in classes[:3]:  # Limit to 3 classes
                summary_parts.append(f"- {class_info}")
        
        # Functions
        if functions:
            summary_parts.append("## Functions:")
            for func_info in functions[:5]:  # Limit to 5 functions
                summary_parts.append(f"- {func_info}")
        
        # Key variables/constants
        if key_variables:
            summary_parts.append("## Key Variables:")
            summary_parts.extend(key_variables[:3])
        
        # If still too long, include partial code with most relevant sections
        summary = '\n'.join(summary_parts)
        if len(summary) > context.target_length and len(summary_parts) > 10:
            # Truncate and add ellipsis
            truncated = summary[:context.target_length - 50]
            summary = truncated + "\n\n... (content truncated)"
        
        return summary
    
    def summarize_tool_output(
        self,
        tool_name: str,
        output: Any,
        context: SummarizationContext
    ) -> str:
        """Specialized summarization for tool outputs."""
        
        if isinstance(output, dict):
            output_str = json.dumps(output, indent=2)
        else:
            output_str = str(output)
        
        if len(output_str) <= context.target_length:
            return output_str
        
        logger.debug(f"INTELLIGENT SUMMARIZATION: Tool output from {tool_name}")
        
        # Tool-specific summarization strategies
        if tool_name in ['read_file', 'read_file_content']:
            return self._summarize_file_content(output_str, context)
        elif tool_name in ['execute_vetted_shell_command', 'run_terminal_cmd']:
            return self._summarize_shell_output(output_str, context)
        elif tool_name in ['codebase_search', 'grep_search']:
            return self._summarize_search_results(output_str, context)
        elif tool_name in ['edit_file', 'edit_file_content']:
            return self._summarize_edit_results(output_str, context)
        else:
            return self._summarize_generic_output(output_str, context)
    
    def _detect_content_type(self, content: str) -> ContentType:
        """Detect the type of content for appropriate summarization."""
        
        content_lower = content.lower()
        
        # Check each content type pattern
        for content_type, patterns in self.content_patterns.items():
            matches = sum(1 for pattern in patterns if re.search(pattern, content, re.IGNORECASE))
            if matches >= 2:  # Require at least 2 pattern matches
                return content_type
        
        # Default classification based on simple heuristics
        if any(keyword in content_lower for keyword in ['def ', 'class ', 'function', 'import']):
            return ContentType.CODE
        elif any(keyword in content_lower for keyword in ['error', 'exception', 'failed', 'traceback']):
            return ContentType.ERROR_MESSAGE
        elif content_lower.count(':') > content_lower.count(' ') / 10:  # High ratio of colons suggests config
            return ContentType.CONFIGURATION
        elif re.search(r'\d{2}:\d{2}:\d{2}', content):  # Timestamp pattern suggests logs
            return ContentType.LOG_OUTPUT
        else:
            return ContentType.GENERIC
    
    def _summarize_by_type(
        self,
        content: str,
        content_type: ContentType,
        context: SummarizationContext
    ) -> str:
        """Apply content-type specific summarization."""
        
        if content_type == ContentType.CODE:
            return self._summarize_code(content, context)
        elif content_type == ContentType.ERROR_MESSAGE:
            return self._summarize_error(content, context)
        elif content_type == ContentType.LOG_OUTPUT:
            return self._summarize_logs(content, context)
        elif content_type == ContentType.CONFIGURATION:
            return self._summarize_config(content, context)
        elif content_type == ContentType.TOOL_OUTPUT:
            return self._summarize_generic_output(content, context)
        else:
            return self._summarize_generic(content, context)
    
    def _summarize_code(self, code: str, context: SummarizationContext) -> str:
        """Summarize code content preserving key structural elements."""
        
        lines = code.split('\n')
        important_lines = []
        
        # Always preserve certain types of lines
        preserve_patterns = [
            r'^\s*def\s+\w+',     # Function definitions
            r'^\s*class\s+\w+',   # Class definitions
            r'^\s*import\s+',     # Imports
            r'^\s*from\s+\w+\s+import',  # From imports
            r'^\s*#.*',           # Comments
            r'^\s*""".*"""',      # Docstrings
            r'^\s*return\s+',     # Return statements
        ]
        
        for i, line in enumerate(lines):
            # Preserve important structural lines
            if any(re.match(pattern, line) for pattern in preserve_patterns):
                important_lines.append(f"{i+1:4d}: {line}")
            # Preserve lines with relevant keywords
            elif any(keyword in line.lower() for keyword in context.relevant_keywords):
                important_lines.append(f"{i+1:4d}: {line}")
            # Preserve error-related lines if in error context
            elif context.error_context and any(keyword in line.lower() for keyword in ['error', 'exception', 'fail']):
                important_lines.append(f"{i+1:4d}: {line}")
        
        # If we have too few important lines, add some context around them
        if len(important_lines) < 10:
            # Add some surrounding lines for context
            summary = '\n'.join(important_lines)
            if len(summary) < context.target_length // 2:
                # Add more context lines
                for i, line in enumerate(lines[:context.target_length // 50]):
                    if i % 3 == 0:  # Every 3rd line for brevity
                        line_marker = f"{i+1:4d}: {line}"
                        if line_marker not in important_lines:
                            important_lines.append(line_marker)
        
        summary = '\n'.join(important_lines[:context.target_length // 30])  # Rough line limit
        
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 50] + "\n... (truncated)"
        
        return summary
    
    def _summarize_error(self, error_content: str, context: SummarizationContext) -> str:
        """Summarize error messages preserving critical information."""
        
        lines = error_content.split('\n')
        
        # Extract key error information
        error_type = ""
        error_message = ""
        traceback_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if 'error:' in line_lower or 'exception:' in line_lower:
                if not error_type:
                    error_type = line.strip()
            elif 'traceback' in line_lower or 'stack trace' in line_lower:
                traceback_lines.append(line.strip())
            elif any(keyword in line_lower for keyword in ['failed', 'fatal', 'critical']):
                if not error_message:
                    error_message = line.strip()
        
        # Build structured error summary
        summary_parts = []
        
        if error_type:
            summary_parts.append(f"🚨 ERROR: {error_type}")
        
        if error_message:
            summary_parts.append(f"📝 MESSAGE: {error_message}")
        
        if traceback_lines:
            summary_parts.append("📍 TRACEBACK:")
            summary_parts.extend(traceback_lines[:5])  # Limit traceback lines
        
        # Include relevant lines that contain keywords
        relevant_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in context.relevant_keywords):
                relevant_lines.append(line.strip())
        
        if relevant_lines:
            summary_parts.append("🔍 RELEVANT DETAILS:")
            summary_parts.extend(relevant_lines[:3])
        
        summary = '\n'.join(summary_parts)
        
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 50] + "\n... (truncated)"
        
        return summary
    
    def _summarize_logs(self, log_content: str, context: SummarizationContext) -> str:
        """Summarize log output focusing on errors and relevant events."""
        
        lines = log_content.split('\n')
        
        # Categorize log lines
        error_lines = []
        warning_lines = []
        info_lines = []
        relevant_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['error', 'exception', 'fatal', 'critical']):
                error_lines.append(line.strip())
            elif any(keyword in line_lower for keyword in ['warn', 'warning']):
                warning_lines.append(line.strip())
            elif any(keyword in line.lower() for keyword in context.relevant_keywords):
                relevant_lines.append(line.strip())
            elif 'info' in line_lower and len(info_lines) < 5:
                info_lines.append(line.strip())
        
        # Build prioritized summary
        summary_parts = []
        
        if error_lines:
            summary_parts.append("❌ ERRORS:")
            summary_parts.extend(error_lines[:5])
        
        if warning_lines:
            summary_parts.append("⚠️  WARNINGS:")
            summary_parts.extend(warning_lines[:3])
        
        if relevant_lines:
            summary_parts.append("🔍 RELEVANT:")
            summary_parts.extend(relevant_lines[:5])
        
        if info_lines and len(summary_parts) < 10:
            summary_parts.append("ℹ️  INFO:")
            summary_parts.extend(info_lines[:3])
        
        summary = '\n'.join(summary_parts)
        
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 50] + "\n... (truncated)"
        
        return summary
    
    def _summarize_config(self, config_content: str, context: SummarizationContext) -> str:
        """Summarize configuration files preserving key settings."""
        
        # Try to parse as JSON first
        try:
            config_data = json.loads(config_content)
            return self._summarize_json_config(config_data, context)
        except json.JSONDecodeError:
            pass
        
        # Handle as plain text config
        lines = config_content.split('\n')
        important_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Preserve lines with important keywords
            if any(keyword in line.lower() for keyword in self.high_importance_keywords):
                important_lines.append(line_stripped)
            elif any(keyword in line.lower() for keyword in context.relevant_keywords):
                important_lines.append(line_stripped)
            elif '=' in line or ':' in line:  # Configuration assignments
                important_lines.append(line_stripped)
        
        summary = '\n'.join(important_lines[:context.target_length // 50])
        
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 50] + "\n... (truncated)"
        
        return summary
    
    def _summarize_json_config(self, config_data: Dict[str, Any], context: SummarizationContext) -> str:
        """Summarize JSON configuration data."""
        
        important_keys = []
        
        def extract_important_values(data, prefix=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    
                    # Check if key or value contains important keywords
                    if any(keyword in key.lower() for keyword in self.high_importance_keywords):
                        important_keys.append(f"{full_key}: {value}")
                    elif any(keyword in str(value).lower() for keyword in context.relevant_keywords):
                        important_keys.append(f"{full_key}: {value}")
                    elif isinstance(value, dict):
                        extract_important_values(value, full_key)
                    elif isinstance(value, list) and len(value) > 0:
                        important_keys.append(f"{full_key}: [{len(value)} items]")
        
        extract_important_values(config_data)
        
        summary = '\n'.join(important_keys[:context.target_length // 80])
        
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 50] + "\n... (truncated)"
        
        return summary
    
    def _summarize_generic(self, content: str, context: SummarizationContext) -> str:
        """Generic summarization for unstructured content."""
        
        # Simple extractive summarization
        sentences = re.split(r'[.!?]+', content)
        important_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue
            
            # Score sentence importance
            importance_score = 0
            
            # Check for important keywords
            for keyword in self.high_importance_keywords:
                if keyword in sentence.lower():
                    importance_score += 2
            
            # Check for relevant keywords
            for keyword in context.relevant_keywords:
                if keyword in sentence.lower():
                    importance_score += 3
            
            # Check for technical keywords
            for keyword in self.technical_keywords:
                if keyword in sentence.lower():
                    importance_score += 1
            
            if importance_score > 0:
                important_sentences.append((importance_score, sentence))
        
        # Sort by importance and take top sentences
        important_sentences.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [sentence for _, sentence in important_sentences[:10]]
        
        summary = '. '.join(top_sentences)
        
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 50] + "..."
        
        return summary
    
    def _summarize_file_content(self, content: str, context: SummarizationContext) -> str:
        """Summarize file content read by read_file tool."""
        return self.summarize_content(content, context)
    
    def _summarize_shell_output(self, output: str, context: SummarizationContext) -> str:
        """Summarize shell command output."""
        
        lines = output.split('\n')
        
        # Prioritize error lines and relevant output
        important_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['error', 'failed', 'exception']):
                important_lines.append(f"❌ {line.strip()}")
            elif any(keyword in line.lower() for keyword in context.relevant_keywords):
                important_lines.append(f"🔍 {line.strip()}")
            elif line.strip() and len(important_lines) < 20:
                important_lines.append(line.strip())
        
        summary = '\n'.join(important_lines[:context.target_length // 50])
        
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 50] + "\n... (truncated)"
        
        return summary
    
    def _summarize_search_results(self, results: str, context: SummarizationContext) -> str:
        """Summarize search results from codebase_search or grep_search."""
        
        lines = results.split('\n')
        
        # Extract file matches and relevant snippets
        file_matches = []
        code_snippets = []
        
        current_file = ""
        for line in lines:
            if ':' in line and len(line.split(':')) >= 2:
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    file_path, line_num, content = parts[0], parts[1], parts[2]
                    if file_path != current_file:
                        current_file = file_path
                        file_matches.append(file_path)
                    code_snippets.append(f"{file_path}:{line_num}: {content.strip()}")
        
        # Build summary
        summary_parts = []
        
        if file_matches:
            summary_parts.append(f"📁 FOUND IN {len(file_matches)} FILES:")
            summary_parts.extend(file_matches[:10])
        
        if code_snippets:
            summary_parts.append("🔍 RELEVANT MATCHES:")
            summary_parts.extend(code_snippets[:15])
        
        summary = '\n'.join(summary_parts)
        
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 50] + "\n... (truncated)"
        
        return summary
    
    def _summarize_edit_results(self, output: str, context: SummarizationContext) -> str:
        """Summarize file edit results."""
        
        # Extract key information from edit results
        summary_parts = []
        
        if 'successfully' in output.lower():
            summary_parts.append("✅ Edit completed successfully")
        elif 'error' in output.lower() or 'failed' in output.lower():
            summary_parts.append("❌ Edit failed")
        
        # Include relevant details
        lines = output.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['file', 'line', 'change', 'modify']):
                summary_parts.append(line.strip())
        
        summary = '\n'.join(summary_parts[:10])
        
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 50] + "\n... (truncated)"
        
        return summary
    
    def _summarize_generic_output(self, output: str, context: SummarizationContext) -> str:
        """Summarize generic tool output."""
        return self._summarize_generic(output, context)
    
    def _extract_functions(self, code: str) -> List[str]:
        """Extract function definitions from code."""
        functions = []
        
        # Python functions
        for match in re.finditer(r'def\s+(\w+)\s*\(([^)]*)\):', code):
            func_name, params = match.groups()
            functions.append(f"def {func_name}({params})")
        
        # JavaScript functions
        for match in re.finditer(r'function\s+(\w+)\s*\(([^)]*)\)', code):
            func_name, params = match.groups()
            functions.append(f"function {func_name}({params})")
        
        return functions
    
    def _extract_classes(self, code: str) -> List[str]:
        """Extract class definitions from code."""
        classes = []
        
        # Python classes
        for match in re.finditer(r'class\s+(\w+)(?:\s*\(([^)]*)\))?:', code):
            class_name, inheritance = match.groups()
            if inheritance:
                classes.append(f"class {class_name}({inheritance})")
            else:
                classes.append(f"class {class_name}")
        
        return classes
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extract import statements from code."""
        imports = []
        
        for match in re.finditer(r'^(import\s+.+|from\s+.+\s+import\s+.+)$', code, re.MULTILINE):
            imports.append(match.group(1))
        
        return imports
    
    def _extract_key_variables(self, code: str, relevant_keywords: List[str]) -> List[str]:
        """Extract key variable assignments."""
        variables = []
        
        # Simple variable assignments
        for match in re.finditer(r'^(\w+)\s*=\s*(.+)$', code, re.MULTILINE):
            var_name, value = match.groups()
            if any(keyword in var_name.lower() or keyword in value.lower() for keyword in relevant_keywords):
                variables.append(f"{var_name} = {value[:50]}{'...' if len(value) > 50 else ''}")
        
        return variables
    
    def _post_process_summary(self, summary: str, context: SummarizationContext) -> str:
        """Post-process summary to ensure quality and adherence to constraints."""
        
        if not summary:
            return ""
        
        # Ensure we don't exceed target length
        if len(summary) > context.target_length:
            summary = summary[:context.target_length - 10] + "..."
        
        # Clean up formatting
        summary = re.sub(r'\n\s*\n\s*\n', '\n\n', summary)  # Remove excessive newlines
        summary = summary.strip()
        
        return summary 