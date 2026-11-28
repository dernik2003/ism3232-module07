# database.py
# Author: Nikita Lemeshenko

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path


def query_all(db_file, sql, values=()):
    """Run a SELECT and return every row as a dictionary."""
    with closing(sqlite3.connect(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, values).fetchall()
        return [dict(row) for row in rows]


def query_one(db_file, sql, values=()):
    """Return the first matching row as a dictionary, or None."""
    rows = query_all(db_file, sql, values)
    if rows == []:
        return None
    return rows[0]


def change(db_file, sql, values=()):
    """Save an INSERT or UPDATE and return the last inserted row ID."""
    with closing(sqlite3.connect(db_file)) as conn, conn:
        cursor = conn.execute(sql, values)
        return cursor.lastrowid


def create_tables(db_file):
    """Create the tables and sample rows unless they already exist."""
    script = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with closing(sqlite3.connect(db_file)) as conn, conn:
        conn.executescript(script)


def find_repair(db_file, ticket_id):
    """Return one repair by its exact ticket ID, or None."""
    return query_one(
        db_file,
        "SELECT * FROM repairs WHERE ticket_id = ?",
        (ticket_id,),
    )


def find_part(db_file, name):
    """Return one part by its exact name, or None."""
    return query_one(
        db_file,
        "SELECT * FROM parts WHERE name = ?",
        (name,),
    )


def part_names(db_file):
    """Return the names of all parts."""
    rows = query_all(db_file, "SELECT name FROM parts")
    return [row["name"] for row in rows]


def all_repairs(db_file):
    """Return all repairs in ticket ID order."""
    return query_all(
        db_file,
        "SELECT * FROM repairs ORDER BY ticket_id",
    )


def add_change_request(db_file, ticket_id, new_value):
    """File a valid change, reusing an identical request that is still waiting."""
    validate_pickup_date(new_value)
    with closing(sqlite3.connect(db_file)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        repair = conn.execute(
            "SELECT ticket_id FROM repairs WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if repair is None:
            raise ValueError("No repair with that ticket ID was found.")

        waiting = conn.execute(
            """SELECT number FROM change_requests
               WHERE ticket_id = ? AND new_value = ? AND status = ?
               ORDER BY number LIMIT 1""",
            (ticket_id, new_value, "waiting"),
        ).fetchone()
        if waiting is not None:
            return waiting[0]

        cursor = conn.execute(
            "INSERT INTO change_requests (ticket_id, new_value) VALUES (?, ?)",
            (ticket_id, new_value),
        )
        return cursor.lastrowid


def validate_pickup_date(value):
    """Require a real calendar date written exactly as YYYY-MM-DD."""
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Use a valid pickup date in YYYY-MM-DD format.") from None
    if parsed.isoformat() != value:
        raise ValueError("Use a valid pickup date in YYYY-MM-DD format.")


def find_request(db_file, number):
    """Return one change request by number, or None."""
    return query_one(
        db_file,
        "SELECT * FROM change_requests WHERE number = ?",
        (number,),
    )


def waiting_requests(db_file):
    """Return requests that still need a staff decision."""
    return query_all(
        db_file,
        """
        SELECT * FROM change_requests
        WHERE status = ?
        ORDER BY number
        """,
        ("waiting",),
    )


def approve_request(db_file, number):
    """Save the pickup date and approval together, or roll both back on failure."""
    with closing(sqlite3.connect(db_file)) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        request = conn.execute(
            "SELECT * FROM change_requests WHERE number = ?", (number,)
        ).fetchone()
        if request is None:
            return f"There is no request {number}."
        if request["status"] != "waiting":
            return f"Request {number} is already {request['status']}."

        try:
            validate_pickup_date(request["new_value"])
        except ValueError:
            return f"Request {number} has an invalid pickup date and remains waiting."

        cursor = conn.execute(
            "UPDATE repairs SET pickup_date = ? WHERE ticket_id = ?",
            (request["new_value"], request["ticket_id"]),
        )
        if cursor.rowcount != 1:
            return f"Request {number} refers to a missing repair and remains waiting."

        conn.execute(
            "UPDATE change_requests SET status = ? WHERE number = ?",
            ("approved", number),
        )

    return f"Request {number} approved."


def reject_request(db_file, number):
    """Reject a waiting request without changing the pickup date."""
    with closing(sqlite3.connect(db_file)) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        request = conn.execute(
            "SELECT * FROM change_requests WHERE number = ?", (number,)
        ).fetchone()
        if request is None:
            return f"There is no request {number}."
        if request["status"] != "waiting":
            return f"Request {number} is already {request['status']}."
        conn.execute(
            "UPDATE change_requests SET status = ? WHERE number = ?",
            ("rejected", number),
        )

    return f"Request {number} rejected."
