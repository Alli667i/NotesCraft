import requests

# your LiteLLM proxy (replace with your Railway URL)
LITELLM_URL = "https://litellm-production-3113.up.railway.app/v1/chat/completions"

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer BEOG789&*(987"  # dummy key, LiteLLM just expects some token
}

data = {
    "model": "gemini/gemini-2.5-flash",
    "messages": [
        {"role": "system", "content": "You are a helpful AI"},
        {"role": "user", "content": "Tell me a dark joke about politicians"}
    ]
}

response = requests.post(LITELLM_URL, headers=headers, json=data)

print(response.json())
