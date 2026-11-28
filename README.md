# Spokewell Bike Repair — Lab 14

Author: Nikita Lemeshenko

## Project

This application uses SQLite to look up repair status, pickup dates,
part prices, and stock. Pickup changes are saved as waiting requests.
Staff can approve or reject them. Approval changes the pickup date;
rejection leaves it unchanged. Decisions persist between program runs.

## Running the application

Install dependencies with:
python -m pip install -r requirements.txt

Start the application from the project folder with:
python main.py

The default keyword model runs without Ollama. Try:
- Is repair R200 ready?
- Do you have inner tube?
- Can I pay with a different card?

Type quit to end the chat and start staff review.
Enter yes to approve a waiting request or no to reject it.

The keyword model handles lookups only. Pickup requests can be filed
through the request_pickup_change tool or directly with
database.add_change_request before running the staff review.

The Ollama adapter is included and limits the decide method to the
last 20 history entries. It is not enabled in the default main.py.

## Guardrails

SQL values use placeholders. Customer-supplied ticket IDs, pickup dates,
and request numbers are checked before the tools run. Whole-word matching
prevents R200 from matching R2000. Pickup dates must be valid calendar dates.

Payment and card questions are referred to staff because the application
does not process payments. These messages are intercepted before entering
history or reaching the model. Common card-number patterns are also
intercepted. This is a classroom safeguard, not a complete sensitive-data detector.

Staff approval is separate from the customer tools. This terminal demo
assumes staff control the terminal during review; it has no staff login.

## Testing

Run from the project folder:
ruff format .
ruff check .
pytest -v

The suite contains 20 tests: 6 database, 10 tool, and 4 agent tests.
Tests use temporary databases and do not contact an Ollama server.

An offline terminal demonstration confirmed that staff approval updates
a pickup date and that the change remains after restarting the application.
