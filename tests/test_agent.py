import sqlite3

import pytest

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


@pytest.mark.parametrize(
    "message",
    [
        "4111111111111111",
        "4111.1111.1111.1111",
        "4111-1111-1111-1111",
        "4111/1111/1111/1111",
        "4111\t1111\t1111\t1111",
        "4111\n1111\n1111\n1111",
        "3782 822463 10005",
        "Can I change my CARD?",
    ],
)
def test_payment_formats_never_reach_history_or_model(tmp_path, message):
    model = FakeModel([])
    bot = make_bot(tmp_path, model)
    assert "contact shop staff" in bot.respond(message)
    assert model.calls == 0
    assert bot.history == []


def test_two_dates_are_not_mistaken_for_a_card_number(tmp_path):
    bot = make_bot(tmp_path, FakeModel([{"text": "Which date would you prefer?"}]))
    assert "Which date" in bot.respond("Pickup dates: 2026-11-20 2026-12-01")
    assert bot.count_user_messages() == 1


@pytest.mark.parametrize(
    "decision",
    [None, [], "invalid", {}, {"text": None}, {"text": ""}, {"tool": "check_part"}],
)
def test_malformed_model_response_does_not_crash(tmp_path, decision):
    bot = make_bot(tmp_path, FakeModel([decision]))
    assert "contact shop staff" in bot.respond("Hello")
    assert database.waiting_requests(bot.tools.db_file) == []


def test_model_can_answer_after_three_tools(tmp_path):
    lookup = {"tool": "look_up_repair", "arguments": {"ticket_id": "R200"}}
    model = FakeModel([lookup, lookup, lookup, {"text": "Your repair is in progress."}])
    bot = make_bot(tmp_path, model)
    assert bot.respond("Is R200 ready?") == "Your repair is in progress."
    assert model.calls == 4
    assert len([m for m in bot.history if m["role"] == "tool"]) == 3


def test_model_cannot_execute_a_fourth_tool(tmp_path):
    lookup = {"tool": "look_up_repair", "arguments": {"ticket_id": "R200"}}
    bot = make_bot(tmp_path, FakeModel([lookup] * 4))
    reply = bot.respond("Is R200 ready?")
    assert "contact shop staff" in reply
    assert "passing you" not in reply
    assert len([m for m in bot.history if m["role"] == "tool"]) == 3


def test_model_cannot_store_generated_card_number(tmp_path):
    bot = make_bot(tmp_path, FakeModel([{"text": "4111.1111.1111.1111"}]))
    assert "contact shop staff" in bot.respond("Hello")
    assert "4111" not in str(bot.history)


@pytest.mark.parametrize(
    "value", ["4111\t1111\t1111\t1111", {"value": "4111111111111111"}]
)
def test_generated_sensitive_arguments_are_not_retained(tmp_path, value):
    bot = make_bot(
        tmp_path,
        FakeModel([{"tool": "check_part", "arguments": {"name": value}}]),
    )
    assert "contact shop staff" in bot.respond("Do you have inner tube?")
    assert "4111" not in str(bot.history)


def test_database_failure_returns_helpful_reply(tmp_path, monkeypatch):
    bot = make_bot(
        tmp_path,
        FakeModel([{"tool": "look_up_repair", "arguments": {"ticket_id": "R200"}}]),
    )

    def unavailable(*args):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(bot.tools, "run", unavailable)
    assert "database is unavailable" in bot.respond("Is R200 ready?")


def test_blank_question_does_not_call_model(tmp_path):
    bot = make_bot(tmp_path, FakeModel([]))
    assert "Please enter a question" in bot.respond("   ")
    assert bot.history == []


def test_keyword_lookup_uses_latest_question(tmp_path):
    bot = make_bot(tmp_path, KeywordModel())
    assert "R200 is in repair" in bot.respond("Is repair R200 ready?")
    assert "$8.00" in bot.respond("Do you have inner tube?")
    assert "R201 is ready" in bot.respond("Is repair R201 ready?")
    assert bot.count_user_messages() == 3
