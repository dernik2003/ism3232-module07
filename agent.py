# agent.py
# Author: Nikita Lemeshenko

import re
import sqlite3

HANDOFF_WORDS = ["payment", "card"]
MAX_TOOL_ROUNDS = 3
PAYMENT_REPLY = "Please contact shop staff for help with payment or card issues."
UNAVAILABLE_REPLY = "Sorry, I can't answer that right now. Please contact shop staff."


class SupportChatbot:
    """A support chatbot. The model decides. The toolbox checks every tool request."""

    def __init__(self, name, instructions, tools, model):
        """Set up one chatbot with its own name, instructions, tools, model, and history."""
        self.name = name
        self.instructions = instructions
        self.tools = tools
        self.model = model
        self.history = []

    def respond(self, user_message):
        """Check for payment details before recording or processing a message."""
        if not isinstance(user_message, str) or not user_message.strip():
            return "Please enter a question about a repair or a part."
        if self.needs_human(user_message):
            return PAYMENT_REPLY

        self.history.append({"role": "user", "content": user_message})
        reply = self.choose_reply(user_message)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def choose_reply(self, user_message):
        """Pass payment questions to a person. Send everything else to the model."""
        if self.needs_human(user_message):
            return PAYMENT_REPLY
        return self.model_reply()

    def needs_human(self, text):
        """Recognize payment words and common card-number formats."""
        text = text.lower()
        for word in HANDOFF_WORDS:
            if word in text:
                return True

        # Contiguous numbers, four groups of four, or the 4-6-5 format.
        # Explicit groups avoid combining two ordinary ISO dates into a number.
        pattern = (
            r"(?<!\d)(?:\d{13,19}|\d{4}(?:[\s./-]+\d{4}){3}"
            r"|\d{4}[\s./-]+\d{6}[\s./-]+\d{5})(?!\d)"
        )
        return re.search(pattern, text) is not None

    def model_reply(self):
        """Ask the model. Run each tool it asks for, then ask again, up to a limit."""
        rounds = 0
        while rounds <= MAX_TOOL_ROUNDS:
            tool_list = self.tools.tool_list()
            try:
                decision = self.model.decide(self.instructions, self.history, tool_list)
            except (ConnectionError, TimeoutError):
                return UNAVAILABLE_REPLY
            if not isinstance(decision, dict):
                return UNAVAILABLE_REPLY
            if "text" in decision:
                reply = decision["text"]
                if not isinstance(reply, str) or not reply.strip():
                    return UNAVAILABLE_REPLY
                if self.needs_human(reply):
                    return PAYMENT_REPLY
                return reply
            name = decision.get("tool")
            arguments = decision.get("arguments")
            if not isinstance(name, str) or not isinstance(arguments, dict):
                return UNAVAILABLE_REPLY
            if any(
                isinstance(value, bool) or not isinstance(value, (str, int))
                for value in arguments.values()
            ):
                return UNAVAILABLE_REPLY
            # One final model response is allowed after the third tool result.
            if rounds == MAX_TOOL_ROUNDS:
                break
            if self.needs_human(name) or any(
                self.needs_human(str(value)) for value in arguments.values()
            ):
                return PAYMENT_REPLY
            try:
                result = self.tools.run(name, arguments, self.history)
            except sqlite3.Error:
                return "The database is unavailable. Please contact shop staff."
            if not isinstance(result, str):
                return UNAVAILABLE_REPLY
            if self.needs_human(result):
                return PAYMENT_REPLY
            self.history.append(
                {
                    "role": "tool",
                    "tool_name": name,
                    "arguments": arguments,
                    "content": result,
                }
            )
            rounds += 1
        return "Sorry, I couldn't finish that. Please contact shop staff."

    def count_user_messages(self):
        """Return how many messages the user has sent so far."""
        count = 0
        for message in self.history:
            if message["role"] == "user":
                count += 1
        return count
