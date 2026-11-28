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
