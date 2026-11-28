# tools.py
# Author: Nikita Lemeshenko

import database


class SpokewellTools:
    """Database tools checked by run before the agent may use them."""

    def __init__(self, db_file):
        """Remember which database to use."""
        self.db_file = db_file

    def tool_list(self):
        """Return the customer tools available to the model."""
        return [
            self.look_up_repair,
            self.check_part,
            self.request_pickup_change,
            self.check_request,
        ]

    def look_up_repair(self, ticket_id):
        """Look up a repair's status and pickup date.

        Args:
            ticket_id: The repair ticket ID, like R200.
        """
        for word in ticket_id.upper().split():
            repair = database.find_repair(self.db_file, word.strip("?.!,#"))
            if repair is not None:
                return (
                    f"Repair {repair['ticket_id']} is {repair['status']}; "
                    f"the pickup date is {repair['pickup_date']}."
                )
        return "No repair with that ticket ID was found. IDs look like R200."

    def check_part(self, name):
        """Check a bicycle part's stock and price.

        Args:
            name: The part name, like inner tube or brake pads.
        """
        for part_name in database.part_names(self.db_file):
            if self.words(part_name) in self.words(name):
                part = database.find_part(self.db_file, part_name)
                return (
                    f"We have {part['stock']} of the {part_name} in stock, "
                    f"at ${part['price']:.2f} each."
                )
        return "That part was not found."

    def request_pickup_change(self, ticket_id, new_date):
        """File a pickup change request that staff must approve.

        Args:
            ticket_id: The repair ticket ID, like R200.
            new_date: The requested pickup date in YYYY-MM-DD format.
        """
        ticket_id = ticket_id.upper()

        if database.find_repair(self.db_file, ticket_id) is None:
            return "No repair with that ticket ID was found. IDs look like R200."

        try:
            number = database.add_change_request(self.db_file, ticket_id, new_date)
        except ValueError as error:
            return str(error)
        return (
            f"Request {number} was sent to staff. The pickup date has not changed yet."
        )

    def check_request(self, number):
        """Check the saved staff decision about a pickup change.

        Args:
            number: The request number, like 1.
        """
        try:
            request = database.find_request(self.db_file, int(number))
        except ValueError:
            return "Request numbers look like 1."
        except OverflowError:
            return f"There is no request {number}."

        if request is None:
            return f"There is no request {number}."

        ticket_id = request["ticket_id"]

        if request["status"] == "waiting":
            return f"Request {number} for repair {ticket_id} is waiting for staff."

        return f"Request {number} for repair {ticket_id} was {request['status']}."

    def run(self, name, arguments, history):
        """Run a tool only after its required checks pass."""
        if not isinstance(arguments, dict):
            return "The tool arguments must be an object with named values."

        if name == "look_up_repair":
            ticket_id = self.clean(arguments, "ticket_id")

            if ticket_id == "":
                return "The ticket ID is missing. Ask the customer for it."

            if not self.customer_said(history, ticket_id):
                return "The customer has not given that ticket ID. Ask them for it."

            return self.look_up_repair(ticket_id)

        if name == "check_part":
            part_name = self.clean(arguments, "name")

            if part_name == "":
                return "The part name is missing. Ask the customer which part."

            return self.check_part(part_name)

        if name == "request_pickup_change":
            ticket_id = self.clean(arguments, "ticket_id")
            new_date = self.clean(arguments, "new_date")

            if ticket_id == "" or new_date == "":
                return "The ticket ID and the new pickup date are both needed."

            if not self.customer_said(history, ticket_id):
                return "The customer has not given that ticket ID. Ask them for it."

            if not self.customer_said(history, new_date):
                return "The customer has not given that pickup date. Ask them for it."

            return self.request_pickup_change(ticket_id, new_date)

        if name == "check_request":
            number = self.clean(arguments, "number")

            if number == "":
                return "The request number is missing. Ask the customer for it."

            if not self.customer_said(history, number):
                return (
                    "The customer has not given that request number. Ask them for it."
                )

            return self.check_request(number)

        return f"There is no tool named {name}."

    def clean(self, arguments, key):
        """Return an argument as stripped text, or empty text if missing."""
        value = arguments.get(key)
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            return ""
        return str(value).strip()

    def words(self, text):
        """Normalize case and punctuation for whole-word matching."""
        cleaned = []
        for word in text.lower().split():
            cleaned.append(word.strip("?.!,#"))
        return " " + " ".join(cleaned) + " "

    def customer_said(self, history, text):
        """Check whether the customer typed this text as whole words."""
        wanted = self.words(text)
        for message in history:
            if message["role"] == "user" and wanted in self.words(message["content"]):
                return True
        return False
