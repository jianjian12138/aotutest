import os
import ast
import subprocess
import logging
from typing import List, Dict, Set, Any
from django.conf import settings

logger = logging.getLogger(__name__)

class GitImpactAnalyzer:
    """
    V3.2 Predictive QA Engine:
    Analyzes Git diffs and maps them to application components.
    """
    
    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or settings.BASE_DIR
        
    def get_changed_files(self, base_branch: str = "main", head_branch: str = "HEAD") -> List[str]:
        """
        Gets the list of files changed between two branches/commits.
        """
        try:
            cmd = ["git", "diff", "--name-only", base_branch, head_branch]
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, check=True)
            files = [f for f in result.stdout.split('\n') if f]
            return files
        except Exception as e:
            logger.error(f"Git diff failed: {e}")
            return []

    def scan_file_dependencies(self, file_path: str) -> Set[str]:
        """
        Uses AST to find what this file imports or what functions are defined.
        Simplified version for V3.2 demo.
        """
        abs_path = os.path.join(self.repo_path, file_path)
        if not os.path.exists(abs_path) or not file_path.endswith('.py'):
            return set()
            
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        imports.add(n.name)
                elif isinstance(node, ast.ImportFrom):
                    imports.add(node.module)
            return imports
        except Exception as e:
            logger.error(f"AST scan failed for {file_path}: {e}")
            return set()

    def analyze_impact(self, target_commit: str = "HEAD") -> Dict[str, Any]:
        """
        Main entry point for impact analysis.
        Returns a list of changed files and their 'risk score'.
        """
        changed_files = self.get_changed_files(head_branch=target_commit)
        impact_results = []
        
        for file in changed_files:
            risk_level = "Medium"
            impact_type = "Unknown"
            
            if file.startswith('backend/'):
                risk_level = "High"
                impact_type = "API Logic"
            elif file.startswith('frontend/'):
                risk_level = "Medium"
                impact_type = "UI Component"
            elif file.endswith('.yaml') or file.endswith('.json'):
                risk_level = "Low"
                impact_type = "Configuration"
            
            # Simple heuristic: if it's a model or view, it's critical
            if "views.py" in file or "models.py" in file:
                 risk_level = "CRITICAL"
            
            impact_results.append({
                "file": file,
                "type": impact_type,
                "risk": risk_level,
                "suggested_tests": self._suggest_tests_for(file)
            })
            
        return {
            "commit": target_commit,
            "changed_count": len(changed_files),
            "impact_items": impact_results
        }

    def _suggest_tests_for(self, file_path: str) -> List[str]:
        """
        Maps a file path to potential test cases in the DB.
        In a real system, this would query a mapping table.
        """
        # Mock mapping for V3.2
        if "api-testing" in file_path or "interfaces" in file_path:
            return ["API Regression Set A", "Protocol Validation"]
        if "ui-automation" in file_path or "elements" in file_path:
            return ["UI Smoketest", "Element Stability Test"]
        return ["General Regression"]

if __name__ == "__main__":
    analyzer = GitImpactAnalyzer()
    print(analyzer.analyze_impact())
