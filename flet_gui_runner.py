# flet_gui_runner.py (V3 Integration - Focus Fix Applied)

import flet as ft
import logging
import os
import sys
from dotenv import load_dotenv
import threading
import time

# Import Acrea core components
from acrea_coordinator import AcreaCoordinator
from chat_module import ChatModule
from vector_memory_module import VectorMemoryModule
from embedding_module import EmbeddingModule
from system_prompt_module import ACREA_SYSTEM_PROMPT
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Import the V3 GUI Design
from flet_gui_design_v3 import AcreaFletUI_V3, COLOR_BACKGROUND, COLOR_ON_SURFACE # Import colors if needed

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AcreaFletRunnerV3")

# --- Globals ---
coordinator_instance: AcreaCoordinator = None
# ui_design instance will be created within main

# --- Configuration (Assume these are correct from previous steps) ---
load_dotenv()
# ... (GEMINI_API_KEY_ENV, VDB_*, ACREA_MODEL_NAME, etc. remain the same) ...
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
VDB_API_ENDPOINT_ENV = "VDB_API_ENDPOINT"
VDB_INDEX_ENDPOINT_ENV = "VDB_INDEX_ENDPOINT_RESOURCE_NAME"
VDB_DEPLOYED_INDEX_ID_ENV = "VDB_DEPLOYED_INDEX_ID"
ACREA_MODEL_NAME = "gemini-2.5-pro-exp-03-25"
DEFAULT_GENERATION_CONFIG = { "temperature": 0.8, "top_p": 0.95, "top_k": 64, "max_output_tokens": 8192 }
DEFAULT_SAFETY_SETTINGS = { HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE }

# --- Placeholder Data Fetching ---
def fetch_text_content_by_ids(neighbor_ids: list[str]) -> dict[str, str]:
    logger.info(f"Attempting to fetch content for IDs: {neighbor_ids}")
    fetched_content = {id_: f"Placeholder text content for ID: {id_}." for id_ in neighbor_ids}
    logger.warning("Using PLACEHOLDER data fetching. Implement actual retrieval!")
    return fetched_content

# --- Initialization Function (Mostly unchanged) ---
def initialize_acrea_system():
    global coordinator_instance
    # ... (Same initialization logic as before: load config, init coordinator, init/register modules) ...
    logger.info("Initializing Acrea Coordinator and Modules for Flet GUI V3...")
    config = { key: os.environ.get(key) for key in [GEMINI_API_KEY_ENV, VDB_API_ENDPOINT_ENV, VDB_INDEX_ENDPOINT_ENV, VDB_DEPLOYED_INDEX_ID_ENV] }
    missing_keys = [key for key, val in config.items() if not val]
    if missing_keys: raise ValueError(f"Missing required configuration: {', '.join(missing_keys)}")
    logger.info("Configuration validated.")

    coordinator = AcreaCoordinator()
    try:
        # Ensure arguments are passed correctly
        chat_module = ChatModule(
            api_key=config[GEMINI_API_KEY_ENV],
            model_name=ACREA_MODEL_NAME,
            system_instruction=ACREA_SYSTEM_PROMPT,
            generation_config=DEFAULT_GENERATION_CONFIG,
            safety_settings=DEFAULT_SAFETY_SETTINGS
        )
        coordinator.register_module("chat", chat_module)
        vector_memory_module = VectorMemoryModule(
            api_endpoint=config[VDB_API_ENDPOINT_ENV],
            index_endpoint_name=config[VDB_INDEX_ENDPOINT_ENV],
            deployed_index_id=config[VDB_DEPLOYED_INDEX_ID_ENV]
        )
        coordinator.register_module("vector_memory", vector_memory_module)
        embedding_module = EmbeddingModule()
        coordinator.register_module("embedding", embedding_module)
    except Exception as e:
        logger.error(f"Failed to initialize modules: {e}", exc_info=True)
        raise
    coordinator_instance = coordinator
    logger.info("Coordinator and modules initialized.")


# --- Flet Application Main Function (V3) ---

def main(page: ft.Page):
    global coordinator_instance

    # --- Page Setup for Desktop App Feel ---
    page.title = "Acrea - AI Architecture Assistant"
    page.theme_mode = ft.ThemeMode.DARK # Apply Dark Theme
    page.bgcolor = COLOR_BACKGROUND # Use custom dark background

    # Window controls
    page.window_resizable = True
    page.window_maximizable = True
    page.window_minimizable = True
    page.window_width = 850
    page.window_height = 700
    page.window_min_height = 500
    page.window_min_width = 600

    # Instantiate the V3 UI design
    ui_design = AcreaFletUI_V3()

    # --- Safe UI Update Function ---
    def update_ui_safe(update_func, *args, **kwargs):
        try:
             update_func(*args, **kwargs)
        except Exception as ui_update_err:
             logger.error(f"Error updating UI from background: {ui_update_err}", exc_info=True)


    # --- Background Processing Function ---
    def process_request_in_background(user_input: str):
        if not coordinator_instance: return
        retrieved_context_str = None
        ai_response = "Error during processing."
        try:
            logger.info(f"Background processing V3: '{user_input[:50]}...'")
            # --- RAG Logic ---
            embedding_message = {"target_module": "embedding", "action": "generate_embedding", "payload": {"text": user_input, "task_type": "RETRIEVAL_QUERY"}}
            query_vector = coordinator_instance.route_message(embedding_message)
            if query_vector:
                search_message = {"target_module": "vector_memory", "action": "find_neighbors", "payload": {"query_vector": query_vector, "num_neighbors": 3}}
                neighbors = coordinator_instance.route_message(search_message)
                if neighbors:
                     neighbor_ids = [n['id'] for n in neighbors]
                     fetched_texts_map = fetch_text_content_by_ids(neighbor_ids)
                     context_pieces = [f"Source ID: {n['id']}\nContent: {fetched_texts_map.get(n['id'], 'Not found.')}\n---" for n in neighbors]
                     if context_pieces: retrieved_context_str = "Found potentially relevant information:\n\n" + "\n".join(context_pieces)

            # --- Generate Final Response ---
            chat_message = {"target_module": "chat", "action": "generate_response", "payload": {"prompt": user_input, "context": retrieved_context_str}}
            ai_response = coordinator_instance.route_message(chat_message)
            if ai_response is None: ai_response = "Sorry, encountered an issue."

        except Exception as e:
            logger.error(f"Error processing request in background: {e}", exc_info=True)
            ai_response = f"Error: Processing failed.\nDetails: {e}"
        finally:
            # --- Safely Update Flet UI from Background ---
            ui_design.add_message_animated("Acrea", ai_response)
            ui_design.set_thinking_status(False)
            ui_design.reset_send_button_animation()

            # Refocus input field - CORRECTED
            try:
                # page.focus(ui_design.input_field) # OLD INCORRECT LINE
                ui_design.input_field.focus()      # CORRECTED LINE
            except Exception as focus_err:
                logger.warning(f"Could not refocus input field: {focus_err}")

            # Update relevant controls if needed (often handled by control-specific updates)
            page.update() # Update page to reflect changes from background thread


    # --- Event Handler for Sending Message ---
    def send_message_handler(e):
        user_input = ui_design.input_field.value.strip()
        if not user_input or ui_design.send_button.disabled: return
        logger.info("Send triggered V3.")
        ui_design.add_message_animated("You", user_input)
        ui_design.clear_input()
        ui_design.trigger_send_button_animation()
        ui_design.set_thinking_status(True)
        page.update()
        thread = threading.Thread(target=process_request_in_background, args=(user_input,))
        thread.daemon = True
        thread.start()

    # --- Connect Event Handlers ---
    ui_design.send_button.on_click = send_message_handler
    ui_design.input_field.on_submit = send_message_handler

    # --- Add layout to page ---
    page.add(ui_design.get_layout())
    page.update()

    # Initial focus - CORRECTED
    # page.focus(ui_design.input_field) # OLD INCORRECT LINE
    ui_design.input_field.focus()      # CORRECTED LINE
    page.update()


# --- Main Execution ---
if __name__ == "__main__":
    try:
        initialize_acrea_system()
        logger.info("Acrea backend initialized. Starting Flet GUI V3...")
        ft.app(target=main, assets_dir="assets")
        logger.info("Flet application stopped.")
    except Exception as init_error:
        logger.critical(f"Failed to initialize or run Acrea Flet GUI: {init_error}", exc_info=True)
        print(f"FATAL: Acrea could not start: {init_error}. Check logs.", file=sys.stderr)
        sys.exit(1)