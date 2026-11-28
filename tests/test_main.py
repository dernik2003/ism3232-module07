"""Exercise customer chat and staff decisions without a live model."""

import sqlite3

import pytest

import database
import main


def start_demo(tmp_path, monkeypatch, answers):
    db_file = tmp_path / "demo.db"
    database.create_tables(db_file)
    monkeypatch.setattr(main, "DB_FILE", db_file)
    inputs = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    return db_file


def test_chat_and_approval_persist_after_restart(tmp_path, monkeypatch, capsys):
    db_file = start_demo(
        tmp_path,
        monkeypatch,
        [
            "Hello",
            "Is repair R200 ready?",
            "Do you have inner tube?",
            "Can I pay with a different card?",
            "quit",
            "yes",
        ],
    )
    number = database.add_change_request(db_file, "R201", "2026-12-01")
    main.main()
    output = capsys.readouterr().out
    assert "R200 is in repair" in output
    assert "$8.00" in output
    assert "contact shop staff" in output
    assert "Customer messages recorded: 3" in output
    assert "Request 1 approved." in output
    assert "R201 2026-12-01" in output

    monkeypatch.setattr("builtins.input", lambda prompt: "quit")
    main.main()
    output = capsys.readouterr().out
    assert "Approve?" not in output
    assert "R201 2026-12-01" in output
    assert database.find_request(db_file, number)["status"] == "approved"


@pytest.mark.parametrize("answer,status", [("no", "rejected"), ("later", "waiting")])
def test_staff_decline_or_skip_keeps_original_date(
    tmp_path, monkeypatch, answer, status
):
    db_file = start_demo(tmp_path, monkeypatch, ["quit", answer])
    number = database.add_change_request(db_file, "R200", "2026-12-01")
    main.main()
    assert database.find_request(db_file, number)["status"] == status
    assert database.find_repair(db_file, "R200")["pickup_date"] == "2026-11-20"


@pytest.mark.parametrize("error", [EOFError, KeyboardInterrupt])
def test_closed_input_does_not_approve_requests(tmp_path, monkeypatch, capsys, error):
    db_file = start_demo(tmp_path, monkeypatch, [])
    number = database.add_change_request(db_file, "R200", "2026-12-01")

    def closed_input(prompt):
        raise error

    monkeypatch.setattr("builtins.input", closed_input)
    main.main()
    assert "Pending requests remain waiting" in capsys.readouterr().out
    assert database.find_request(db_file, number)["status"] == "waiting"


def test_interrupted_staff_review_keeps_pending_request(tmp_path, monkeypatch, capsys):
    db_file = start_demo(tmp_path, monkeypatch, [])
    number = database.add_change_request(db_file, "R200", "2026-12-01")

    def input_until_review(prompt):
        if prompt.startswith("You:"):
            return "quit"
        raise EOFError

    monkeypatch.setattr("builtins.input", input_until_review)
    main.main()
    assert "Undecided requests remain waiting" in capsys.readouterr().out
    assert database.find_request(db_file, number)["status"] == "waiting"


def test_failed_approval_is_not_reported_as_success(tmp_path, monkeypatch, capsys):
    db_file = start_demo(tmp_path, monkeypatch, ["quit", "yes"])
    number = database.add_change_request(db_file, "R200", "2026-12-01")

    def fail(*args):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(main, "approve_request", fail)
    main.main()
    output = capsys.readouterr().out
    assert "Could not save" in output
    assert "Request 1 approved." not in output
    assert database.find_request(db_file, number)["status"] == "waiting"
