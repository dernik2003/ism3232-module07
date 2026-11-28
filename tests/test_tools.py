import pytest

import database
from tools import SpokewellTools


def make_tools(tmp_path):
    """Build tools using a fresh temporary database."""
    db_file = tmp_path / "test.db"
    database.create_tables(db_file)
    return SpokewellTools(db_file)


def customer(text):
    """Create a conversation containing one customer message."""
    return [{"role": "user", "content": text}]


def test_lookup_finds_id_inside_a_sentence(tmp_path):
    tools = make_tools(tmp_path)
    message = "Is repair R200 ready?"

    reply = tools.run(
        "look_up_repair",
        {"ticket_id": message},
        customer(message),
    )

    assert "R200 is in repair" in reply
    assert "2026-11-20" in reply


def test_pickup_change_waits_for_staff(tmp_path):
    tools = make_tools(tmp_path)

    reply = tools.run(
        "request_pickup_change",
        {"ticket_id": "R200", "new_date": "2026-12-01"},
        customer("Move pickup for R200 to 2026-12-01."),
    )

    assert "sent to staff" in reply
    assert database.find_request(tools.db_file, 1)["status"] == "waiting"
    assert database.find_repair(tools.db_file, "R200")["pickup_date"] == "2026-11-20"


def test_unknown_tool_is_refused(tmp_path):
    tools = make_tools(tmp_path)

    reply = tools.run("delete_repair", {}, customer("Delete R200"))

    assert "There is no tool named delete_repair" in reply
    assert database.find_repair(tools.db_file, "R200") is not None


def test_missing_ticket_id_is_refused(tmp_path):
    tools = make_tools(tmp_path)

    reply = tools.run("look_up_repair", {}, customer("Where is my repair?"))

    assert "ticket ID is missing" in reply


def test_made_up_ticket_id_is_refused(tmp_path):
    tools = make_tools(tmp_path)

    reply = tools.run(
        "look_up_repair",
        {"ticket_id": "R201"},
        customer("Where is R200?"),
    )

    assert "has not given that ticket ID" in reply


def test_typo_ticket_id_does_not_authorize_a_real_ticket(tmp_path):
    tools = make_tools(tmp_path)
    history = customer("Move pickup for R2000 to 2026-12-01")

    lookup = tools.run(
        "look_up_repair",
        {"ticket_id": "R200"},
        history,
    )

    change = tools.run(
        "request_pickup_change",
        {"ticket_id": "R200", "new_date": "2026-12-01"},
        history,
    )

    assert "has not given that ticket ID" in lookup
    assert "has not given that ticket ID" in change
    assert database.waiting_requests(tools.db_file) == []


def test_made_up_pickup_date_is_refused(tmp_path):
    tools = make_tools(tmp_path)

    reply = tools.run(
        "request_pickup_change",
        {"ticket_id": "R200", "new_date": "2026-12-02"},
        customer("Move pickup for R200 to 2026-12-01"),
    )

    assert "has not given that pickup date" in reply
    assert database.waiting_requests(tools.db_file) == []


def test_invalid_calendar_date_is_refused(tmp_path):
    tools = make_tools(tmp_path)

    reply = tools.run(
        "request_pickup_change",
        {"ticket_id": "R200", "new_date": "2026-02-30"},
        customer("Move pickup for R200 to 2026-02-30"),
    )

    assert "valid pickup date" in reply
    assert database.waiting_requests(tools.db_file) == []


def test_part_lookup_reports_stock_and_price(tmp_path):
    tools = make_tools(tmp_path)

    reply = tools.run(
        "check_part",
        {"name": "inner tube"},
        customer("Do you have an inner tube?"),
    )

    assert "25" in reply
    assert "$8.00" in reply


def test_check_request_reports_staff_decision(tmp_path):
    tools = make_tools(tmp_path)
    number = database.add_change_request(tools.db_file, "R200", "2026-12-01")
    history = customer(f"What happened to request {number}?")

    waiting = tools.run("check_request", {"number": number}, history)
    assert "waiting for staff" in waiting

    database.reject_request(tools.db_file, number)

    decided = tools.run("check_request", {"number": number}, history)
    assert "was rejected" in decided


@pytest.mark.parametrize("arguments", [None, [], "R200", 7])
def test_malformed_argument_container_is_refused(tmp_path, arguments):
    tools = make_tools(tmp_path)
    reply = tools.run("request_pickup_change", arguments, customer("R200 2026-12-01"))
    assert "named values" in reply
    assert database.waiting_requests(tools.db_file) == []


@pytest.mark.parametrize("value", [None, True, [], {"id": "R200"}])
def test_invalid_argument_value_is_treated_as_missing(tmp_path, value):
    tools = make_tools(tmp_path)
    reply = tools.run("look_up_repair", {"ticket_id": value}, customer("R200"))
    assert "ticket ID is missing" in reply


def test_part_with_zero_stock_is_reported(tmp_path):
    tools = make_tools(tmp_path)
    reply = tools.run("check_part", {"name": "brake pads"}, customer("brake pads"))
    assert "0 of the brake pads" in reply
    assert "$15.00" in reply


def test_repeated_tool_change_does_not_duplicate_request(tmp_path):
    tools = make_tools(tmp_path)
    arguments = {"ticket_id": "R200", "new_date": "2026-12-01"}
    history = customer("Move pickup for R200 to 2026-12-01")
    first = tools.run("request_pickup_change", arguments, history)
    second = tools.run("request_pickup_change", arguments, history)
    assert first == second
    assert len(database.waiting_requests(tools.db_file)) == 1


def test_request_number_must_be_supplied_by_customer(tmp_path):
    tools = make_tools(tmp_path)
    database.add_change_request(tools.db_file, "R200", "2026-12-01")
    reply = tools.run("check_request", {"number": 1}, customer("What happened?"))
    assert "has not given that request number" in reply


def test_approved_request_is_reported_from_database(tmp_path):
    tools = make_tools(tmp_path)
    number = database.add_change_request(tools.db_file, "R200", "2026-12-01")
    database.approve_request(tools.db_file, number)
    reply = tools.run(
        "check_request", {"number": number}, customer(f"Request {number}")
    )
    assert "was approved" in reply
