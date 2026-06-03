from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from cafe_order_kiosk.utils import utc_now


class OrderStatus(str, Enum):
    OPEN = "open"
    PAID = "paid"
    CANCELED = "canceled"


@dataclass(frozen=True)
class MenuItem:
    id: int
    name: str
    price: int
    category: str | None = None
    description: str | None = None
    is_available: bool = True


OPTION_PRICES: dict[str, int] = {
    "샷추가": 500,
    "사이즈업": 1000,
    "휘핑크림": 500,
    "시럽추가": 300,
    "디카페인": 300,
}


@dataclass
class OrderItem:
    menu_item_id: int
    name: str
    unit_price: int
    quantity: int
    options: list[str] = field(default_factory=list)

    @property
    def surcharge(self) -> int:
        return sum(OPTION_PRICES.get(opt.strip(), 0) for opt in self.options)

    @property
    def line_total(self) -> int:
        return (self.unit_price + self.surcharge) * self.quantity



@dataclass(frozen=True)
class Payment:
    method: str
    amount: int
    paid_at: datetime


@dataclass
class Order:
    id: int
    items: list[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.OPEN
    created_at: datetime = field(default_factory=utc_now)
    paid_at: datetime | None = None
    canceled_at: datetime | None = None
    note: str | None = None
    payment: Payment | None = None

    @property
    def total(self) -> int:
        return sum(item.line_total for item in self.items)
