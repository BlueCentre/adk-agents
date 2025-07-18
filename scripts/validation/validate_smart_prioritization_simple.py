#!/usr/bin/env python3
"""
Simplified validation script for Smart Prioritization system.
Tests various scenarios to demonstrate relevance-based ranking.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Add the agents/devops directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents', 'devops'))

# Import only the smart prioritization module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents', 'devops', 'components', 'context_management'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the smart prioritization classes directly
from smart_prioritization import RelevanceScore, SmartPrioritizer


class SmartPrioritizationValidator:
    """Validates the smart prioritization system with comprehensive test cases."""
    
    def __init__(self):
        self.prioritizer = SmartPrioritizer()
        self.test_results = []
    
    def run_all_tests(self):
        """Run all validation tests."""
        print("🧪 SMART PRIORITIZATION VALIDATION")
        print("=" * 50)
        
        # Test 1: Content Relevance
        self.test_content_relevance()
        
        # Test 2: Recency Impact
        self.test_recency_impact()
        
        # Test 3: Error Priority
        self.test_error_priority()
        
        # Test 4: Context Coherence
        self.test_context_coherence()
        
        # Test 5: Frequency Score
        self.test_frequency_score()
        
        # Test 6: End-to-End Ranking
        self.test_end_to_end_ranking()
        
        # Test 7: Tool Results Prioritization
        self.test_tool_results_prioritization()
        
        # Summary
        return self.print_summary()
    
    def test_content_relevance(self):
        """Test content relevance scoring."""
        print("\n📊 TEST 1: Content Relevance Scoring")
        print("-" * 40)
        
        current_context = "debugging authentication error in user login system"
        
        test_snippets = [
            {
                'file': 'auth/login.py',
                'code': 'def authenticate_user(username, password):\n    if not validate_credentials(username, password):\n        raise AuthenticationError("Invalid credentials")',
                'start_line': 45,
                'last_accessed': 10
            },
            {
                'file': 'utils/helpers.py', 
                'code': 'def format_date(date_obj):\n    return date_obj.strftime("%Y-%m-%d")',
                'start_line': 12,
                'last_accessed': 10
            },
            {
                'file': 'auth/models.py',
                'code': 'class User(Model):\n    username = CharField(max_length=150)\n    password = CharField(max_length=128)',
                'start_line': 8,
                'last_accessed': 10
            }
        ]
        
        ranked_snippets = self.prioritizer.prioritize_code_snippets(
            test_snippets, current_context, current_turn=15
        )
        
        print("Expected ranking: auth/login.py > auth/models.py > utils/helpers.py")
        print("Actual ranking:")
        for i, snippet in enumerate(ranked_snippets):
            score = snippet['_relevance_score']
            print(f"  {i+1}. {snippet['file']} (final: {score.final_score:.3f}, content: {score.content_relevance:.3f})")
        
        # Validate that auth-related files rank higher
        auth_files = [s for s in ranked_snippets if 'auth' in s['file']]
        non_auth_files = [s for s in ranked_snippets if 'auth' not in s['file']]
        
        if auth_files and non_auth_files:
            auth_score = auth_files[0]['_relevance_score'].final_score
            non_auth_score = non_auth_files[0]['_relevance_score'].final_score
            success = auth_score > non_auth_score
            print(f"✅ PASS: Auth files ranked higher" if success else f"❌ FAIL: Auth files not prioritized")
            self.test_results.append(("Content Relevance", success))
        else:
            print("⚠️  SKIP: Not enough variety in test data")
            self.test_results.append(("Content Relevance", True))
    
    def test_recency_impact(self):
        """Test recency scoring impact."""
        print("\n⏰ TEST 2: Recency Impact")
        print("-" * 40)
        
        current_context = "working on file operations"
        current_turn = 20
        
        test_snippets = [
            {
                'file': 'file_ops.py',
                'code': 'def read_file(path): return open(path).read()',
                'start_line': 1,
                'last_accessed': 19  # Very recent
            },
            {
                'file': 'file_ops.py',
                'code': 'def write_file(path, content): open(path, "w").write(content)',
                'start_line': 5,
                'last_accessed': 5   # Old
            }
        ]
        
        ranked_snippets = self.prioritizer.prioritize_code_snippets(
            test_snippets, current_context, current_turn=current_turn
        )
        
        print("Expected: Recent access should boost ranking")
        print("Actual ranking:")
        for i, snippet in enumerate(ranked_snippets):
            score = snippet['_relevance_score']
            print(f"  {i+1}. Line {snippet['start_line']} (final: {score.final_score:.3f}, recency: {score.recency_score:.3f}, last_accessed: {snippet['last_accessed']})")
        
        # Validate that more recent snippet ranks higher
        recent_snippet = next(s for s in ranked_snippets if s['last_accessed'] == 19)
        old_snippet = next(s for s in ranked_snippets if s['last_accessed'] == 5)
        
        recent_score = recent_snippet['_relevance_score'].final_score
        old_score = old_snippet['_relevance_score'].final_score
        success = recent_score > old_score
        
        print(f"✅ PASS: Recent access boosted ranking" if success else f"❌ FAIL: Recency not properly weighted")
        self.test_results.append(("Recency Impact", success))
    
    def test_error_priority(self):
        """Test error priority scoring."""
        print("\n🚨 TEST 3: Error Priority")
        print("-" * 40)
        
        current_context = "investigating system issues"
        
        test_snippets = [
            {
                'file': 'error_handler.py',
                'code': 'try:\n    process_data()\nexcept Exception as e:\n    logger.error(f"Critical error: {e}")\n    raise',
                'start_line': 10,
                'last_accessed': 10
            },
            {
                'file': 'data_processor.py',
                'code': 'def process_data():\n    # Normal processing logic\n    return clean_data(raw_data)',
                'start_line': 5,
                'last_accessed': 10
            }
        ]
        
        ranked_snippets = self.prioritizer.prioritize_code_snippets(
            test_snippets, current_context, current_turn=15
        )
        
        print("Expected: Error-related code should rank higher")
        print("Actual ranking:")
        for i, snippet in enumerate(ranked_snippets):
            score = snippet['_relevance_score']
            print(f"  {i+1}. {snippet['file']} (final: {score.final_score:.3f}, error: {score.error_priority:.3f})")
        
        # Validate that error-related snippet ranks higher
        error_snippet = next(s for s in ranked_snippets if 'error' in s['code'].lower())
        normal_snippet = next(s for s in ranked_snippets if 'error' not in s['code'].lower())
        
        error_score = error_snippet['_relevance_score'].error_priority
        normal_score = normal_snippet['_relevance_score'].error_priority
        success = error_score > normal_score
        
        print(f"✅ PASS: Error content prioritized" if success else f"❌ FAIL: Error priority not working")
        self.test_results.append(("Error Priority", success))
    
    def test_context_coherence(self):
        """Test context coherence scoring."""
        print("\n🔗 TEST 4: Context Coherence")
        print("-" * 40)
        
        current_context = "working on API endpoints and database models"
        
        test_snippets = [
            {
                'file': 'api/endpoints.py',
                'code': '@app.route("/users")\ndef get_users():\n    return User.query.all()',
                'start_line': 15,
                'last_accessed': 10
            },
            {
                'file': 'models/user.py',
                'code': 'class User(db.Model):\n    id = db.Column(db.Integer, primary_key=True)',
                'start_line': 3,
                'last_accessed': 10
            },
            {
                'file': 'tests/test_random.py',
                'code': 'def test_random_function():\n    assert random.randint(1, 10) > 0',
                'start_line': 8,
                'last_accessed': 10
            }
        ]
        
        ranked_snippets = self.prioritizer.prioritize_code_snippets(
            test_snippets, current_context, current_turn=15
        )
        
        print("Expected: API and model files should rank higher than random test")
        print("Actual ranking:")
        for i, snippet in enumerate(ranked_snippets):
            score = snippet['_relevance_score']
            print(f"  {i+1}. {snippet['file']} (final: {score.final_score:.3f}, coherence: {score.context_coherence:.3f})")
        
        # Validate that relevant files rank higher
        relevant_files = [s for s in ranked_snippets if any(keyword in s['file'] for keyword in ['api', 'model'])]
        irrelevant_files = [s for s in ranked_snippets if not any(keyword in s['file'] for keyword in ['api', 'model'])]
        
        if relevant_files and irrelevant_files:
            relevant_score = relevant_files[0]['_relevance_score'].final_score
            irrelevant_score = irrelevant_files[0]['_relevance_score'].final_score
            success = relevant_score > irrelevant_score
            print(f"✅ PASS: Contextually relevant files prioritized" if success else f"❌ FAIL: Context coherence not working")
            self.test_results.append(("Context Coherence", success))
        else:
            print("⚠️  SKIP: Not enough variety in test data")
            self.test_results.append(("Context Coherence", True))
    
    def test_frequency_score(self):
        """Test frequency scoring based on existing relevance."""
        print("\n📈 TEST 5: Frequency Score")
        print("-" * 40)
        
        current_context = "general development work"
        
        test_snippets = [
            {
                'file': 'frequently_used.py',
                'code': 'def common_utility(): pass',
                'start_line': 1,
                'last_accessed': 10,
                'relevance_score': 8.5  # High existing relevance
            },
            {
                'file': 'rarely_used.py',
                'code': 'def rare_function(): pass',
                'start_line': 1,
                'last_accessed': 10,
                'relevance_score': 1.2  # Low existing relevance
            }
        ]
        
        ranked_snippets = self.prioritizer.prioritize_code_snippets(
            test_snippets, current_context, current_turn=15
        )
        
        print("Expected: Frequently accessed code should rank higher")
        print("Actual ranking:")
        for i, snippet in enumerate(ranked_snippets):
            score = snippet['_relevance_score']
            print(f"  {i+1}. {snippet['file']} (final: {score.final_score:.3f}, frequency: {score.frequency_score:.3f}, existing_relevance: {snippet.get('relevance_score', 1.0)})")
        
        # Validate that frequently used snippet ranks higher
        frequent_snippet = next(s for s in ranked_snippets if s.get('relevance_score', 1.0) > 5)
        rare_snippet = next(s for s in ranked_snippets if s.get('relevance_score', 1.0) < 5)
        
        frequent_score = frequent_snippet['_relevance_score'].frequency_score
        rare_score = rare_snippet['_relevance_score'].frequency_score
        success = frequent_score > rare_score
        
        print(f"✅ PASS: Frequency scoring working" if success else f"❌ FAIL: Frequency not properly weighted")
        self.test_results.append(("Frequency Score", success))
    
    def test_end_to_end_ranking(self):
        """Test comprehensive end-to-end ranking scenario."""
        print("\n🎯 TEST 6: End-to-End Ranking")
        print("-" * 40)
        
        current_context = "fixing authentication bug in login system with database connection issues"
        current_turn = 25
        
        test_snippets = [
            {
                'file': 'auth/login.py',
                'code': 'def login(username, password):\n    try:\n        user = authenticate(username, password)\n    except DatabaseError as e:\n        logger.error(f"DB connection failed: {e}")\n        raise',
                'start_line': 10,
                'last_accessed': 24,  # Very recent
                'relevance_score': 3.2
            },
            {
                'file': 'database/connection.py',
                'code': 'def connect_to_db():\n    try:\n        return psycopg2.connect(DATABASE_URL)\n    except Exception as e:\n        raise DatabaseError(f"Connection failed: {e}")',
                'start_line': 5,
                'last_accessed': 20,  # Recent
                'relevance_score': 2.1
            },
            {
                'file': 'utils/formatting.py',
                'code': 'def format_username(username):\n    return username.strip().lower()',
                'start_line': 8,
                'last_accessed': 10,  # Old
                'relevance_score': 1.5
            },
            {
                'file': 'tests/test_math.py',
                'code': 'def test_addition():\n    assert 2 + 2 == 4',
                'start_line': 3,
                'last_accessed': 5,   # Very old
                'relevance_score': 1.0
            }
        ]
        
        ranked_snippets = self.prioritizer.prioritize_code_snippets(
            test_snippets, current_context, current_turn=current_turn
        )
        
        print("Expected ranking based on context (auth bug + DB issues):")
        print("  1. auth/login.py (recent, relevant, has error handling)")
        print("  2. database/connection.py (relevant to DB issues)")
        print("  3. utils/formatting.py (somewhat relevant to auth)")
        print("  4. tests/test_math.py (irrelevant)")
        
        print("\nActual ranking:")
        for i, snippet in enumerate(ranked_snippets):
            score = snippet['_relevance_score']
            print(f"  {i+1}. {snippet['file']} (final: {score.final_score:.3f})")
            print(f"      Content: {score.content_relevance:.3f}, Recency: {score.recency_score:.3f}")
            print(f"      Frequency: {score.frequency_score:.3f}, Error: {score.error_priority:.3f}")
            print(f"      Coherence: {score.context_coherence:.3f}")
        
        # Validate expected ranking
        file_order = [s['file'] for s in ranked_snippets]
        
        # Check that auth/login.py is ranked highest
        auth_first = file_order[0] == 'auth/login.py'
        
        # Check that database file is ranked higher than test file
        db_index = next(i for i, f in enumerate(file_order) if 'database' in f)
        test_index = next(i for i, f in enumerate(file_order) if 'test_math' in f)
        db_before_test = db_index < test_index
        
        success = auth_first and db_before_test
        
        print(f"\n✅ PASS: Ranking follows expected priority" if success else f"❌ FAIL: Unexpected ranking order")
        self.test_results.append(("End-to-End Ranking", success))
    
    def test_tool_results_prioritization(self):
        """Test tool results prioritization."""
        print("\n🔧 TEST 7: Tool Results Prioritization")
        print("-" * 40)
        
        current_context = "debugging file read errors"
        current_turn = 15
        
        tool_results = [
            {
                'tool': 'read_file',
                'summary': 'Successfully read config.py file',
                'turn': 14,
                'is_error': False
            },
            {
                'tool': 'execute_vetted_shell_command',
                'summary': 'FileNotFoundError: config.py not found',
                'turn': 13,
                'is_error': True
            },
            {
                'tool': 'list_directory',
                'summary': 'Listed files in current directory',
                'turn': 10,
                'is_error': False
            }
        ]
        
        ranked_results = self.prioritizer.prioritize_tool_results(
            tool_results, current_context, current_turn=current_turn
        )
        
        print("Expected: Error results should rank highest, then recent file operations")
        print("Actual ranking:")
        for i, result in enumerate(ranked_results):
            score = result['_relevance_score']
            error_indicator = " ❌" if result.get('is_error') else ""
            print(f"  {i+1}. {result['tool']} (turn {result['turn']}){error_indicator} (final: {score.final_score:.3f})")
        
        # Validate that error result ranks highest
        error_result = next(r for r in ranked_results if r.get('is_error'))
        error_index = ranked_results.index(error_result)
        success = error_index == 0
        
        print(f"✅ PASS: Error result prioritized" if success else f"❌ FAIL: Error not ranked highest")
        self.test_results.append(("Tool Results Prioritization", success))
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("📋 VALIDATION SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for _, success in self.test_results if success)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        
        print("\nDetailed results:")
        for test_name, success in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}: {test_name}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Smart Prioritization is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Review implementation.")
        
        return passed == total

def main():
    """Run the smart prioritization validation."""
    validator = SmartPrioritizationValidator()
    
    success = validator.run_all_tests()
    
    if success:
        print("\n🚀 Smart Prioritization validation completed successfully!")
        return 0
    else:
        print("\n💥 Smart Prioritization validation failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 