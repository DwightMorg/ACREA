# chat_module.py

import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from system_prompt_module import ACREA_SYSTEM_PROMPT

class ChatModule:
    """Handles interaction with the Gemini language model for Acrea."""
    def __init__(self, api_key: str, model_name: str, system_instruction: str,
                 generation_config: dict, safety_settings: dict):
        self.logger = logging.getLogger("ChatModule")
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name,
                system_instruction=system_instruction,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            # Start a chat session to maintain history internally
            self.chat = self.model.start_chat(history=[])
            self.logger.info(f"ChatModule initialized with model '{model_name}'.")
        except Exception as e:
            self.logger.error(f"Failed to initialize ChatModule's Gemini model: {e}", exc_info=True)
            raise

    def handle_message(self, action: str, payload: dict):
        """Handles actions directed to the chat module."""
        if action == "generate_response":
            user_prompt = payload.get("prompt")
            context_info = payload.get("context") # Optional context from RAG

            if not user_prompt:
                self.logger.warning("Generate response action received without 'prompt' in payload.")
                return "I received an empty request."

            full_prompt = user_prompt
            if context_info:
                # Basic context injection - adjust formatting as needed
                full_prompt = f"Based on the following relevant context:\n---\n{context_info}\n---\n\nPlease answer the user's query: {user_prompt}"
                self.logger.info("Injecting retrieved context into prompt for Gemini.")

            try:
                # Use the internal chat session which manages history
                response = self.chat.send_message(full_prompt) # Blocking call for simplicity
                self.logger.info("Successfully generated response from Gemini.")

                # Basic safety/completion check
                if not response.candidates or response.candidates[0].finish_reason not in (1, 0): # 1=STOP, 0=UNSPECIFIED (often ok)
                    finish_reason = response.candidates[0].finish_reason if response.candidates else 'UNKNOWN'
                    self.logger.warning(f"Gemini response finished with reason: {finish_reason}")
                    if hasattr(response, 'prompt_feedback'):
                        self.logger.warning(f"Prompt Feedback: {response.prompt_feedback}")
                    # Decide how to handle non-ideal finishes (e.g., return partial or error message)

                return response.text
            except Exception as e:
                self.logger.error(f"Error during Gemini response generation: {e}", exc_info=True)
                return "I apologize, but I encountered an error trying to generate a response."

        elif action == "get_history":
             # Example: Action to retrieve history if needed externally
             return self.chat.history
        else:
            self.logger.warning(f"ChatModule received unknown action: {action}")
            return None