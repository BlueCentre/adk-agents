import json
import os
from collections import defaultdict
from datetime import datetime

# Define a simple file for persistence
LEARNING_DATA_FILE = os.path.join(os.path.dirname(__file__), 'learning_data.json')

class LearningSystem:
    def __init__(self):
        self.learned_patterns = self._load_data()

    def _load_data(self):
        if os.path.exists(LEARNING_DATA_FILE):
            with open(LEARNING_DATA_FILE, 'r') as f:
                return json.load(f)
        return {}

    def _save_data(self):
        with open(LEARNING_DATA_FILE, 'w') as f:
                json.dump(self.learned_patterns, f, indent=4)

    def record_success(self, original_command: str, error_type: str, successful_alternative: str, context_keywords: list[str]):
        key = f"{original_command}|{error_type}"
        if key not in self.learned_patterns:
            self.learned_patterns[key] = {
                "original_command": original_command,
                "error_type": error_type,
                "successful_alternatives": defaultdict(int),
                "context_keywords": list(set(context_keywords)), # Ensure unique keywords
                "last_updated": datetime.now().isoformat()
            }
        self.learned_patterns[key]["successful_alternatives"][successful_alternative] += 1
        self.learned_patterns[key]["last_updated"] = datetime.now().isoformat()
        self._save_data()

    def get_suggestions(self, original_command: str, error_type: str, context_keywords: list[str]) -> list[str]:
        # Prioritize exact matches first
        exact_key = f"{original_command}|{error_type}"
        if exact_key in self.learned_patterns:
            # Sort alternatives by frequency
            sorted_alternatives = sorted(
                self.learned_patterns[exact_key]["successful_alternatives"].items(),
                key=lambda item: item[1],
                reverse=True
            )
            return [alt for alt, count in sorted_alternatives]

        # Then, try to find partial matches based on error type and context keywords
        relevant_suggestions = defaultdict(int)
        for key, data in self.learned_patterns.items():
            if data["error_type"] == error_type:
                # Check for overlap in context keywords
                if any(kw in data["context_keywords"] for kw in context_keywords):
                    for alt, count in data["successful_alternatives"].items():
                        relevant_suggestions[alt] += count # Aggregate counts

        sorted_relevant = sorted(
            relevant_suggestions.items(),
            key=lambda item: item[1],
            reverse=True
        )
        return [alt for alt, count in sorted_relevant]

# Initialize the learning system
learning_system = LearningSystem()
