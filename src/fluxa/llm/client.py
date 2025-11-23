"""Client per l'interazione con LMStudio (o API compatibili OpenAI).

Gestisce la comunicazione HTTP asincrona, lo streaming delle risposte
e il logging automatico delle interazioni.
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from fluxa.core.config import get_settings
from fluxa.utils.logger import get_logger, log_llm_interaction

logger = get_logger(__name__)

class LLMClient:
    """Client asincrono per comunicare con LMStudio."""

    def __init__(self) -> None:
        """Inizializza il client con le impostazioni globali."""
        settings = get_settings()
        self.config = settings.lmstudio

        # Converto HttpUrl in una stringa rimuovendo lo slash finale
        self.base_url = str(self.config.base_url).rstrip("/")
        self.timeout = self.config.timeout

        logger.info(f"LLM Client inizializzato | URL: {self.base_url}")

    async def check_connection(self) -> bool:
        """Verifica la connessione al server LMStudio."""

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response =  await client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Impossibile connettersi ad LMStudio: {e}")
            return False

    async def get_models(self) -> List[str]:
        """Recupera la lista dei modelli disponibili"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/models")
                response.raise_for_status()
                data = response.json()
                return [model["id"] for model in data.get("data", [])]
        except Exception as e:
            logger.warning(f"Errore durante il recupero dei modelli: {e}")
            return []

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any] | AsyncGenerator[str, None]:
        """Invia una richiesta di chat completion.

        Gestisce sia risposte complete che streaming.
        """
        # Determino i parametri finali (override o default)
        model = model or self.config.model_name
        if not model:
            # Fallback: LMStudio usa "local-model" come default
            model = "local-model"

        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        stream = stream if stream is not None else self.config.stream

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        # Log richiesta
        log_llm_interaction(
            direction="request",
            content=messages[-1]["content"] if messages else "No content",
            metadata={
                "model": model,
                "temp": temperature,
                "stream": stream,
                "tools_count": len(tools) if tools else 0
            }
        )

        try:
            client = httpx.AsyncClient(timeout=self.timeout)

            if stream:
                return self._stream_response(client, payload)
            else:
                return await self._unary_response(client, payload)

        except Exception as e:
            logger.error(f"Errore richiesta LLM: {e}")
            raise

    async def _unary_response(
            self, client: httpx.AsyncClient, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gestisce una risposta non-streaming (unary)."""
        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            # Estrai contenuto per logging
            content = ""
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0].get("message", {})
                content = message.get("content" or "")
                if message.get("tool_calls"):
                    content += f" [Tool Calls: {len(message['tool_calls'])}]"

            log_llm_interaction(
                direction="response",
                content=content,
                metadata={"usage": data.get("usage", {})}
            )

            return data
        finally:
            await client.aclose()

    async def _stream_response(
            self, client: httpx.AsyncClient, payload: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Gestisce una risposta in streaming."""
        full_content = []

        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            if not  data.get("choices"):
                                continue

                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                full_content.append(content)
                                yield content
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"Errore streaming: {e}")
            raise
        finally:
            # Log finale
            log_llm_interaction(
                direction="response",
                content="".join(full_content),
                metadata={"stream": True, "length": len(full_content)}
            )
            await client.aclose()