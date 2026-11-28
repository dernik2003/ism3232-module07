import database
from agent import SupportChatbot
from fake_model import FakeModel
from fallback_model import FallbackModel
from keyword_model import KeywordModel
from settings import INSTRUCTIONS
from tools import SpokewellTools


class SilentModel:
    """Stand in for an unavailable model without contacting Ollama."""

    def decide(self, instructions, history, tools):
        return None


def make_bot(tmp_path, model):
    """Build a chatbot using a fresh temporary database."""
    db_file = tmp_path / "test.db"
    database.create_tables(db_file)

    return SupportChatbot(
        "Jamie",
        INSTRUCTIONS,
        SpokewellTools(db_file),
        model,
    )


def test_model_chosen_lookup_reads_the_database(tmp_path):
    model = FakeModel(
        [
            {
                "tool": "look_up_repair",
                "arguments": {"ticket_id": "R200"},
            },
            {"text": "Your repair is in progress."},
        ]
    )
    bot = make_bot(tmp_path, model)

    reply = bot.respond("Is repair R200 ready?")

    assert reply == "Your repair is in progress."
    assert model.calls == 2

    tool_result = bot.history[1]
    assert tool_result["role"] == "tool"
    assert tool_result["tool_name"] == "look_up_repair"
    assert "R200 is in repair" in tool_result["content"]
    assert "2026-11-20" in tool_result["content"]


def test_unavailable_model_falls_back_to_keyword_lookup(tmp_path):
    model = FallbackModel(SilentModel(), KeywordModel())
    bot = make_bot(tmp_path, model)

    reply = bot.respond("Is repair R201 ready?")

    assert "R201 is ready" in reply
    assert "2026-11-18" in reply


def test_payment_message_skips_model_and_history(tmp_path):
    model = FakeModel([])
    bot = make_bot(tmp_path, model)

    reply = bot.respond("Can I pay with a different card?")

    assert "contact shop staff" in reply
    assert model.calls == 0
    assert bot.history == []
    assert database.waiting_requests(bot.tools.db_file) == []


def test_card_number_is_not_kept_for_a_later_turn(tmp_path):
    model = FakeModel([{"text": "Hello!"}])
    bot = make_bot(tmp_path, model)

    reply = bot.respond("4111 1111 1111 1111")

    assert "contact shop staff" in reply
    assert model.calls == 0
    assert bot.history == []

    assert bot.respond("Hello") == "Hello!"
    assert model.calls == 1
    assert "4111" not in str(bot.history)
