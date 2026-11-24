# Capstone Proposal: Spokewell Bike Repair

Author: YOUR NAME

## The business

Spokewell is a local bicycle repair shop. Customers
often contact the shop to check repair status, part
availability and pickup dates. The assistant will
help answer these questions and reduce staff workload.

## Who uses it

Chat: customers.
Staff tab: bike shop employees.

## Tables

repairs:
ticket_id TEXT PRIMARY KEY,
customer TEXT NOT NULL,
bike TEXT NOT NULL,
status TEXT NOT NULL,
pickup_date TEXT NOT NULL

Example: R200, Jordan Lee, road bike, in repair, 2026-11-20

parts:
name TEXT PRIMARY KEY,
price REAL NOT NULL,
stock INTEGER NOT NULL

Example: inner tube, 8.00, 25

change_requests:
number INTEGER PRIMARY KEY AUTOINCREMENT,
ticket_id TEXT NOT NULL,
new_value TEXT NOT NULL,
status TEXT NOT NULL DEFAULT 'waiting'

The change_requests table starts empty.

## Lookup tools

look_up_repair(ticket_id):
Checks the repair status and pickup date.
The ticket ID must be valid and exist.
Example: Is repair R200 ready?

check_part(name):
Checks the price and quantity of a bicycle part.
The part name cannot be empty.
Example: Do you have brake pads?

Both tools only read information from the database.

## Change tool

request_pickup_change(ticket_id, new_date):
Checks that the ticket exists and the date is valid.
Creates a waiting request for staff to review.

Staff can approve or reject the request. Approval
updates the pickup_date in repairs and changes the
request status to approved. Rejection leaves the
original pickup date unchanged.

## Handoff rule

Words: payment, card

These messages will be intercepted before reaching
the model. Employees must handle payment issues
because the assistant cannot process payments.

The reason for the handoff will be documented
in the README.

## Data it never stores

Credit and debit card numbers. These must never
be stored or passed to the model. Messages containing
card details must be intercepted before processing.

## Instructions draft

You are a customer support assistant for Spokewell
Bike Repair.

The shop is open Monday through Saturday,
9 am to 6 pm.

Customers can check repairs, part availability
and request a different pickup date.

Pickup date changes require employee approval.
Do not tell customers a request is approved
unless staff have approved it.

Ask for missing information before filing requests.
Keep responses short and clear.
Do not invent repair information.

Only state facts that appear in these instructions or in tool results.

## Five sample conversations

1. Customer: "Is my repair R200 ready?"
   Must: use look_up_repair.

2. Customer: "Do you have brake pads?"
   Must: use check_part.

3. Customer: "Move pickup for R201 to 2026-12-01."
   Must: file 1 change.

4. Customer: "Can I pay with a different card?"
   Must: hand off.

5. Customer: "Change my pickup date to 2026-12-03."
   Must: file 0 changes because the ticket ID
   was not provided.

## Out of scope

- Processing payments or refunds.
- Diagnosing mechanical problems.
- Verifying customer identity.
- Changing repair prices.

## Checklist

- [x] One business with customer chat and Staff tab.
- [x] Two business tables and change_requests.
- [x] Two read-only lookup tools with validation.
- [x] Change requests require staff approval.
- [x] Handoff rule before the model.
- [x] Sensitive payment information excluded.
- [x] Business instructions with factual restrictions.
- [x] Five sample conversations including safety.
