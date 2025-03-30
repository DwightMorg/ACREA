# vector_memory_module.py

import logging
# Assuming vector_search_client.py is accessible
from vector_search_client import VertexVectorSearchClient
from system_prompt_module import ACREA_SYSTEM_PROMPT

class VectorMemoryModule:
    """Handles interaction with the Vertex AI Vector Search index."""
    def __init__(self, api_endpoint: str, index_endpoint_name: str, deployed_index_id: str):
        self.logger = logging.getLogger("VectorMemoryModule")
        try:
            # Use the client class we defined earlier
            self.client = VertexVectorSearchClient(
                api_endpoint=api_endpoint,
                index_endpoint_resource_name=index_endpoint_name,
                deployed_index_id=deployed_index_id,
            )
            self.logger.info("VectorMemoryModule initialized.")
        except Exception as e:
            self.logger.error(f"Failed to initialize VectorMemoryModule: {e}", exc_info=True)
            raise

    def handle_message(self, action: str, payload: dict):
        """Handles actions directed to the vector memory module."""
        if action == "find_neighbors":
            query_vector = payload.get("query_vector")
            num_neighbors = payload.get("num_neighbors", 5) # Default to 5 neighbors

            if not query_vector:
                self.logger.error("Find neighbors action received without 'query_vector' in payload.")
                return [] # Return empty list on error

            try:
                neighbors = self.client.find_neighbors(
                    query_vector=query_vector,
                    neighbor_count=num_neighbors
                )
                self.logger.info(f"Found {len(neighbors)} neighbors in vector memory.")
                # Returns list of dicts like [{'id': '...', 'distance': ...}, ...]
                return neighbors
            except Exception as e:
                self.logger.error(f"Error during vector search: {e}", exc_info=True)
                return [] # Return empty list on error
        else:
            self.logger.warning(f"VectorMemoryModule received unknown action: {action}")
            return None