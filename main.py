# main.py
# Author: Nikita Lemeshenko

from agent import SupportChatbot
from database import (
    all_repairs,
    approve_request,
    create_tables,
    reject_request,
    waiting_requests,
)
from keyword_model import KeywordModel
from settings import DB_FILE, INSTRUCTIONS
from tools import SpokewellTools


def main():
    """Run customer chat, then let staff review pickup changes."""
    create_tables(DB_FILE)

    bot = SupportChatbot(
        "Jamie",
        INSTRUCTIONS,
        SpokewellTools(DB_FILE),
        KeywordModel(),
    )

    print("Spokewell Bike Repair")
    print("Type a message, or type quit to stop.")

    while True:
        user_message = input("You: ")

        if user_message.strip().lower() == "quit":
            break

        print(f"{bot.name}: {bot.respond(user_message)}")

    print(f"Messages in this conversation: {len(bot.history)}")

    print("\nStaff review")

    for request in waiting_requests(DB_FILE):
        number = request["number"]

        print(
            f"Request {number}: repair {request['ticket_id']} "
            f"to pickup date {request['new_value']}"
        )

        answer = input("Approve? yes or no: ").strip().lower()

        if answer == "yes":
            print(approve_request(DB_FILE, number))
        elif answer == "no":
            print(reject_request(DB_FILE, number))
        else:
            print(f"Request {number} is still waiting.")

    print("\nCurrent pickup dates")

    for repair in all_repairs(DB_FILE):
        print(repair["ticket_id"], repair["pickup_date"])


if __name__ == "__main__":
    main()
