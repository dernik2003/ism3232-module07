# Spokewell Bike Repair — Lab 14

Author: Nikita Lemeshenko

## Project

This application uses SQLite to look up repair status, pickup dates,
part prices, and stock. Pickup changes are saved as waiting requests.
Staff can approve or reject them. Approval changes the pickup date;
rejection leaves it unchanged. Decisions persist between program runs.

## Running the application

Install dependencies with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start the application from the project folder with:

```bash
python main.py
```

The schema and application database are located beside the Python files,
so launching the script from another directory uses the same database.

The default keyword model runs without Ollama. Try:

- Is repair R200 ready?
- Do you have inner tube?
- Can I pay with a different card?

Type quit to end the chat and start staff review.
Enter yes to approve a waiting request or no to reject it.

The keyword model handles lookups only. Pickup requests can be filed
through the request_pickup_change tool or directly with
database.add_change_request before running the staff review.

For example, run this from the project folder to file a sample request:

```bash
python -c 'import database; from settings import DB_FILE; database.create_tables(DB_FILE); print(database.add_change_request(DB_FILE, "R201", "2026-12-01"))'
python main.py
```

Type `quit`, then `yes` during staff review. Start the program again and ask
`Is repair R201 ready?` to check the saved pickup date. Repeating an identical
request while it is waiting returns the existing request number.

The Ollama adapter is included and limits the decide method to the
last 20 history entries. It is not enabled in the default main.py. Model calls
have a 60-second timeout; connection errors, timeouts, and empty replies can
fall back through `FallbackModel` when that model is configured.

## Guardrails

SQL values use placeholders. Customer-supplied ticket IDs, pickup dates,
and request numbers are checked before the tools run. Whole-word matching
prevents R200 from matching R2000. Pickup dates must be valid calendar dates.
Direct database requests also require an existing repair and a valid date.
Approval saves the pickup date and request status in one transaction. A failed
write rolls back both updates, and simultaneous staff decisions are serialized.

Payment and card questions are referred to staff because the application
does not process payments. These messages are intercepted before entering
history or reaching the model. The detector covers contiguous 13–19 digit
numbers, four groups of four digits, and the 4-6-5 format, with whitespace,
dots, slashes, or hyphens between groups. It also screens model responses and
tool results before retaining them. This is a classroom safeguard, not a
complete sensitive-data detector; unusual encodings or spelled-out numbers
are not guaranteed to be detected. Do not enter real payment information.

Staff approval is separate from the customer tools. This terminal demo
assumes staff control the terminal during review; it has no staff login.
The program directs people to staff; it does not actually transfer a conversation.
Closing input or pressing Ctrl+C leaves undecided requests waiting.

## Testing

Run from the project folder:

```bash
ruff format .
ruff check .
python -m pytest -v
```

Tests cover the database, tools, agent, and terminal workflow, including
failed database writes, duplicate requests, simultaneous staff decisions,
malformed model replies, payment screening, interrupted input, and persistence.
Tests use temporary databases and do not contact an Ollama server.

An offline terminal demonstration confirmed that staff approval updates
a pickup date and that the change remains after restarting the application.
