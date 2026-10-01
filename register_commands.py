import os

import httpx
from dotenv import load_dotenv

load_dotenv()

APPLICATION_ID = os.environ["DISCORD_APPLICATION_ID"]
BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

URL = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands"

COMMANDS = [
    {
        "name": "status",
        "description": "Check the bot's status",
        "type": 1,
    },
    {
        "name": "report",
        "description": "Submit a report",
        "type": 1,
        "options": [
            {
                "name": "text",
                "description": "What are you reporting?",
                "type": 3,  # STRING
                "required": True,
            }
        ],
    },
]


def main():
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    for command in COMMANDS:
        response = httpx.post(URL, headers=headers, json=command)
        response.raise_for_status()
        data = response.json()
        print(f"Registered /{data['name']} (id={data['id']})")


if __name__ == "__main__":
    main()
