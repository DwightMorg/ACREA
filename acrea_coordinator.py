# acrea_coordinator.py

import logging
import os
from dotenv import load_dotenv
from system_prompt_module import ACREA_SYSTEM_PROMPT

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class AcreaCoordinator:
    """
    Acts as a Mediator for communication between different AI modules
    within the main Acrea application (`gemini_2.5.py`). Modules are registered
    by the main application, and messages are routed through this coordinator.
    """
    def __init__(self):
        self.modules = {}  # Registry: module_name -> module_instance
        self.context = {}  # Optional shared context
        self.logger = logging.getLogger("AcreaCoordinator")
        # Configuration loading from .env can be managed here or in the main app
        # load_dotenv() # Load if coordinator needs direct access to config
        # self.config = os.environ
        self.logger.info("AcreaCoordinator (Mediator) initialized.")

    def register_module(self, module_name: str, module_instance: object):
        """Registers a functional module instance provided by the main application."""
        if module_name in self.modules:
             self.logger.warning(f"Re-registering module '{module_name}'. Overwriting previous instance.")
        self.modules[module_name] = module_instance
        self.logger.info(f"Module '{module_name}' registered with the coordinator.")

    def get_module(self, module_name: str):
         """Retrieves a registered module instance."""
         return self.modules.get(module_name)

    def route_message(self, message: dict):
        """
        Routes a message dictionary to the specified target module's handle_message method.

        Args:
            message: A dictionary containing message details, including:
                - 'target_module': The string name of the destination module.
                - 'action': The specific action the target module should perform.
                - 'payload': A dictionary containing the data needed for the action.

        Returns:
            The result from the target module's handle_message method, or None on error.

        Raises:
            KeyError: If 'target_module' or 'action' is missing.
            AttributeError: If the target module doesn't have 'handle_message'.
        """
        if 'target_module' not in message or 'action' not in message:
            self.logger.error("Message routing failed: Missing 'target_module' or 'action' key.")
            raise KeyError("Message dictionary must contain 'target_module' and 'action' keys.")

        target_module_name = message["target_module"]
        action = message["action"]
        payload = message.get("payload", {}) # Payload is optional

        module_instance = self.modules.get(target_module_name)

        if module_instance:
            self.logger.debug(f"Routing action '{action}' to module '{target_module_name}'.")
            try:
                # Check if module has the standard handler method
                if not hasattr(module_instance, 'handle_message'):
                     raise AttributeError(f"Module '{target_module_name}' is missing the required 'handle_message' method.")

                # Call the module's handler
                response = module_instance.handle_message(action=action, payload=payload)
                return response

            except AttributeError as ae:
                 self.logger.error(ae)
                 raise # Re-raise attribute error as it's a module implementation issue
            except Exception as e:
                 self.logger.error(f"Error executing handle_message in module '{target_module_name}' for action '{action}': {e}", exc_info=True)
                 return None # Return None on general module error during handling
        else:
            self.logger.warning(f"Routing failed: Module '{target_module_name}' not found in registry.")
            return None # Indicate routing failure

    # --- Optional Context Management ---
    def set_context(self, key: str, value: any):
        """Sets a value in the shared context."""
        self.context[key] = value
        self.logger.debug(f"Coordinator context updated: '{key}' set.")

    def get_context(self, key: str, default: any = None):
        """Gets a value from the shared context."""
        return self.context.get(key, default)