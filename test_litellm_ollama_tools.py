"""Test LiteLLM tool calling with Ollama"""

import litellm
from agents.vision_agent import TOOLS

def test_ollama_tool_calling():
    """Test if Ollama supports tool calling through LiteLLM"""
    print("Testing Ollama tool calling support...")
    
    # Check if model supports function calling
    model = "ollama/PetrosStav/gemma3-tools:4b"
    supports_tools = litellm.supports_function_calling(model)
    print(f"Model {model} supports function calling: {supports_tools}")
    
    if not supports_tools:
        print("\nNote: This Ollama model may not support tool calling.")
        print("Tool calling might need to be simulated through prompting.")
        
    # Try a simple tool call
    messages = [
        {
            "role": "system",
            "content": "You are a Pokemon game player. Use tools to interact with the game."
        },
        {
            "role": "user",
            "content": "Press the A button to continue the dialogue."
        }
    ]
    
    try:
        print("\nAttempting tool call with Ollama...")
        response = litellm.completion(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",  # Let model decide
            temperature=0.1,
            max_tokens=500
        )
        
        print("Response received!")
        
        # Check response structure
        if hasattr(response.choices[0].message, 'tool_calls'):
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                print(f"✓ Tool calls found: {len(tool_calls)}")
                for tc in tool_calls:
                    print(f"  - Function: {tc.function.name}")
                    print(f"  - Arguments: {tc.function.arguments}")
            else:
                print("✗ No tool calls in response")
                print(f"Content: {response.choices[0].message.content[:200]}...")
        else:
            print("✗ Response doesn't have tool_calls attribute")
            print(f"Response type: {type(response)}")
            print(f"Message type: {type(response.choices[0].message)}")
            
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_ollama_tool_calling()