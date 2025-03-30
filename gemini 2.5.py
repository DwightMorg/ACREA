# gemini_2.5.py (Main Application - Refactored with External System Prompt)

import os
import sys
import logging
from dotenv import load_dotenv
import google.generativeai as genai # Needed for safety types
from google.generativeai.types import HarmCategory, HarmBlockThreshold # Explicit import for safety settings

# Import the Coordinator and Modules
from acrea_coordinator import AcreaCoordinator
from chat_module import ChatModule
from vector_memory_module import VectorMemoryModule
from embedding_module import EmbeddingModule # Import the placeholder
from system_prompt_module import ACREA_SYSTEM_PROMPT # <-- Import the prompt

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AcreaMainApp")

# --- Load Environment Variables ---
load_dotenv()
logger.info("Loaded environment variables from .env")

# --- Configuration Keys ---
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
VDB_API_ENDPOINT_ENV = "VDB_API_ENDPOINT"
VDB_INDEX_ENDPOINT_ENV = "VDB_INDEX_ENDPOINT_RESOURCE_NAME"
VDB_DEPLOYED_INDEX_ID_ENV = "VDB_DEPLOYED_INDEX_ID"
# Add other keys as needed

# --- Gemini/Chat Configuration ---
ACREA_MODEL_NAME = "gemini-2.5-pro-exp-03-25" # Or "gemini-1.5-flash-latest"
# !!! ACREA_SYSTEM_PROMPT definition is REMOVED from here !!!

# Define Generation Config and Safety Settings here as they are parameters for ChatModule init
DEFAULT_GENERATION_CONFIG = {
    "temperature": 0.8,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192
}
# Ensure HarmCategory and HarmBlockThreshold are available or imported
DEFAULT_SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# --- Main Application Logic ---

def initialize_modules_and_coordinator():
    """Loads config, initializes coordinator and all functional modules, and registers them."""
    logger.info("Initializing Acrea Coordinator and Modules...")

    # 1. Load and Validate Configuration
    config = {
        GEMINI_API_KEY_ENV: os.environ.get(GEMINI_API_KEY_ENV),
        VDB_API_ENDPOINT_ENV: os.environ.get(VDB_API_ENDPOINT_ENV),
        VDB_INDEX_ENDPOINT_ENV: os.environ.get(VDB_INDEX_ENDPOINT_ENV),
        VDB_DEPLOYED_INDEX_ID_ENV: os.environ.get(VDB_DEPLOYED_INDEX_ID_ENV),
        # Add other config values here
    }

    required_keys = [
        GEMINI_API_KEY_ENV, VDB_API_ENDPOINT_ENV,
        VDB_INDEX_ENDPOINT_ENV, VDB_DEPLOYED_INDEX_ID_ENV
    ]
    missing_keys = [key for key in required_keys if not config.get(key)]
    if missing_keys:
        raise ValueError(f"Missing required configuration: {', '.join(missing_keys)}")
    logger.info("Configuration validated.")

    # 2. Instantiate Coordinator
    coordinator = AcreaCoordinator()

    # 3. Instantiate and Register Modules
    try:
        # Chat Module - Uses imported prompt
        chat_module = ChatModule(
            api_key=config[GEMINI_API_KEY_ENV],
            model_name=ACREA_MODEL_NAME,
            system_instruction=ACREA_SYSTEM_PROMPT, # <-- Use imported prompt
            generation_config=DEFAULT_GENERATION_CONFIG,
            safety_settings=DEFAULT_SAFETY_SETTINGS
        )
        coordinator.register_module("chat", chat_module)

        # Vector Memory Module
        vector_memory_module = VectorMemoryModule(
            api_endpoint=config[VDB_API_ENDPOINT_ENV],
            index_endpoint_name=config[VDB_INDEX_ENDPOINT_ENV],
            deployed_index_id=config[VDB_DEPLOYED_INDEX_ID_ENV]
        )
        coordinator.register_module("vector_memory", vector_memory_module)

        # Embedding Module (Placeholder)
        embedding_module = EmbeddingModule() # Add config if needed later
        coordinator.register_module("embedding", embedding_module)

        # Register other modules here
        # e.g., tts_module = TextToSpeechModule(...)
        # coordinator.register_module("tts", tts_module)

    except Exception as e:
        logger.error(f"Failed to initialize one or more modules: {e}", exc_info=True)
        raise # Re-raise critical initialization errors

    logger.info("Coordinator and modules initialized and registered.")
    return coordinator

def run_interaction_loop(coordinator: AcreaCoordinator):
    """Runs the main interactive CLI loop, orchestrating via the coordinator."""
    print("\n--- Acrea AI Architecture Assistant (Mediator Architecture) ---")
    print(f"Chat Model: {ACREA_MODEL_NAME}")
    print("Type 'quit' or 'exit' to end.")
    print("-" * 60)

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["quit", "exit"]:
                print("\nAcrea: Goodbye! Architecting the future awaits.")
                break
            if not user_input.strip():
                continue

            print("Acrea: ...thinking...") # Indicate processing

            # --- RAG Orchestration ---
            retrieved_context_str = None
            try:
                # 1. Get Embedding (via Coordinator)
                embedding_message = {
                    "target_module": "embedding",
                    "action": "generate_embedding",
                    "payload": {"text": user_input}
                }
                query_vector = coordinator.route_message(embedding_message)

                if query_vector:
                    logger.info("Received query vector from embedding module.")
                    # 2. Search Vector Memory (via Coordinator)
                    search_message = {
                        "target_module": "vector_memory",
                        "action": "find_neighbors",
                        "payload": {"query_vector": query_vector, "num_neighbors": 3}
                    }
                    neighbors = coordinator.route_message(search_message)

                    if neighbors:
                        logger.info(f"Retrieved {len(neighbors)} neighbors from vector memory.")
                        # --- CONTEXT FORMATTING NEEDED ---
                        formatted_neighbors = [f"ID: {n['id']} (Dist: {n['distance']:.4f})" for n in neighbors]
                        retrieved_context_str = "Found potentially relevant items:\n" + "\n".join(formatted_neighbors)
                        # --- END CONTEXT FORMATTING ---
                    else:
                        logger.info("No neighbors found in vector memory.")
                else:
                    logger.info("Skipping vector memory search (no query vector).")

            except KeyError as ke:
                 logger.error(f"RAG orchestration failed: Required module not found. {ke}")
            except Exception as rag_e:
                 logger.error(f"Error during RAG processing: {rag_e}", exc_info=True)

            # 3. Generate Final Response (via Coordinator)
            chat_message = {
                "target_module": "chat",
                "action": "generate_response",
                "payload": {
                    "prompt": user_input,
                    "context": retrieved_context_str # Pass formatted context (or None)
                }
            }
            ai_response = coordinator.route_message(chat_message)

            # Handle potential errors from chat module
            if ai_response is None:
                ai_response = "Sorry, I encountered an issue generating a response."

            # Clear "thinking" line and print response
            print(f"\rAcrea: {ai_response}    ") # \r + spaces to clear line

        except KeyboardInterrupt:
            print("\n\nAcrea: Session interrupted. Goodbye!")
            break
        except Exception as e:
            logger.error(f"\n[Error]: An unexpected error occurred in the main loop: {e}", exc_info=True)
            print("\nAn critical error occurred. Please check the logs.")

# --- Script Entry Point ---
if __name__ == "__main__":
    try:
        acrea_coordinator = initialize_modules_and_coordinator()
        run_interaction_loop(acrea_coordinator)
    except Exception as init_error:
        logger.critical(f"Failed to initialize Acrea: {init_error}", exc_info=True)
        print("\nFATAL: Acrea could not start due to an initialization error. Check logs.", file=sys.stderr)
        sys.exit(1) # Exit if initialization fails