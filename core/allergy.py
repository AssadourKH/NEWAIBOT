# core/allergy.py

import os
from dotenv import load_dotenv
from core.openai_client import client  # Shared OpenAI client

load_dotenv()

deployment = os.getenv("DEPLOYMENT_NAME")
search_endpoint = os.getenv("SEARCH_ENDPOINT")
search_key = os.getenv("SEARCH_KEY")
embedding_endpoint = os.getenv("EMBEDDING_ENDPOINT")
embedding_key = os.getenv("EMBEDDING_KEY")
index_name = os.getenv("SEARCH_INDEX_NAME", "musing-zoo-vmjc7lqxf6")


def get_allergen_response(conversation_history: list) -> str:
    """Respond to allergen-related questions using Azure Cognitive Search."""
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=conversation_history,
            max_tokens=800,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            extra_body={
                "data_sources": [{
                    "type": "azure_search",
                    "parameters": {
                        "endpoint": search_endpoint,
                        "index_name": index_name,
                        "semantic_configuration": "azureml-default",
                        "query_type": "vector_simple_hybrid",
                        "in_scope": True,
                        "filter": None,
                        "role_information": (
                            "You are an AI assistant that helps users find allergen and ingredient information "
                            "for restaurant food items.\n"
                            "- Explicitly state allergen content if found.\n"
                            "- Always list ingredients (excluding allergens).\n"
                            "- Respond 'I don't know' if info is missing.\n"
                            "- Do NOT include document references.\n"
                            "Format:\n"
                            "- Allergen Notice: ...\n"
                            "- Ingredients: ..."
                        ),
                        "authentication": {
                            "type": "api_key",
                            "key": search_key,
                        },
                        "embedding_dependency": {
                            "type": "endpoint",
                            "endpoint": embedding_endpoint,
                            "authentication": {
                                "type": "api_key",
                                "key": embedding_key,
                            },
                        },
                        "strictness": 3,
                        "top_n_documents": 5,
                    }
                }]
            }
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"[ERROR] Allergen response failed: {e}")
        return "I'm sorry, I couldn't find allergen information at the moment."
