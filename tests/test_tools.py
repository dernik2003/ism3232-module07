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
