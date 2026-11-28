import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

import database


def make_db(tmp_path):
    """Create a fresh database just for this test."""
    db_file = tmp_path / "test.db"
    database.create_tables(db_file)
    return db_file


def test_create_tables_twice_adds_no_duplicate_rows(tmp_path):
    db_file = make_db(tmp_path)

    database.create_tables(db_file)

    assert len(database.all_repairs(db_file)) == 5
    assert len(database.part_names(db_file)) == 5
    assert database.waiting_requests(db_file) == []


def test_find_repair_needs_the_exact_id(tmp_path):
    db_file = make_db(tmp_path)

    repair = database.find_repair(db_file, "R200")

    assert isinstance(repair, dict)
    assert repair["status"] == "in repair"
    assert database.find_repair(db_file, "R20") is None
    assert database.find_repair(db_file, "R2000") is None
    assert database.find_repair(db_file, "R999") is None


def test_sql_in_a_ticket_id_is_just_text(tmp_path):
    db_file = make_db(tmp_path)

    repair = database.find_repair(db_file, "R200' OR '1'='1")

    assert repair is None
    assert len(database.all_repairs(db_file)) == 5


def test_change_requests_get_numbers_and_wait(tmp_path):
    db_file = make_db(tmp_path)

    first = database.add_change_request(db_file, "R200", "2026-12-01")
    second = database.add_change_request(db_file, "R201", "2026-12-02")

    assert first == 1
    assert second == 2

    request = database.find_request(db_file, first)
    assert request["ticket_id"] == "R200"
    assert request["new_value"] == "2026-12-01"
    assert request["status"] == "waiting"

    assert len(database.waiting_requests(db_file)) == 2
    assert database.find_repair(db_file, "R200")["pickup_date"] == "2026-11-20"


def test_approve_changes_the_pickup_date_once(tmp_path):
    db_file = make_db(tmp_path)
    number = database.add_change_request(db_file, "R200", "2026-12-01")

    assert database.approve_request(db_file, number) == "Request 1 approved."
    assert database.find_repair(db_file, "R200")["pickup_date"] == "2026-12-01"
    assert database.find_request(db_file, number)["status"] == "approved"

    assert database.approve_request(db_file, number) == "Request 1 is already approved."
    assert database.waiting_requests(db_file) == []


def test_reject_changes_nothing_and_cannot_be_approved_later(tmp_path):
    db_file = make_db(tmp_path)
    number = database.add_change_request(db_file, "R200", "2026-12-01")

    assert database.reject_request(db_file, number) == "Request 1 rejected."
    assert database.find_repair(db_file, "R200")["pickup_date"] == "2026-11-20"
    assert database.find_request(db_file, number)["status"] == "rejected"

    assert database.approve_request(db_file, number) == "Request 1 is already rejected."
    assert database.find_repair(db_file, "R200")["pickup_date"] == "2026-11-20"
    assert database.waiting_requests(db_file) == []


def test_approval_rolls_back_if_saving_status_fails(tmp_path):
    db_file = make_db(tmp_path)
    number = database.add_change_request(db_file, "R200", "2026-12-01")
    database.change(
        db_file,
        """CREATE TRIGGER fail_approval BEFORE UPDATE ON change_requests
           BEGIN SELECT RAISE(ABORT, 'simulated storage failure'); END""",
    )

    with pytest.raises(sqlite3.IntegrityError, match="storage failure"):
        database.approve_request(db_file, number)

    assert database.find_repair(db_file, "R200")["pickup_date"] == "2026-11-20"
    assert database.find_request(db_file, number)["status"] == "waiting"
    database.change(db_file, "DROP TRIGGER fail_approval")
    assert database.approve_request(db_file, number) == "Request 1 approved."


def test_duplicate_pending_request_keeps_one_number(tmp_path):
    db_file = make_db(tmp_path)
    first = database.add_change_request(db_file, "R200", "2026-12-01")
    second = database.add_change_request(db_file, "R200", "2026-12-01")

    assert first == second
    assert len(database.waiting_requests(db_file)) == 1
    database.reject_request(db_file, first)
    assert database.add_change_request(db_file, "R200", "2026-12-01") != first


@pytest.mark.parametrize("value", ["2026-02-30", "20261201", "tomorrow", None])
def test_direct_database_request_rejects_invalid_dates(tmp_path, value):
    db_file = make_db(tmp_path)
    with pytest.raises(ValueError, match="valid pickup date"):
        database.add_change_request(db_file, "R200", value)
    assert database.waiting_requests(db_file) == []


def test_direct_database_request_rejects_missing_repair(tmp_path):
    db_file = make_db(tmp_path)
    with pytest.raises(ValueError, match="No repair"):
        database.add_change_request(db_file, "R999", "2026-12-01")
    assert database.waiting_requests(db_file) == []


@pytest.mark.parametrize(
    "ticket_id,new_value,reason",
    [("R999", "2026-12-01", "missing repair"), ("R200", "bad", "invalid pickup date")],
)
def test_bad_legacy_request_cannot_be_approved(tmp_path, ticket_id, new_value, reason):
    db_file = make_db(tmp_path)
    number = database.change(
        db_file,
        "INSERT INTO change_requests (ticket_id, new_value) VALUES (?, ?)",
        (ticket_id, new_value),
    )
    assert reason in database.approve_request(db_file, number)
    assert database.find_request(db_file, number)["status"] == "waiting"
    assert database.find_repair(db_file, "R200")["pickup_date"] == "2026-11-20"


def test_schema_is_found_from_another_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_file = make_db(tmp_path)
    assert len(database.all_repairs(db_file)) == 5


def test_reopening_database_keeps_staff_decision(tmp_path):
    db_file = make_db(tmp_path)
    number = database.add_change_request(db_file, "R201", "2026-12-01")
    database.approve_request(db_file, number)
    database.create_tables(db_file)
    assert database.find_repair(db_file, "R201")["pickup_date"] == "2026-12-01"
    assert database.find_request(db_file, number)["status"] == "approved"


def test_missing_requests_have_clear_responses(tmp_path):
    db_file = make_db(tmp_path)
    assert database.approve_request(db_file, 99) == "There is no request 99."
    assert database.reject_request(db_file, 99) == "There is no request 99."


def test_two_staff_decisions_cannot_disagree_with_pickup_date(tmp_path):
    db_file = make_db(tmp_path)
    number = database.add_change_request(db_file, "R200", "2026-12-01")
    ready = Barrier(2)

    def decide(function):
        ready.wait(timeout=5)
        return function(db_file, number)

    with ThreadPoolExecutor(max_workers=2) as executor:
        approve = executor.submit(decide, database.approve_request)
        reject = executor.submit(decide, database.reject_request)
        replies = [approve.result(timeout=10), reject.result(timeout=10)]

    assert sum("already" in reply for reply in replies) == 1
    status = database.find_request(db_file, number)["status"]
    expected = "2026-12-01" if status == "approved" else "2026-11-20"
    assert status in {"approved", "rejected"}
    assert database.find_repair(db_file, "R200")["pickup_date"] == expected
