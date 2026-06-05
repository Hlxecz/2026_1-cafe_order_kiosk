from __future__ import annotations

from datetime import datetime, timezone


def local_now() -> datetime:
    return datetime.now().astimezone()


def format_money(amount: int) -> str:
    return f"{amount:,}"
