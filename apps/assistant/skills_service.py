import logging
import traceback
import sys
import io

logger = logging.getLogger(__name__)

class SkillsService:
    """
    Skills Service for executing dynamic Python code snippets.
    """
    
    @staticmethod
    def execute_skill(code, context=None):
        """
        Execute a Python skill with a given context.
        """
        context = context or {}
        
        # Redirect stdout to capture print statements
        old_stdout = sys.stdout
        new_stdout = io.StringIO()
        sys.stdout = new_stdout
        
        # Global and local variables for the execution environment
        globals_dict = {
            "__builtins__": __builtins__,
            "context": context,
        }
        
        try:
            # Execute the code
            exec(code, globals_dict)
            
            # Get output from captured stdout
            output = new_stdout.getvalue()
            
            # Return results (assume the skill sets a 'result' variable)
            return {
                "success": True,
                "output": output,
                "result": globals_dict.get("result", None)
            }
        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"Skill execution failed: {error_msg}")
            return {
                "success": False,
                "error": str(e),
                "traceback": error_msg
            }
        finally:
            sys.stdout = old_stdout
