"""Точка входа в курсовой проект."""

from dotenv import load_dotenv

from aviation_tracker.cli import user_interaction


if __name__ == "__main__":
    load_dotenv()
    user_interaction()

