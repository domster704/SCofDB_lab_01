"""Доменные сущности заказа."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
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
    order_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def subtotal(self) -> Decimal:
        return self.price * self.quantity

    def __post_init__(self):
        if not self.product_name or not self.product_name.strip():
            raise ValueError("Имя не может быть пустым")

        if self.quantity <= 0:
            raise InvalidQuantityError("Количество должно быть больше 0")

        if self.price < Decimal("0"):
            raise InvalidPriceError("Цена должна быть больше или равна 0")


# TODO: Реализовать OrderStatusChange (dataclass)
# Поля: order_id, status, changed_at, id
@dataclass
class OrderStatusChange:
    order_id: str
    status: OrderStatus
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    changed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


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
    user_id: str
    id: str
    created_at: datetime
    status: OrderStatus
    total_amount: Decimal
    items: list[OrderItem] = field(default_factory=list)
    status_history: list[OrderStatusChange] = field(default_factory=list)

    def __post_init__(self):
        self.status_history.append(
            OrderStatusChange(order_id=self.id, status=self.status)
        )

    def add_item(self, product_name: str, price: Decimal, quantity: int) -> OrderItem:
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
            raise OrderAlreadyPaidError("Заказ уже оплачен")

        if self.status == OrderStatus.CANCELLED:
            raise OrderCancelledError("Нельзя оплатить отменённый заказ")

        if self.total_amount <= Decimal("0"):
            raise InvalidAmountError("Нельзя оплатить заказ с нулевым количеством")

        self._change_status(OrderStatus.PAID)

    def cancel(self) -> None:
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
            raise InvalidAmountError("Количество не может быть отрицательным")

        self.total_amount = total
