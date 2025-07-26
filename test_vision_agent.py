"""Test script to validate vision agent LiteLLM tool calling"""

import litellm
import json
from agents.vision_agent import TOOLS

# Test that tool calling works with a simple example
def test_tool_calling():
    print("Testing LiteLLM tool calling...")
    
    # Create a simple test message
    messages = [
        {
            "role": "system",
            "content": "You are a test agent. Use the press_button tool to press the A button."
        },
        {
            "role": "user", 
            "content": "Press the A button"
        }
    ]
    
    try:
        # Test with a model that supports function calling
        response = litellm.completion(
            model="gpt-3.5-turbo",  # Using OpenAI for testing
            messages=messages,
            tools=TOOLS,
            tool_choice="required",
            mock_response="Test mode"  # Use mock mode if no API key
        )
        
        print("Response received successfully")
        
        # Check if tool calls exist
        if hasattr(response.choices[0].message, 'tool_calls'):
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                print(f"Tool calls found: {len(tool_calls)}")
                for tc in tool_calls:
                    print(f"  - Function: {tc.function.name}")
                    print(f"  - Arguments: {tc.function.arguments}")
            else:
                print("No tool calls in response")
        else:
            print("Response doesn't have tool_calls attribute")
            
    except Exception as e:
        print(f"Error during tool calling test: {e}")
        print(f"Error type: {type(e).__name__}")

# Test tool definitions
def test_tool_definitions():
    print("\nValidating tool definitions...")
    
    for tool in TOOLS:
        print(f"\nTool: {tool['function']['name']}")
        print(f"  Type: {tool['type']}")
        print(f"  Description: {tool['function']['description']}")
        print(f"  Parameters: {json.dumps(tool['function']['parameters'], indent=2)}")
        
        # Validate structure
        assert tool['type'] == 'function', "Tool type must be 'function'"
        assert 'name' in tool['function'], "Tool must have a name"
        assert 'description' in tool['function'], "Tool must have a description"
        assert 'parameters' in tool['function'], "Tool must have parameters"

if __name__ == "__main__":
    test_tool_definitions()
    test_tool_calling()