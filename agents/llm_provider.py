"""
LLM Provider using LiteLLM for unified model access
"""
import os
import logging
from typing import Optional, Dict, Any, List
from litellm import completion, acompletion
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

try:
    from .wsl_utils import get_ollama_endpoint, test_ollama_connection
except ImportError:
    # Handle case when running as main script
    from wsl_utils import get_ollama_endpoint, test_ollama_connection

logger = logging.getLogger(__name__)


class LiteLLMProvider:
    """Unified LLM provider using LiteLLM for consistent API across all models"""
    
    def __init__(
        self,
        provider: str = "claude",
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
        **kwargs
    ):
        self.provider = provider.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs
        
        # Set up model name and any provider-specific configurations
        self.model_name = self._get_model_name(model_name)
        self._setup_provider()
        
        logger.info(f"Initialized LiteLLM provider: {self.provider} with model: {self.model_name}")
    
    def _get_model_name(self, model_name: Optional[str]) -> str:
        """Get the appropriate model name for the provider"""
        if model_name:
            # If provider is ollama and model doesn't have prefix, add it
            if self.provider == "ollama" and not model_name.startswith("ollama/"):
                return f"ollama/{model_name}"
            # For other providers that need prefixes
            elif self.provider == "gemini" and not model_name.startswith("gemini/"):
                return f"gemini/{model_name}"
            elif self.provider == "openrouter" and not model_name.startswith("openrouter/"):
                return f"openrouter/{model_name}"
            else:
                return model_name
            
        # Default models for each provider
        defaults = {
            "claude": "claude-3-7-sonnet-20250219",
            "openai": "gpt-4o",
            "gemini": "gemini/gemini-2.5-flash-lite-preview-06-17",
            "openrouter": "openrouter/meta-llama/llama-4-maverick",
            "ollama": "ollama/PetrosStav/gemma3-tools:4b",
        }
        
        return defaults.get(self.provider, "claude-3-7-sonnet-20250219")
    
    def _setup_provider(self):
        """Set up provider-specific configurations and validate API keys"""
        if self.provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            os.environ["ANTHROPIC_API_KEY"] = api_key
            
        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY") 
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            os.environ["OPENAI_API_KEY"] = api_key
            
        elif self.provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            os.environ["GOOGLE_API_KEY"] = api_key
            
        elif self.provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable not set")
            os.environ["OPENROUTER_API_KEY"] = api_key
            
        elif self.provider == "ollama":
            # Configure Ollama endpoint for WSL -> Windows host
            ollama_endpoint = get_ollama_endpoint()
            os.environ["OLLAMA_API_BASE"] = ollama_endpoint
            
            # Test connection to ensure Ollama is accessible
            if test_ollama_connection(ollama_endpoint):
                logger.info(f"Successfully connected to Ollama at {ollama_endpoint}")
            else:
                logger.warning(f"Could not connect to Ollama at {ollama_endpoint}. Please ensure Ollama is running on Windows host.")
            
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def complete(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        Complete a chat conversation using LiteLLM
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                     Content can be a string or a list for multimodal messages.
            **kwargs: Additional parameters for the completion
            
        Returns:
            The AI response as a string
        """
        try:
            # Process messages to handle vision content
            processed_messages = []
            for message in messages:
                processed_message = {"role": message["role"]}
                
                # Handle multimodal content (text + images)
                if isinstance(message["content"], dict) and "image" in message["content"]:
                    # This is a vision message with text and image
                    processed_message["content"] = [
                        {"type": "text", "text": message["content"]["text"]},
                        {
                            "type": "image_url", 
                            "image_url": {"url": f"data:image/png;base64,{message['content']['image']}"}
                        }
                    ]
                else:
                    # Regular text-only message
                    processed_message["content"] = message["content"]
                
                processed_messages.append(processed_message)
            
            # Merge instance parameters with call-specific parameters
            params = {
                "model": self.model_name,
                "messages": processed_messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                **self.kwargs,
                **kwargs
            }
            
            logger.debug(f"Making LiteLLM completion call with model: {self.model_name}")
            response = completion(**params)
            
            content = response.choices[0].message.content
            logger.debug(f"Received response with {len(content)} characters")
            return content
            
        except Exception as e:
            logger.error(f"Error in LiteLLM completion: {e}")
            raise
    
    def generate(self, prompt: str, image_b64: str = None, **kwargs) -> str:
        """
        Generate a response from a simple text prompt, optionally with an image
        
        Args:
            prompt: The input prompt as a string
            image_b64: Optional base64-encoded image for vision models
            **kwargs: Additional parameters for the completion
            
        Returns:
            The AI response as a string
        """
        if image_b64:
            # Create multimodal message with text and image
            content = {"text": prompt, "image": image_b64}
        else:
            # Regular text-only message
            content = prompt
            
        messages = [{"role": "user", "content": content}]
        return self.complete(messages, **kwargs)
    
    async def acomplete(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        Async version of complete()
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional parameters for the completion
            
        Returns:
            The AI response as a string
        """
        try:
            # Process messages to handle vision content (same as sync version)
            processed_messages = []
            for message in messages:
                processed_message = {"role": message["role"]}
                
                # Handle multimodal content (text + images)
                if isinstance(message["content"], dict) and "image" in message["content"]:
                    # This is a vision message with text and image
                    processed_message["content"] = [
                        {"type": "text", "text": message["content"]["text"]},
                        {
                            "type": "image_url", 
                            "image_url": {"url": f"data:image/png;base64,{message['content']['image']}"}
                        }
                    ]
                else:
                    # Regular text-only message
                    processed_message["content"] = message["content"]
                
                processed_messages.append(processed_message)
            
            # Merge instance parameters with call-specific parameters
            params = {
                "model": self.model_name,
                "messages": processed_messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                **self.kwargs,
                **kwargs
            }
            
            logger.debug(f"Making async LiteLLM completion call with model: {self.model_name}")
            response = await acompletion(**params)
            
            content = response.choices[0].message.content
            logger.debug(f"Received async response with {len(content)} characters")
            return content
            
        except Exception as e:
            logger.error(f"Error in async LiteLLM completion: {e}")
            raise


class LangChainLiteLLM(BaseChatModel):
    """LangChain-compatible wrapper for LiteLLM provider"""
    
    provider: str = Field(default="claude")
    model_name: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=1500)
    litellm_provider: Optional[Any] = Field(default=None, exclude=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize the LiteLLM provider after parent initialization
        object.__setattr__(self, 'litellm_provider', LiteLLMProvider(
            provider=self.provider,
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        ))
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate chat response using LiteLLM"""
        try:
            # Convert LangChain messages to LiteLLM format
            litellm_messages = []
            for message in messages:
                if isinstance(message, SystemMessage):
                    litellm_messages.append({"role": "system", "content": message.content})
                elif isinstance(message, HumanMessage):
                    litellm_messages.append({"role": "user", "content": message.content})
                elif isinstance(message, AIMessage):
                    litellm_messages.append({"role": "assistant", "content": message.content})
                else:
                    # Fallback for other message types
                    litellm_messages.append({"role": "user", "content": str(message.content)})
            
            # Add stop sequences if provided
            completion_kwargs = {}
            if stop:
                completion_kwargs["stop"] = stop
            
            # Call LiteLLM
            response = self.litellm_provider.complete(litellm_messages, **completion_kwargs, **kwargs)
            
            # Create LangChain response
            message = AIMessage(content=response)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])
            
        except Exception as e:
            logger.error(f"Error in LangChain LiteLLM generation: {e}")
            raise
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate chat response using LiteLLM"""
        try:
            # Convert LangChain messages to LiteLLM format
            litellm_messages = []
            for message in messages:
                if isinstance(message, SystemMessage):
                    litellm_messages.append({"role": "system", "content": message.content})
                elif isinstance(message, HumanMessage):
                    litellm_messages.append({"role": "user", "content": message.content})
                elif isinstance(message, AIMessage):
                    litellm_messages.append({"role": "assistant", "content": message.content})
                else:
                    # Fallback for other message types
                    litellm_messages.append({"role": "user", "content": str(message.content)})
            
            # Add stop sequences if provided
            completion_kwargs = {}
            if stop:
                completion_kwargs["stop"] = stop
            
            # Call async LiteLLM
            response = await self.litellm_provider.acomplete(litellm_messages, **completion_kwargs, **kwargs)
            
            # Create LangChain response
            message = AIMessage(content=response)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])
            
        except Exception as e:
            logger.error(f"Error in async LangChain LiteLLM generation: {e}")
            raise
    
    @property
    def _llm_type(self) -> str:
        return "litellm"


def create_llm_provider(
    provider: str = "claude",
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1500,
    use_langchain: bool = True,
    **kwargs
):
    """
    Factory function to create appropriate LLM provider
    
    Args:
        provider: The LLM provider name
        model_name: Specific model name (optional)
        temperature: Generation temperature
        max_tokens: Maximum tokens to generate
        use_langchain: Whether to return LangChain-compatible interface
        **kwargs: Additional provider-specific parameters
        
    Returns:
        LLM provider instance
    """
    if use_langchain:
        return LangChainLiteLLM(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
    else:
        return LiteLLMProvider(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )