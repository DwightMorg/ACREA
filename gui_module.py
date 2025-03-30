# gui_module.py

import tkinter as tk
import logging
import os
import sys
from dotenv import load_dotenv
import threading # For running coordinator calls in a separate thread

# Import Acrea core components
from acrea_coordinator import AcreaCoordinator
from chat_module import ChatModule
from vector_memory_module import VectorMemoryModule
from embedding_module import EmbeddingModule
from system_prompt_module import ACREA_SYSTEM_PROMPT
import google.generativeai as genai # Needed for safety types
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Import the GUI Design
from gui_design import AcreaGUI

# --- Basic Logging Setup (Configure as needed) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AcreaGUIModule")

# --- Global Coordinator Instance ---
# We need a global coordinator instance accessible by the callback
# Ensure this is initialized only once in main()
coordinator_instance: AcreaCoordinator = None
gui_instance: AcreaGUI = None

# --- Configuration (Copied/Adapted from gemini_2.5.py) ---
# Load .env - should happen before accessing os.environ
load_dotenv()
logger.info("Loaded environment variables from .env")

# Config Keys
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
VDB_API_ENDPOINT_ENV = "VDB_API_ENDPOINT"
VDB_INDEX_ENDPOINT_ENV = "VDB_INDEX_ENDPOINT_RESOURCE_NAME"
VDB_DEPLOYED_INDEX_ID_ENV = "VDB_DEPLOYED_INDEX_ID"

# Gemini/Chat Config
ACREA_MODEL_NAME = "gemini-2.5-pro-exp-03-25" # Or "gemini-1.5-flash-latest"
DEFAULT_GENERATION_CONFIG = { "temperature": 0.8, "top_p": 0.95, "top_k": 64, "max_output_tokens": 8192 }
DEFAULT_SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# --- Placeholder Data Fetching (Same as before) ---
def fetch_text_content_by_ids(neighbor_ids: list[str]) -> dict[str, str]:
    logger.info(f"Attempting to fetch content for IDs: {neighbor_ids}")
    fetched_content = {id_: f"Placeholder text content for ID: {id_}." for id_ in neighbor_ids}
    logger.warning("Using PLACEHOLDER data fetching. Implement actual retrieval!")
    return fetched_content

# --- Initialization Function (Similar to gemini_2.5.py) ---
def initialize_acrea_system():
    """Loads config, initializes coordinator and modules, registers them."""
    global coordinator_instance # Make sure we modify the global instance
    logger.info("Initializing Acrea Coordinator and Modules for GUI...")
    config = {
        GEMINI_API_KEY_ENV: os.environ.get(GEMINI_API_KEY_ENV),
        VDB_API_ENDPOINT_ENV: os.environ.get(VDB_API_ENDPOINT_ENV),
        VDB_INDEX_ENDPOINT_ENV: os.environ.get(VDB_INDEX_ENDPOINT_ENV),
        VDB_DEPLOYED_INDEX_ID_ENV: os.environ.get(VDB_DEPLOYED_INDEX_ID_ENV),
    }
    required_keys = [GEMINI_API_KEY_ENV, VDB_API_ENDPOINT_ENV, VDB_INDEX_ENDPOINT_ENV, VDB_DEPLOYED_INDEX_ID_ENV]
    missing_keys = [key for key in required_keys if not config.get(key)]
    if missing_keys:
        raise ValueError(f"Missing required configuration: {', '.join(missing_keys)}")
    logger.info("Configuration validated.")

    coordinator = AcreaCoordinator()
    try:
        chat_module = ChatModule(
            api_key=config[GEMINI_API_KEY_ENV], model_name=ACREA_MODEL_NAME,
            system_instruction=ACREA_SYSTEM_PROMPT, generation_config=DEFAULT_GENERATION_CONFIG,
            safety_settings=DEFAULT_SAFETY_SETTINGS
        )
        coordinator.register_module("chat", chat_module)
        vector_memory_module = VectorMemoryModule(
            api_endpoint=config[VDB_API_ENDPOINT_ENV], index_endpoint_name=config[VDB_INDEX_ENDPOINT_ENV],
            deployed_index_id=config[VDB_DEPLOYED_INDEX_ID_ENV]
        )
        coordinator.register_module("vector_memory", vector_memory_module)
        embedding_module = EmbeddingModule()
        coordinator.register_module("embedding", embedding_module)
        # Register other modules like TTS if needed
    except Exception as e:
        logger.error(f"Failed to initialize modules: {e}", exc_info=True)
        raise
    coordinator_instance = coordinator # Assign to global variable
    logger.info("Coordinator and modules initialized and registered.")


# --- GUI Interaction Logic ---

def process_request_in_background(user_input: str):
    """
    Handles the logic for processing user input (RAG, Chat) via the coordinator.
    This runs in a separate thread to avoid blocking the GUI.
    """
    global coordinator_instance, gui_instance
    if not coordinator_instance or not gui_instance:
        logger.error("Coordinator or GUI not initialized.")
        gui_instance.display_message("Error", "System not fully initialized.")
        gui_instance.set_thinking_status(False)
        return

    retrieved_context_str = None
    ai_response = "An error occurred during processing." # Default error response

    try:
        logger.info(f"Background thread processing: '{user_input[:50]}...'")
        # --- RAG Orchestration ---
        embedding_message = {"target_module": "embedding", "action": "generate_embedding", "payload": {"text": user_input, "task_type": "RETRIEVAL_QUERY"}}
        query_vector = coordinator_instance.route_message(embedding_message)

        if query_vector:
            search_message = {"target_module": "vector_memory", "action": "find_neighbors", "payload": {"query_vector": query_vector, "num_neighbors": 3}}
            neighbors = coordinator_instance.route_message(search_message)
            if neighbors:
                neighbor_ids = [n['id'] for n in neighbors]
                fetched_texts_map = fetch_text_content_by_ids(neighbor_ids) # Needs implementation!
                context_pieces = []
                for neighbor in neighbors:
                    fetched_text = fetched_texts_map.get(neighbor['id'])
                    if fetched_text: context_pieces.append(f"Source ID: {neighbor['id']}\nContent: {fetched_text}\n---")
                if context_pieces: retrieved_context_str = "Found potentially relevant information:\n\n" + "\n".join(context_pieces)
                else: logger.info("No usable content fetched for retrieved neighbor IDs.")
            else: logger.info("No neighbors found in vector memory.")
        else: logger.error("Failed to generate query vector. Skipping RAG.")

        # --- Generate Final Response ---
        chat_message = {
            "target_module": "chat", "action": "generate_response",
            "payload": {"prompt": user_input, "context": retrieved_context_str}
        }
        ai_response = coordinator_instance.route_message(chat_message)
        if ai_response is None: ai_response = "Sorry, I encountered an issue generating a response."

    except Exception as e:
        logger.error(f"Error processing request in background thread: {e}", exc_info=True)
        ai_response = f"Error: {e}" # Show error in GUI
    finally:
        # --- Update GUI from the main thread ---
        # Use 'after' to schedule GUI updates safely from the background thread
        gui_instance.master.after(0, lambda: gui_instance.display_message("Acrea", ai_response))
        gui_instance.master.after(0, lambda: gui_instance.set_thinking_status(False))
        gui_instance.master.after(0, gui_instance.clear_input)


def send_message_callback_for_gui(user_input: str):
    """
    Callback function passed to the GUI. Called when the user clicks Send.
    It triggers the background processing.
    """
    global gui_instance
    if not gui_instance: return

    logger.info("Send button clicked or Enter pressed.")
    gui_instance.display_message("You", user_input) # Display user message immediately
    gui_instance.set_thinking_status(True)    # Show thinking status
    # Run the coordinator interaction in a background thread
    thread = threading.Thread(target=process_request_in_background, args=(user_input,))
    thread.daemon = True # Allows program to exit even if thread is running
    thread.start()


# --- Main Execution ---

def main():
    """Initializes the system and starts the Tkinter GUI."""
    global gui_instance
    try:
        initialize_acrea_system()
    except Exception as e:
        logger.critical(f"Failed to initialize Acrea system: {e}", exc_info=True)
        # Show error in a simple Tkinter popup if GUI can't start
        try:
            root = tk.Tk()
            root.withdraw() # Hide the main window
            tk.messagebox.showerror("Initialization Error", f"Failed to initialize Acrea: {e}\nCheck logs.")
        except Exception:
            print(f"FATAL: Failed to initialize Acrea: {e}. Check logs.", file=sys.stderr)
        sys.exit(1)

    # Create the main Tkinter window
    root = tk.Tk()
    # Instantiate the GUI design, passing the callback function
    gui_instance = AcreaGUI(root, send_message_callback_for_gui)
    # Start the Tkinter event loop
    logger.info("Starting Acrea GUI main loop...")
    root.mainloop()
    logger.info("Acrea GUI finished.")

if __name__ == "__main__":
    main()