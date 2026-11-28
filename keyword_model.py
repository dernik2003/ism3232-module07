# keyword_model.py
# Author: Nikita Lemeshenko


class KeywordModel:
    """An offline model that selects tools using keyword rules."""

    def decide(self, instructions, history, tools):
        """Return a reply or a tool request based on the latest message."""
        last = history[-1]

        if last["role"] == "tool":
            return {"text": last["content"]}

        text = last["content"].lower()

        if "repair" in text:
            return {
                "tool": "look_up_repair",
                "arguments": {"ticket_id": last["content"]},
            }

        if "stock" in text or "part" in text or "have" in text:
            return {
                "tool": "check_part",
                "arguments": {"name": last["content"]},
            }

        if "hello" in text:
            return {"text": "Hello! I can check repair status and part availability."}

        return {
            "text": (
                "I can check repairs or parts. "
                "Try 'Is repair R200 ready?' or 'Do you have inner tube?'"
            )
        }
