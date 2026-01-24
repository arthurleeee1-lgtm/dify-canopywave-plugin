import logging
from collections.abc import Generator
from typing import Optional, Union

from dify_plugin import LargeLanguageModel
from dify_plugin.entities import I18nObject
from dify_plugin.errors.model import (
    CredentialsValidateFailedError,
    InvokeError,
)
from dify_plugin.entities.model import (
    AIModelEntity,
    FetchFrom,
    ModelType,
)
from dify_plugin.entities.model.llm import (
    LLMResult,
    LLMResultChunk,
    LLMResultChunkDelta,
    LLMUsage,
)
from dify_plugin.entities.model.message import (
    PromptMessage,
    PromptMessageTool,
    AssistantPromptMessage,
    PromptMessageRole,
)

logger = logging.getLogger(__name__)


class CanopywaveLargeLanguageModel(LargeLanguageModel):
    """
    Model class for canopywave large language model.
    """

    def _invoke(
        self,
        model: str,
        credentials: dict,
        prompt_messages: list[PromptMessage],
        model_parameters: dict,
        tools: Optional[list[PromptMessageTool]] = None,
        stop: Optional[list[str]] = None,
        stream: bool = True,
        user: Optional[str] = None,
    ) -> Union[LLMResult, Generator]:
        """
        Invoke large language model
        """
        import requests
        import json

        api_key = credentials.get("canopywave_api_key")
        
        # Default to inference endpoint
        url = "https://inference.canopywave.io/v1/chat/completions"
        
        # Models that use the 'api' endpoint
        api_endpoint_models = [
            "xiaomimimo/mimo-v2-flash",
            "openai/gpt-oss-120b",
            "Qwen/Qwen3-Coder-30B-A3B-Instruct",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            "deepseek-ai/DeepSeek-Math-V2"
        ]
        
        if model in api_endpoint_models:
            url = "https://api.canopywave.io/v1/chat/completions"
        
        # Prepare messages
        messages = []
        for msg in prompt_messages:
            role = "user"
            if msg.role == PromptMessageRole.ASSISTANT:
                role = "assistant" 
            elif msg.role == PromptMessageRole.SYSTEM:
                role = "system"
            
            messages.append({
                "role": role,
                "content": msg.content
            })
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model, 
            "messages": messages,
            "stream": stream,
            **model_parameters
        }
        
        if stop:
            payload["stop"] = stop

        try:
            response = requests.post(url, headers=headers, json=payload, stream=stream, timeout=120)
            response.raise_for_status()
        except Exception as e:
            raise self._handle_invoke_error(e)

        if stream:
            return self._handle_stream(response, model)
        else:
            return self._handle_response(response, model)

    def _handle_stream(self, response, model):
        import json
        from dify_plugin.entities.model.message import AssistantPromptMessage
        
        # Handle SSE stream
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    line = line[6:]
                
                if line == "[DONE]":
                    break
                
                if not line:
                     continue
                     
                try:
                    data = json.loads(line)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    
                    if content:
                        yield LLMResultChunk(
                            model=model,
                            delta=LLMResultChunkDelta(
                                index=0,
                                message=AssistantPromptMessage(content=content),
                                usage=None
                            )
                        )
                except Exception:
                    continue

    def _handle_response(self, response, model):
        from dify_plugin.entities.model.message import AssistantPromptMessage
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        # Usage parsing if available
        usage_data = data.get("usage", {})
        
        from dify_plugin.entities.model.llm import LLMUsage
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
            prompt_unit_price="0.0",
            prompt_price_unit="0.000001",
            prompt_price="0.0",
            completion_unit_price="0.0",
            completion_price_unit="0.000001",
            completion_price="0.0",
            total_price="0.0",
            currency="USD",
            latency=0.0
        )

        return LLMResult(
            model=model,
            prompt_messages=[],
            message=AssistantPromptMessage(content=content),
            usage=usage
        )
   
    def get_num_tokens(
        self,
        model: str,
        credentials: dict,
        prompt_messages: list[PromptMessage],
        tools: Optional[list[PromptMessageTool]] = None,
    ) -> int:
        """
        Get number of tokens for given prompt messages
        """
        return 0

    def validate_credentials(self, model: str, credentials: dict) -> None:
        """
        Validate model credentials
        """
        # We can use a simple invocation to validate credentials
        from dify_plugin.entities.model.message import UserPromptMessage
        
        try:
             # Just try to generate 1 token to verify auth
             self._invoke(
                 model=model,
                 credentials=credentials,
                 prompt_messages=[UserPromptMessage(content="Hi")],
                 model_parameters={"max_tokens": 1, "temperature": 0.1},
                 stream=False
             )
        except Exception as e:
             # If invoke fails, catch and re-raise as validate failed if it's auth related
             # Actually _invoke already raises specific InvokeErrors.
             # We should probably map them or let them propagate? 
             # The provider expects CredentialsValidateFailedError.
             # But _invoke raises InvokeAuthorizationError which inherits or is mapped?
             # Let's check imports.
             
             # Actually, simpler: map InvokeAuthorizationError to CredentialsValidateFailedError
             from dify_plugin.errors.model import InvokeAuthorizationError
             if isinstance(e, InvokeAuthorizationError):
                 raise CredentialsValidateFailedError(str(e))
             
             # For other errors, if we simply want to pass "if auth holds", we might be lenient
             # But usually if invoke fails, validation fails.
             # Re-raise standard exception
             raise CredentialsValidateFailedError(f"Validation failed: {str(e)}")

    def get_customizable_model_schema(
        self, model: str, credentials: dict
    ) -> AIModelEntity:
        """
        Return customizable model schema
        """
        entity = AIModelEntity(
            model=model,
            label=I18nObject(zh_Hans=model, en_US=model),
            model_type=ModelType.LLM,
            features=[],
            fetch_from=FetchFrom.CUSTOMIZABLE_MODEL,
            model_properties={},
            parameter_rules=[],
        )

        return entity

    @property
    def _invoke_error_mapping(self) -> dict[type[InvokeError], list[type[Exception]]]:
        """
        Map model invoke error to unified error
        """
        return {}

    def _handle_invoke_error(self, error: Exception) -> InvokeError:
        """
        Map to InvokeError
        """
        import requests
        from dify_plugin.errors.model import (
            InvokeAuthorizationError,
            InvokeBadRequestError,
            InvokeRateLimitError,
            InvokeServerUnavailableError,
            InvokeConnectionError,
        )

        if isinstance(error, requests.exceptions.HTTPError):
            status_code = error.response.status_code
            if status_code == 401:
                return InvokeAuthorizationError("Invalid API Key")
            elif status_code == 400:
                return InvokeBadRequestError(f"Bad Request: {error.response.text}")
            elif status_code == 429:
                return InvokeRateLimitError("Rate Limit Exceeded")
            elif status_code >= 500:
                return InvokeServerUnavailableError(f"Server Error: {status_code}")
        
        elif isinstance(error, requests.exceptions.ConnectionError):
            return InvokeConnectionError("Connection Failed")
            
        return InvokeError(str(error))
