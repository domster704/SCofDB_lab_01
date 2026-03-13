"""Доменная сущность пользователя."""
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC

from .exceptions import InvalidEmailError

# TODO: Реализовать класс User
# - Использовать @dataclass
# - Поля: email, name, id, created_at
# - Реализовать валидацию email в __post_init__
# - Regex: r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

EMAIL_REGEXP = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


@dataclass
class User:
    email: str
    name: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not isinstance(self.email, str) or not self.email.strip():
            raise InvalidEmailError("Почта должна быть непустой строкой")

        if not re.match(EMAIL_REGEXP, self.email):
            raise InvalidEmailError(f"Неправильный формат: {self.email}")
