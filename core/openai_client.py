# # core/openai_client.py
# import os
# from openai import OpenAI
# from dotenv import load_dotenv

# load_dotenv()

# # Debugging output
# print("[DEBUG] Configuring OpenAI client")
# print(f"[DEBUG] Endpoint URL: {os.environ.get('ENDPOINT_URL')}")
# print(f"[DEBUG] Deployment Name: {os.environ.get('DEPLOYMENT_NAME')}")
# print(f"[DEBUG] API Key Exists: {bool(os.environ.get('AZURE_OPENAI_API_KEY'))}")

# client = OpenAI(
#     api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#     base_url=os.getenv("ENDPOINT_URL"),  # ❗ Do not add /openai/deployments here
#     default_headers={
#         "api-key": os.getenv("AZURE_OPENAI_API_KEY")
#     }
# )

# deployment = os.getenv("DEPLOYMENT_NAME")

# def get_chat_completion(messages, temperature=0.7, max_tokens=800):
#     try:
#         response = client.chat.completions.create(
#             model=deployment,  # This must be your Azure deployment name
#             messages=messages,
#             max_tokens=max_tokens,
#             temperature=temperature,
#             top_p=0.95,
#             frequency_penalty=0,
#             presence_penalty=0
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         print(f"[ERROR] OpenAI chat completion failed:\n{e}")
#         return "Sorry, I couldn't process your request at the moment."

# core/openai_client.py

import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

print("[DEBUG] Configuring Azure OpenAI client")
print(f"[DEBUG] Endpoint URL: {os.getenv('ENDPOINT_URL')}")
print(f"[DEBUG] Deployment Name: {os.getenv('DEPLOYMENT_NAME')}")
print(f"[DEBUG] API Key Exists: {bool(os.getenv('AZURE_OPENAI_API_KEY'))}")

# Correct usage for Azure OpenAI client (v1+ SDK)
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("ENDPOINT_URL"),
    api_version="2024-02-15-preview",  # Match your deployment version
)

deployment = os.getenv("DEPLOYMENT_NAME")

def get_chat_completion(messages, temperature=0.7):
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            temperature=temperature,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ERROR] OpenAI chat completion failed:\n{e}")
        return "Sorry, I couldn't process your request at the moment."
