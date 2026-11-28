# database.py
# Author: Nikita Lemeshenko

import sqlite3


def query_all(db_file, sql, values=()):
    """Run a SELECT and return every row as a dictionary."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, values).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def query_one(db_file, sql, values=()):
    """Return the first matching row as a dictionary, or None."""
    rows = query_all(db_file, sql, values)
    if rows == []:
        return None
    return rows[0]


def change(db_file, sql, values=()):
    """Save an INSERT or UPDATE and return the last inserted row ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.execute(sql, values)
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def create_tables(db_file):
    """Create the tables and sample rows unless they already exist."""
    with open("schema.sql") as f:
        script = f.read()
    conn = sqlite3.connect(db_file)
    conn.executescript(script)
    conn.commit()
    conn.close()


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
    """File a pickup change request without changing the repair."""
    return change(
        db_file,
        """
        INSERT INTO change_requests (ticket_id, new_value)
        VALUES (?, ?)
        """,
        (ticket_id, new_value),
    )


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
    """Apply a waiting pickup change and mark it approved."""
    request = find_request(db_file, number)

    if request is None:
        return f"There is no request {number}."

    if request["status"] != "waiting":
        return f"Request {number} is already {request['status']}."

    change(
        db_file,
        "UPDATE repairs SET pickup_date = ? WHERE ticket_id = ?",
        (request["new_value"], request["ticket_id"]),
    )

    change(
        db_file,
        "UPDATE change_requests SET status = ? WHERE number = ?",
        ("approved", number),
    )

    return f"Request {number} approved."


def reject_request(db_file, number):
    """Reject a waiting request without changing the pickup date."""
    request = find_request(db_file, number)

    if request is None:
        return f"There is no request {number}."

    if request["status"] != "waiting":
        return f"Request {number} is already {request['status']}."

    change(
        db_file,
        "UPDATE change_requests SET status = ? WHERE number = ?",
        ("rejected", number),
    )

    return f"Request {number} rejected."
