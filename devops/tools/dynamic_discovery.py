"""Dynamic tool and capability discovery for adaptive DevOps environments."""

import logging
import subprocess
import shutil
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ToolCapability:
    """Represents a discovered tool capability."""
    name: str
    version: str
    available: bool
    path: str
    description: str
    common_commands: List[str]

@dataclass
class EnvironmentCapabilities:
    """Represents the discovered environment capabilities."""
    tools: Dict[str, ToolCapability]
    shell: str
    os_type: str
    working_directory: str
    python_version: str
    package_managers: List[str]

class DynamicToolDiscovery:
    """Discovers available tools and environment capabilities."""
    
    def __init__(self):
        self.capabilities_cache: Optional[EnvironmentCapabilities] = None
        
        # Define tools to discover
        self.tool_definitions = {
            'git': {
                'check_command': ['git', '--version'],
                'description': 'Version control system',
                'common_commands': ['status', 'log', 'diff', 'branch', 'checkout', 'commit', 'push', 'pull']
            },
            'docker': {
                'check_command': ['docker', '--version'],
                'description': 'Container platform',
                'common_commands': ['ps', 'images', 'build', 'run', 'exec', 'logs', 'stop']
            },
            'kubectl': {
                'check_command': ['kubectl', 'version', '--client', '--short'],
                'description': 'Kubernetes CLI',
                'common_commands': ['get', 'describe', 'logs', 'exec', 'apply', 'delete']
            },
            'gh': {
                'check_command': ['gh', '--version'],
                'description': 'GitHub CLI',
                'common_commands': ['repo', 'pr', 'issue', 'workflow', 'auth']
            },
            'jira': {
                'check_command': ['jira', 'version'],
                'description': 'Jira CLI',
                'common_commands': ['issue', 'project', 'sprint']
            },
            'terraform': {
                'check_command': ['terraform', '--version'],
                'description': 'Infrastructure as Code',
                'common_commands': ['init', 'plan', 'apply', 'destroy', 'validate']
            },
            'ansible': {
                'check_command': ['ansible', '--version'],
                'description': 'Configuration management',
                'common_commands': ['playbook', 'vault', 'galaxy']
            },
            'helm': {
                'check_command': ['helm', 'version', '--short'],
                'description': 'Kubernetes package manager',
                'common_commands': ['install', 'upgrade', 'list', 'status', 'delete']
            },
            'aws': {
                'check_command': ['aws', '--version'],
                'description': 'AWS CLI',
                'common_commands': ['s3', 'ec2', 'iam', 'cloudformation', 'logs']
            },
            'gcloud': {
                'check_command': ['gcloud', '--version'],
                'description': 'Google Cloud CLI',
                'common_commands': ['compute', 'container', 'sql', 'storage', 'iam']
            },
            'az': {
                'check_command': ['az', '--version'],
                'description': 'Azure CLI',
                'common_commands': ['vm', 'storage', 'network', 'group', 'account']
            }
        }
    
    def discover_environment_capabilities(self, force_refresh: bool = False) -> EnvironmentCapabilities:
        """Discover and cache environment capabilities."""
        if self.capabilities_cache is None or force_refresh:
            logger.info("DISCOVERY: Starting environment capability discovery...")
            
            # Discover basic environment info
            shell = os.environ.get('SHELL', 'unknown')
            os_type = os.name
            working_directory = os.getcwd()
            
            # Discover Python version
            try:
                python_version = subprocess.check_output(['python3', '--version'], stderr=subprocess.STDOUT, text=True).strip()
            except:
                try:
                    python_version = subprocess.check_output(['python', '--version'], stderr=subprocess.STDOUT, text=True).strip()
                except:
                    python_version = "Unknown"
            
            # Discover package managers
            package_managers = []
            for pm in ['uv', 'pip', 'pipenv', 'poetry', 'conda']:
                if shutil.which(pm):
                    package_managers.append(pm)
            
            # Discover tools
            discovered_tools = {}
            for tool_name, tool_def in self.tool_definitions.items():
                capability = self._discover_tool(tool_name, tool_def)
                discovered_tools[tool_name] = capability
                
                if capability.available:
                    logger.info(f"DISCOVERY: ✅ {tool_name} v{capability.version} available at {capability.path}")
                else:
                    logger.info(f"DISCOVERY: ❌ {tool_name} not available")
            
            self.capabilities_cache = EnvironmentCapabilities(
                tools=discovered_tools,
                shell=shell,
                os_type=os_type,
                working_directory=working_directory,
                python_version=python_version,
                package_managers=package_managers
            )
            
            logger.info(f"DISCOVERY: Environment discovery complete. Found {len([t for t in discovered_tools.values() if t.available])} available tools.")
            
        return self.capabilities_cache
    
    def _discover_tool(self, tool_name: str, tool_def: Dict) -> ToolCapability:
        """Discover a specific tool capability."""
        try:
            # Check if tool is in PATH
            tool_path = shutil.which(tool_name)
            if not tool_path:
                return ToolCapability(
                    name=tool_name,
                    version="N/A",
                    available=False,
                    path="",
                    description=tool_def['description'],
                    common_commands=tool_def['common_commands']
                )
            
            # Get version information
            try:
                result = subprocess.run(
                    tool_def['check_command'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version = self._extract_version(result.stdout or result.stderr)
                    available = True
                else:
                    version = "Error getting version"
                    available = False
            except subprocess.TimeoutExpired:
                version = "Timeout"
                available = False
            except Exception as e:
                version = f"Error: {e}"
                available = False
                
            return ToolCapability(
                name=tool_name,
                version=version,
                available=available,
                path=tool_path,
                description=tool_def['description'],
                common_commands=tool_def['common_commands']
            )
            
        except Exception as e:
            logger.debug(f"Error discovering {tool_name}: {e}")
            return ToolCapability(
                name=tool_name,
                version="Error",
                available=False,
                path="",
                description=tool_def['description'],
                common_commands=tool_def['common_commands']
            )
    
    def _extract_version(self, version_output: str) -> str:
        """Extract version number from command output."""
        lines = version_output.strip().split('\n')
        for line in lines:
            if line and not line.startswith('#'):
                # Extract first version-like pattern
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+)', line)
                if version_match:
                    return version_match.group(1)
                # Fallback to first line
                return line.strip()
        return "Unknown"
    
    def get_available_commands_for_tool(self, tool_name: str) -> List[str]:
        """Get available commands for a specific tool."""
        capabilities = self.discover_environment_capabilities()
        tool = capabilities.tools.get(tool_name)
        
        if tool and tool.available:
            return tool.common_commands
        return []
    
    def suggest_tools_for_task(self, task_description: str) -> List[str]:
        """Suggest available tools based on task description."""
        capabilities = self.discover_environment_capabilities()
        task_lower = task_description.lower()
        
        suggestions = []
        
        # Simple keyword-based suggestions
        tool_keywords = {
            'git': ['git', 'version control', 'commit', 'branch', 'repository'],
            'docker': ['docker', 'container', 'containerize', 'build image'],
            'kubectl': ['kubernetes', 'k8s', 'cluster', 'pod', 'deployment'],
            'gh': ['github', 'pull request', 'pr', 'issue', 'workflow'],
            'terraform': ['infrastructure', 'terraform', 'aws', 'cloud resources'],
            'ansible': ['ansible', 'configuration', 'playbook', 'automation'],
            'helm': ['helm', 'chart', 'kubernetes package'],
            'aws': ['aws', 'amazon', 's3', 'ec2', 'lambda'],
            'gcloud': ['google cloud', 'gcp', 'compute engine'],
            'az': ['azure', 'microsoft cloud']
        }
        
        for tool_name, keywords in tool_keywords.items():
            tool = capabilities.tools.get(tool_name)
            if tool and tool.available:
                if any(keyword in task_lower for keyword in keywords):
                    suggestions.append(tool_name)
        
        return suggestions
    
    def generate_environment_summary(self) -> str:
        """Generate a summary of the environment capabilities."""
        capabilities = self.discover_environment_capabilities()
        
        summary = []
        summary.append("ENVIRONMENT CAPABILITIES SUMMARY")
        summary.append("=" * 40)
        summary.append(f"Shell: {capabilities.shell}")
        summary.append(f"OS: {capabilities.os_type}")
        summary.append(f"Python: {capabilities.python_version}")
        summary.append(f"Package Managers: {', '.join(capabilities.package_managers)}")
        summary.append(f"Working Directory: {capabilities.working_directory}")
        summary.append("")
        
        available_tools = [t for t in capabilities.tools.values() if t.available]
        summary.append(f"AVAILABLE TOOLS ({len(available_tools)}):")
        
        for tool in available_tools:
            summary.append(f"  ✅ {tool.name} v{tool.version} - {tool.description}")
        
        unavailable_tools = [t for t in capabilities.tools.values() if not t.available]
        if unavailable_tools:
            summary.append("")
            summary.append(f"UNAVAILABLE TOOLS ({len(unavailable_tools)}):")
            for tool in unavailable_tools:
                summary.append(f"  ❌ {tool.name} - {tool.description}")
        
        return "\n".join(summary)

# Global instance for easy access
tool_discovery = DynamicToolDiscovery() 