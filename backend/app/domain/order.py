"""Доменные сущности заказа."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .exceptions import (
    InvalidQuantityError,
    InvalidPriceError, InvalidAmountError, OrderCancelledError, OrderAlreadyPaidError,
)


# TODO: Реализовать OrderStatus (str, Enum)
# Значения: CREATED, PAID, CANCELLED, SHIPPED, COMPLETED
class OrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"
    COMPLETED = "completed"


# TODO: Реализовать OrderItem (dataclass)
# Поля: product_name, price, quantity, id, order_id
# Свойство: subtotal (price * quantity)
# Валидация: quantity > 0, price >= 0
@dataclass
class OrderItem:
    product_name: str
    price: Decimal
    quantity: int
    order_id: uuid.UUID | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    @property
    def subtotal(self) -> Decimal:
        return self.price * self.quantity

    def __post_init__(self):
        if not self.product_name or not self.product_name.strip():
            raise ValueError("Имя не может быть пустым")

        if self.quantity <= 0:
            raise InvalidQuantityError(self.quantity)

        if self.price < Decimal("0"):
            raise InvalidPriceError(self.price)


# TODO: Реализовать OrderStatusChange (dataclass)
# Поля: order_id, status, changed_at, id
@dataclass
class OrderStatusChange:
    order_id: uuid.UUID
    status: OrderStatus
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    changed_at: datetime = field(default_factory=datetime.now)


# TODO: Реализовать Order (dataclass)
# Поля: user_id, id, status, total_amount, created_at, items, status_history
# Методы:
#   - add_item(product_name, price, quantity) -> OrderItem
#   - pay() -> None  [КРИТИЧНО: нельзя оплатить дважды!]
#   - cancel() -> None
#   - ship() -> None
#   - complete() -> None
@dataclass
class Order:
    user_id: uuid.UUID
    created_at: datetime = field(default_factory=datetime.now)
    status: OrderStatus = OrderStatus.CREATED
    total_amount: Decimal = Decimal("0")
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    items: list[OrderItem] = field(default_factory=list)
    status_history: list[OrderStatusChange] = field(default_factory=list)

    def __post_init__(self):
        self.status_history.append(
            OrderStatusChange(order_id=self.id, status=self.status)
        )

    def add_item(self, product_name: str, price: Decimal, quantity: int) -> OrderItem:
        if self.status == OrderStatus.CANCELLED:
            raise OrderCancelledError(self.id)

        item = OrderItem(
            product_name=product_name,
            price=price,
            quantity=quantity,
            order_id=self.id,
        )

        self.items.append(item)
        self._recalculate_total()
        return item

    def pay(self) -> None:
        if self.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError(self.id)

        if self.status == OrderStatus.CANCELLED:
            raise OrderCancelledError(self.id)

        self._change_status(OrderStatus.PAID)

    def cancel(self) -> None:
        if self.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError(self.id)
        if self.status == OrderStatus.CANCELLED:
            return

        self._change_status(OrderStatus.CANCELLED)

    def ship(self) -> None:
        if self.status != OrderStatus.PAID:
            raise ValueError("Только оплаченные товары могут быть отгружены")

        self._change_status(OrderStatus.SHIPPED)

    def complete(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise ValueError("Только отгруженные товары могут быть завершены")

        self._change_status(OrderStatus.COMPLETED)

    def _change_status(self, new_status: OrderStatus) -> None:
        self.status = new_status
        self.status_history.append(
            OrderStatusChange(order_id=self.id, status=new_status)
        )

    def _recalculate_total(self) -> None:
        total = sum(item.subtotal for item in self.items)
        if total < Decimal("0"):
            raise InvalidAmountError(total)

        self.total_amount = total
