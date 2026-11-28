# main.py
# Author: Nikita Lemeshenko

import sqlite3

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
        try:
            user_message = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nChat ended. Pending requests remain waiting for staff.")
            return

        if user_message.strip().lower() == "quit":
            break

        print(f"{bot.name}: {bot.respond(user_message)}")

    print(f"Customer messages recorded: {bot.count_user_messages()}")

    print("\nStaff review")

    for request in waiting_requests(DB_FILE):
        number = request["number"]

        print(
            f"Request {number}: repair {request['ticket_id']} "
            f"to pickup date {request['new_value']}"
        )

        try:
            answer = input("Approve? yes or no: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nStaff review ended. Undecided requests remain waiting.")
            break

        try:
            if answer == "yes":
                print(approve_request(DB_FILE, number))
            elif answer == "no":
                print(reject_request(DB_FILE, number))
            else:
                print(f"Request {number} is still waiting.")
        except sqlite3.Error:
            print(
                f"Could not save the decision for request {number}. Please try again."
            )

    print("\nCurrent pickup dates")

    for repair in all_repairs(DB_FILE):
        print(repair["ticket_id"], repair["pickup_date"])


if __name__ == "__main__":
    try:
        main()
    except sqlite3.Error:
        print("The database is unavailable. Check the database file and try again.")
        raise SystemExit(1)
