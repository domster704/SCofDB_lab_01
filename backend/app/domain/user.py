"""Доменная сущность пользователя."""
import re
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
    id: str
    name: str
    email: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self):
        if not isinstance(self.email, str) or not self.email.strip():
            raise InvalidEmailError("Почта должна быть непустой строкой")

        if not re.match(EMAIL_REGEXP, self.email):
            raise InvalidEmailError(f"Неправильный формат: {self.email}")
