import requests
import json

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2"

def chat_with_ollama(prompt):
    """
    Sends a prompt to the local Ollama instance and prints the response.
    """
    print(f"🤖 User: {prompt}")
    print("Thinking...", end="", flush=True)

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False  # Set to True for streaming responses
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status() # Raise exception for bad status codes
        
        result = response.json()
        bot_response = result['message']['content']
        
        print("\r" + " " * 20 + "\r", end="") # Clear "Thinking..."
        print(f"🦙 Llama: {bot_response}\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to Ollama. Is the app running?")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    # Test the model
    chat_with_ollama("Why is Python good for AI?")
