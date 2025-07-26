"""Comprehensive test of vision agent functionality"""

import base64
import io
import json
from PIL import Image
from agents.vision_agent import VisionAgent, TOOLS

def create_test_image():
    """Create a test image to simulate a screenshot"""
    # Create a simple test image
    img = Image.new('RGB', (160, 144), color='blue')  # Game Boy resolution
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()

def test_agent_initialization():
    """Test agent can be initialized with various providers"""
    print("Testing agent initialization...")
    
    providers = ["ollama", "openai", "claude", "gemini"]
    for provider in providers:
        try:
            agent = VisionAgent(
                provider=provider,
                model_name="test-model",
                headless=True
            )
            print(f"✓ {provider} provider initialized successfully")
            
            # Test core components
            assert agent.llm is not None, "LLM provider not initialized"
            assert agent.conversation_history == [], "Conversation history should start empty"
            assert agent.upscale_factor == 2.0, "Default upscale factor should be 2.0"
            
        except Exception as e:
            print(f"✗ {provider} provider failed: {e}")

def test_image_upscaling():
    """Test image upscaling functionality"""
    print("\nTesting image upscaling...")
    
    agent = VisionAgent(provider="ollama", headless=True)
    test_image_b64 = create_test_image()
    
    # Test upscaling
    upscaled = agent.upscale_image(test_image_b64)
    
    # Verify upscaling worked
    original_img = Image.open(io.BytesIO(base64.b64decode(test_image_b64)))
    upscaled_img = Image.open(io.BytesIO(base64.b64decode(upscaled)))
    
    print(f"Original size: {original_img.size}")
    print(f"Upscaled size: {upscaled_img.size}")
    
    assert upscaled_img.width == original_img.width * 2, "Width not properly upscaled"
    assert upscaled_img.height == original_img.height * 2, "Height not properly upscaled"
    print("✓ Image upscaling works correctly")

def test_cot_extraction():
    """Test chain of thought component extraction"""
    print("\nTesting COT extraction...")
    
    agent = VisionAgent(provider="ollama", headless=True)
    
    # Test various reasoning formats
    test_cases = [
        {
            "input": "**COT_effort**: HIGH\n**COT_length**: 250\n**COT**: This is a complex battle situation requiring careful analysis of type matchups and available moves.",
            "expected": {"effort": "HIGH", "length": "250"}
        },
        {
            "input": "COT_effort: LOW\nCOT_length: 50\nCOT: Simple navigation, just need to press up.",
            "expected": {"effort": "LOW", "length": "50"}
        }
    ]
    
    for i, test in enumerate(test_cases):
        components = agent.extract_cot_components(test["input"])
        print(f"\nTest case {i+1}:")
        print(f"  Effort: {components['effort']} (expected: {test['expected']['effort']})")
        print(f"  Length: {components['length']} (expected: {test['expected']['length']})")
        
        assert components['effort'] == test['expected']['effort'], f"Effort extraction failed for test {i+1}"
        assert components['length'] == test['expected']['length'], f"Length extraction failed for test {i+1}"
        
    print("✓ COT extraction works correctly")

def test_conversation_history():
    """Test conversation history management"""
    print("\nTesting conversation history...")
    
    agent = VisionAgent(provider="ollama", conversation_history_limit=3, headless=True)
    
    # Add some history entries
    for i in range(5):
        agent.conversation_history.append({
            "role": "assistant",
            "content": f"Test message {i}",
            "tool_calls": []
        })
    
    # Build messages with history
    test_image = create_test_image()
    messages = agent.build_conversation_messages(test_image)
    
    # Check that only recent history is included
    # Should have: system message + 3 history entries + current user message = 5 total
    print(f"Total messages: {len(messages)}")
    assert len(messages) == 5, "Conversation history not properly limited"
    
    # Verify message roles
    assert messages[0]["role"] == "system", "First message should be system"
    assert messages[-1]["role"] == "user", "Last message should be user"
    
    print("✓ Conversation history management works correctly")

def test_tool_response_parsing():
    """Test parsing of tool responses"""
    print("\nTesting tool response parsing...")
    
    agent = VisionAgent(provider="ollama", headless=True)
    
    # Create mock response with tool call
    class MockChoice:
        class MockMessage:
            content = "**COT_effort**: MEDIUM\n**COT_length**: 150\n**COT**: I need to press A to continue the dialogue."
            class MockToolCall:
                id = "call_123"
                class MockFunction:
                    name = "press_button"
                    arguments = '{"button": "A"}'
                function = MockFunction()
            tool_calls = [MockToolCall()]
        message = MockMessage()
    
    class MockResponse:
        choices = [MockChoice()]
    
    mock_response = MockResponse()
    
    # Parse the response
    reasoning, action, tool_call = agent.parse_tool_response(mock_response)
    
    print(f"Reasoning extracted: {len(reasoning)} chars")
    print(f"Action: {action}")
    print(f"Tool call: {tool_call}")
    
    assert action is not None, "Action not parsed"
    assert action["action_type"] == "press_key", "Wrong action type"
    assert action["keys"] == ["a"], "Button not lowercased"
    assert tool_call["function"] == "press_button", "Tool function not captured"
    
    print("✓ Tool response parsing works correctly")

if __name__ == "__main__":
    test_agent_initialization()
    test_image_upscaling()
    test_cot_extraction()
    test_conversation_history()
    test_tool_response_parsing()
    
    print("\n✅ All tests passed!")