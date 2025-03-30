import os
import sys
from typing import List, Dict, Any, Optional
# Import necessary Google Cloud libraries
try:
    from google.cloud import aiplatform_v1
    from google.api_core import exceptions as google_exceptions
except ImportError:
    print("Error: google-cloud-aiplatform library not found.", file=sys.stderr)
    print("Please install it using: pip install google-cloud-aiplatform", file=sys.stderr)
    sys.exit(1)


DEFAULT_API_ENDPOINT = "YOUR_API_ENDPOINT" 
DEFAULT_INDEX_ENDPOINT_RESOURCE_NAME = "YOUR_INDEX_ENDPOINT_RESOURCE_NAME" 
DEFAULT_DEPLOYED_INDEX_ID = "YOUR_DEPLOYED_INDEX_ID" 


class VertexVectorSearchClient:
    """
    A client module for interacting with a Google Cloud Vertex AI Vector Search index.

    This class encapsulates the configuration and logic for performing nearest
    neighbor searches against a specific deployed index endpoint.
    """

    def __init__(
        self,
        api_endpoint: str = DEFAULT_API_ENDPOINT,
        index_endpoint_resource_name: str = DEFAULT_INDEX_ENDPOINT_RESOURCE_NAME,
        deployed_index_id: str = DEFAULT_DEPLOYED_INDEX_ID,
        client_options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initializes the VertexVectorSearchClient.

        Args:
            api_endpoint: The specific API endpoint for the deployed index
                          (e.g., "12345.us-central1-12345.vdb.vertexai.goog").
            index_endpoint_resource_name: The full resource name of the Index Endpoint
                                         (e.g., "projects/.../locations/.../indexEndpoints/...").
            deployed_index_id: The ID of the specific index deployed on the endpoint.
            client_options: Optional dictionary of client options passed directly to
                            aiplatform_v1.MatchServiceClient. Primarily used for custom
                            endpoint configuration if api_endpoint is not sufficient.

        Raises:
            ValueError: If required configuration arguments are missing or invalid.
            ImportError: If google-cloud-aiplatform is not installed.
        """
        if not all([api_endpoint, index_endpoint_resource_name, deployed_index_id]):
            raise ValueError("API endpoint, index endpoint resource name, and deployed index ID are required.")

        self.api_endpoint = api_endpoint
        self.index_endpoint_resource_name = index_endpoint_resource_name
        self.deployed_index_id = deployed_index_id

        effective_client_options = {"api_endpoint": self.api_endpoint}
        if client_options:
            effective_client_options.update(client_options)

        try:
            # Configure and initialize the underlying Vector Search client
            self.client = aiplatform_v1.MatchServiceClient(
                client_options=effective_client_options,
            )
            print(f"VertexVectorSearchClient initialized for endpoint: {self.api_endpoint}")
        except Exception as e:
            print(f"Error initializing MatchServiceClient: {e}", file=sys.stderr)
            raise # Re-raise the exception after logging

    def find_neighbors(
        self,
        query_vector: List[float],
        neighbor_count: int = 10,
        return_full_datapoint: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Finds the nearest neighbors for a given query vector.

        Args:
            query_vector: A list of floats representing the embedding or feature vector
                          to search for.
            neighbor_count: The desired number of nearest neighbors to retrieve.
            return_full_datapoint: If True, retrieve the full datapoint object
                                   (including feature vector) for each neighbor.
                                   Defaults to False for efficiency.

        Returns:
            A list of dictionaries, where each dictionary represents a neighbor
            and contains 'id' (the datapoint ID) and 'distance' (the distance
            score from the query vector). Returns an empty list if no neighbors
            are found or an error occurs.

        Raises:
            TypeError: If query_vector is not a list of floats or neighbor_count is not an int.
            ValueError: If neighbor_count is not positive.
            google_exceptions.GoogleAPICallError: If the API call fails.
        """
        if not isinstance(query_vector, list) or not all(isinstance(n, (int, float)) for n in query_vector):
            raise TypeError("query_vector must be a list of numbers (floats or ints).")
        if not isinstance(neighbor_count, int):
             raise TypeError("neighbor_count must be an integer.")
        if neighbor_count <= 0:
            raise ValueError("neighbor_count must be a positive integer.")

        try:
            # 1. Construct the datapoint for the query vector
            datapoint = aiplatform_v1.IndexDatapoint(feature_vector=query_vector)

            # 2. Construct the query object
            query = aiplatform_v1.FindNeighborsRequest.Query(
                datapoint=datapoint,
                neighbor_count=neighbor_count,
            )

            # 3. Construct the main request
            request = aiplatform_v1.FindNeighborsRequest(
                index_endpoint=self.index_endpoint_resource_name,
                deployed_index_id=self.deployed_index_id,
                queries=[query],
                return_full_datapoint=return_full_datapoint,
            )

            # 4. Execute the request
            response = self.client.find_neighbors(request)

            # 5. Process the response
            processed_neighbors = []
            # The response contains a list of nearest_neighbor_result, one for each query.
            # Since we sent one query, we access the first element.
            if response.nearest_neighbors and response.nearest_neighbors[0].neighbors:
                for neighbor in response.nearest_neighbors[0].neighbors:
                    neighbor_data = {"id": neighbor.datapoint.datapoint_id, "distance": neighbor.distance}
                    if return_full_datapoint:
                         neighbor_data["feature_vector"] = list(neighbor.datapoint.feature_vector) # Convert tuple to list
                    processed_neighbors.append(neighbor_data)

            return processed_neighbors

        except google_exceptions.GoogleAPICallError as e:
            print(f"API Error during find_neighbors: {e}", file=sys.stderr)
            raise # Re-raise the API error for upstream handling
        except Exception as e:
            print(f"An unexpected error occurred in find_neighbors: {e}", file=sys.stderr)
            # Depending on desired robustness, you might raise, return [], or log differently
            raise # Re-raise unexpected errors by default


# --- Example Usage (Guard with if __name__ == "__main__":) ---
if __name__ == "__main__":
    # Best Practice: Load sensitive details from environment variables or a config system
    # Ensure these environment variables are set before running the script
    API_ENDPOINT = os.environ.get("VDB_API_ENDPOINT", DEFAULT_API_ENDPOINT)
    INDEX_ENDPOINT = os.environ.get("VDB_INDEX_ENDPOINT_RESOURCE_NAME", DEFAULT_INDEX_ENDPOINT_RESOURCE_NAME)
    DEPLOYED_INDEX_ID = os.environ.get("VDB_DEPLOYED_INDEX_ID", DEFAULT_DEPLOYED_INDEX_ID)

    # --- Dummy Example ---
    # Replace this with a real feature vector (e.g., from a text embedding model)
    # The dimension must match the dimension of the vectors in your index!
    # Example: A 4-dimensional vector
    example_query_vector = [0.1, 0.8, 0.3, 0.5]
    num_neighbors_to_find = 5

    print("\n--- Running Vertex AI Vector Search Example ---")
    print(f"Target Index Endpoint: {INDEX_ENDPOINT}")
    print(f"Deployed Index ID: {DEPLOYED_INDEX_ID}")

    try:
        # Instantiate the client
        search_client = VertexVectorSearchClient(
            api_endpoint=API_ENDPOINT,
            index_endpoint_resource_name=INDEX_ENDPOINT,
            deployed_index_id=DEPLOYED_INDEX_ID,
        )

        # Perform the search
        print(f"\nSearching for {num_neighbors_to_find} neighbors for vector: {example_query_vector[:10]}...") # Print first few dimensions
        neighbors = search_client.find_neighbors(
            query_vector=example_query_vector,
            neighbor_count=num_neighbors_to_find
        )

        # Display results
        if neighbors:
            print(f"\nFound {len(neighbors)} neighbors:")
            for i, neighbor in enumerate(neighbors):
                print(f"  {i+1}. ID: {neighbor['id']}, Distance: {neighbor['distance']:.4f}")
        else:
            print("\nNo neighbors found.")

    except ValueError as ve:
        print(f"\nConfiguration Error: {ve}", file=sys.stderr)
    except ImportError as ie:
         # Message already printed if import failed initially
         pass
    except google_exceptions.GoogleAPICallError as api_error:
        print(f"\nAPI Call Failed: {api_error}", file=sys.stderr)
    except Exception as e:
        print(f"\nAn unexpected error occurred during the example run: {e}", file=sys.stderr)