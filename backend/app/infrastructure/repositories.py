"""Реализация репозиториев с использованием SQLAlchemy."""

import uuid
from typing import Optional, List

from app.domain.order import Order, OrderItem, OrderStatus, OrderStatusChange
from app.domain.user import User
from sqlalchemy import text, TextClause
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    """Репозиторий для User."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # TODO: Реализовать save(user: User) -> None
    # Используйте INSERT ... ON CONFLICT DO UPDATE
    async def save(self, user: User) -> None:
        query: TextClause = text("""
                                 INSERT INTO users(id, email, name, created_at)
                                 VALUES (:id, :email, :name, :created_at)
                                 ON CONFLICT (id)
                                     DO UPDATE SET email = EXCLUDED.email,
                                                   name  = EXCLUDED.name
                                 """)

        await self.session.execute(query, {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at
        })

    # TODO: Реализовать find_by_id(user_id: UUID) -> Optional[User]
    async def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.session.execute(
            text("SELECT * FROM users WHERE id=:id"),
            {
                "id": str(user_id)
            }
        )
        row = result.fetchone()
        if not row:
            return None

        return User(
            id=row.id,
            email=row.email,
            name=row.name,
            created_at=row.created_at
        )

    # TODO: Реализовать find_by_email(email: str) -> Optional[User]
    async def find_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            text("SELECT * FROM users WHERE email=:email"),
            {
                "email": email
            }
        )
        row = result.fetchone()
        if not row:
            return None

        return User(
            id=row.id,
            email=row.email,
            name=row.name,
            created_at=row.created_at
        )

    # TODO: Реализовать find_all() -> List[User]
    async def find_all(self) -> List[User]:
        result = await self.session.execute(
            text("SELECT * FROM users")
        )
        rows = result.fetchall()
        return [
            User(
                id=r.id,
                email=r.email,
                name=r.name,
                created_at=r.created_at
            )
            for r in rows
        ]


class OrderRepository:
    """Репозиторий для Order."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # TODO: Реализовать save(order: Order) -> None
    # Сохранить заказ, товары и историю статусов
    async def save(self, order: Order) -> None:
        query: TextClause = text("""
                                 INSERT INTO orders(id, user_id, status, total_amount, created_at)
                                 VALUES (:id, :user_id, :status, :total_amount, :created_at)
                                 ON CONFLICT (id)
                                     DO UPDATE SET status       = EXCLUDED.status,
                                                   total_amount = EXCLUDED.total_amount
                                 """)
        await self.session.execute(query, {
            "id": order.id,
            "user_id": order.user_id,
            "status": order.status.value,
            "total_amount": order.total_amount,
            "created_at": order.created_at
        })
        await self._save_order_items(order.items)
        await self._save_status_history(order.status_history)

    # TODO: Реализовать find_by_id(order_id: UUID) -> Optional[Order]
    # Загрузить заказ со всеми товарами и историей
    # Используйте object.__new__(Order) чтобы избежать __post_init__
    async def find_by_id(self, order_id: uuid.UUID) -> Optional[Order]:
        query: TextClause = text("""
                                 SELECT *
                                 FROM orders
                                 WHERE id = :id
                                 """)
        result = await self.session.execute(query, {"id": str(order_id)})

        row = result.fetchone()
        if not row:
            return None

        order_id = row.id

        items: list[OrderItem] = await self._load_items(order_id)
        status_history: list[OrderStatusChange] = await self._load_status_history(order_id)

        order = Order(
            id=row.id,
            user_id=row.user_id,
            status=OrderStatus(row.status),
            total_amount=row.total_amount,
            created_at=row.created_at,
            items=items,
            status_history=status_history
        )

        return order

    # TODO: Реализовать find_by_user(user_id: UUID) -> List[Order]
    async def find_by_user(self, user_id: uuid.UUID) -> List[Order]:
        query: TextClause = text("""
                                 SELECT id
                                 FROM orders
                                 WHERE user_id = :uid
                                 """)
        result = await self.session.execute(query, {"uid": str(user_id)})

        ids = [row.id for row in result.fetchall()]
        return await self._load_orders_by_ids(ids)

    # TODO: Реализовать find_all() -> List[Order]
    async def find_all(self) -> List[Order]:
        query: TextClause = text("""
                                 SELECT id
                                 FROM orders
                                 """)
        result = await self.session.execute(query)

        ids = [row.id for row in result.fetchall()]
        return await self._load_orders_by_ids(ids)

    async def _save_order_items(self, items: list[OrderItem]) -> None:
        query: TextClause = text("""
                                 INSERT INTO order_items(id, order_id, product_name, price, quantity)
                                 VALUES (:id, :order_id, :product_name, :price, :quantity)
                                 ON CONFLICT (id) DO NOTHING
                                 """)
        for item in items:
            await self.session.execute(query, {
                "id": item.id,
                "order_id": item.order_id,
                "product_name": item.product_name,
                "price": item.price,
                "quantity": item.quantity
            })

    async def _save_status_history(self, status_history: list[OrderStatusChange]) -> None:
        query: TextClause = text("""
                                 INSERT INTO order_status_history(id, order_id, status, changed_at)
                                 VALUES (:id, :order_id, :status, :changed_at)
                                 ON CONFLICT (id) DO NOTHING
                                 """)

        for change in status_history:
            await self.session.execute(query, {
                "id": change.id,
                "order_id": change.order_id,
                "status": change.status.value,
                "changed_at": change.changed_at
            })

    async def _load_items(self, order_id: uuid.UUID) -> list[OrderItem]:
        query: TextClause = text("""
                                 SELECT *
                                 FROM order_items
                                 WHERE order_id = :id
                                 """)
        result = await self.session.execute(query, {
            "id": str(order_id)
        })

        items: list[OrderItem] = []
        for r in result.fetchall():
            items.append(
                OrderItem(
                    id=r.id,
                    order_id=r.order_id,
                    product_name=r.product_name,
                    price=r.price,
                    quantity=r.quantity
                )
            )

        return items

    async def _load_status_history(self, order_id: uuid.UUID) -> list[OrderStatusChange]:
        query: TextClause = text("""
                                 SELECT *
                                 FROM order_status_history
                                 WHERE order_id = :id
                                 """)
        result = await self.session.execute(query, {"id": str(order_id)})

        history: list[OrderStatusChange] = []
        for r in result.fetchall():
            history.append(
                OrderStatusChange(
                    id=r.id,
                    order_id=r.order_id,
                    status=OrderStatus(r.status),
                    changed_at=r.changed_at
                )
            )

        return history

    async def _load_orders_by_ids(self, ids: list[uuid.UUID]) -> list[Order]:
        orders: list[Order] = []
        for oid in ids:
            order = await self.find_by_id(oid)

            if order:
                orders.append(order)
        return orders
