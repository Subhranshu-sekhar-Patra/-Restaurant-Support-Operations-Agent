"""LLM client - thin wrapper supporting Google Gemini and OpenAI."""

import json
import asyncio
from typing import List, Optional
from dataclasses import dataclass, field
from app.config import settings
from app.observability.logging import get_logger

logger = get_logger(__name__)


class LLMError(Exception):
    """Raised when LLM calls fail."""
    pass


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    """Response from the LLM."""
    text: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)


class LLMClient:
    """Thin wrapper around LLM providers. Mockable in tests."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            if settings.LLM_PROVIDER == "google":
                from google import genai
                self._client = genai.Client(api_key=settings.LLM_API_KEY)
            else:
                raise LLMError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
        return self._client

    async def chat(
        self,
        system_prompt: str,
        messages: List[dict],
        tool_schemas: Optional[List[dict]] = None,
        timeout: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send a chat request to the LLM with optional tool schemas.
        """
        if settings.SIMULATE_FAILURE == "llm_down":
            raise LLMError("Simulated LLM unavailability")

        timeout = timeout or settings.LLM_TIMEOUT_S

        try:
            if settings.LLM_PROVIDER == "google":
                return await self._chat_google(system_prompt, messages, tool_schemas, timeout)
            else:
                raise LLMError(f"Unsupported provider: {settings.LLM_PROVIDER}")
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise LLMError(str(e))

    async def _chat_google(
        self,
        system_prompt: str,
        messages: List[dict],
        tool_schemas: Optional[List[dict]],
        timeout: int,
    ) -> LLMResponse:
        """Chat using Google Gemini API."""
        from google.genai import types

        client = self._get_client()

        # Convert tool schemas to Gemini format
        tools = None
        if tool_schemas:
            function_declarations = []
            for schema in tool_schemas:
                func = schema["function"]
                # Convert JSON Schema to Gemini format
                params = func.get("parameters", {})
                properties = params.get("properties", {})
                required = params.get("required", [])

                # Build Gemini-compatible schema
                gemini_props = {}
                for prop_name, prop_def in properties.items():
                    prop_type = prop_def.get("type", "string").upper()
                    gemini_props[prop_name] = types.Schema(
                        type=prop_type,
                        description=prop_def.get("description", ""),
                    )

                function_declarations.append(types.FunctionDeclaration(
                    name=func["name"],
                    description=func["description"],
                    parameters=types.Schema(
                        type="OBJECT",
                        properties=gemini_props,
                        required=required,
                    ),
                ))

            tools = [types.Tool(function_declarations=function_declarations)]

        # Build contents
        contents = []
        for msg in messages:
            role = msg["role"]
            if role == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=msg["content"])],
                ))
            elif role == "assistant":
                if "tool_calls" in msg:
                    # Represent tool calls as function call parts
                    parts = []
                    for tc in msg["tool_calls"]:
                        parts.append(types.Part.from_function_call(
                            name=tc["name"],
                            args=tc["arguments"],
                        ))
                    if msg.get("content"):
                        parts.insert(0, types.Part.from_text(text=msg["content"]))
                    contents.append(types.Content(role="model", parts=parts))
                else:
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=msg.get("content", ""))],
                    ))
            elif role == "tool":
                # Tool result
                tool_name = msg.get("tool_name", "unknown")
                tool_content = msg.get("content", "{}")
                if isinstance(tool_content, str):
                    try:
                        tool_data = json.loads(tool_content)
                    except json.JSONDecodeError:
                        tool_data = {"result": tool_content}
                else:
                    tool_data = tool_content

                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=tool_name,
                        response=tool_data,
                    )],
                ))

        # Make the API call
        def _sync_call():
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tools,
                temperature=0.3,
            )
            response = client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=contents,
                config=config,
            )
            return response

        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _sync_call),
            timeout=timeout,
        )

        # Parse response
        result = LLMResponse()

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fc = part.function_call
                    result.tool_calls.append(ToolCall(
                        id=f"call_{fc.name}_{id(fc)}",
                        name=fc.name,
                        arguments=dict(fc.args) if fc.args else {},
                    ))
                elif part.text:
                    result.text = (result.text or "") + part.text

        return result

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        """Simple text generation (used for complaint analysis)."""
        from google.genai import types

        client = self._get_client()

        def _sync_call():
            config = types.GenerateContentConfig(
                temperature=0.1,
            )
            if json_mode:
                config.response_mime_type = "application/json"

            response = client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt,
                config=config,
            )
            return response.text

        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _sync_call),
            timeout=settings.LLM_TIMEOUT_S,
        )


# Singleton
llm_client = LLMClient()
