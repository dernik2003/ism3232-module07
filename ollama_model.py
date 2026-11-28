# ollama_model.py
# Author: Nikita Lemeshenko

from httpx import HTTPError
from ollama import Client, ResponseError

MAX_MESSAGES = 20


class OllamaModel:
    """A real AI model that runs on this computer through Ollama."""

    def __init__(self, model_name, timeout=60):
        """Remember which model to ask."""
        self.model_name = model_name
        self.client = Client(timeout=timeout)

    def reply(self, instructions, history):
        """Send the instructions and the conversation to the model. Return its reply."""
        decision = self.decide(instructions, history, [])
        if decision is None:
            return None
        return decision.get("text")

    def decide(self, instructions, history, tools):
        """Send the conversation and the tools. Return a reply or a tool request."""
        messages = [{"role": "system", "content": instructions}]
        for message in history[-MAX_MESSAGES:]:
            if message["role"] == "tool":
                messages = messages + self.tool_messages(message)
            else:
                messages.append(message)
        try:
            response = self.client.chat(
                model=self.model_name, messages=messages, tools=tools
            )
        except (ConnectionError, ResponseError, HTTPError):
            return None
        if response.message.tool_calls:
            call = response.message.tool_calls[0]
            return {"tool": call.function.name, "arguments": call.function.arguments}
        content = response.message.content
        if not isinstance(content, str) or not content.strip():
            return None
        return {"text": content}

    def tool_messages(self, message):
        """Turn one tool entry into the two messages Ollama expects."""
        name = message["tool_name"]
        request = {"function": {"name": name, "arguments": message["arguments"]}}
        return [
            {"role": "assistant", "content": "", "tool_calls": [request]},
            {"role": "tool", "tool_name": name, "content": message["content"]},
        ]
