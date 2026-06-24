class Account:
    """Lightweight model representing a row from the accounts table."""

    __slots__ = (
        "id", "user_id", "name", "type",
        "initial_balance", "current_balance",
        "icon", "color", "created_at", "updated_at",
    )

    def __init__(self, row: tuple):
        (
            self.id, self.user_id, self.name, self.type,
            self.initial_balance, self.current_balance,
            self.icon, self.color, self.created_at, self.updated_at,
        ) = row

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "type": self.type,
            "initial_balance": float(self.initial_balance),
            "current_balance": float(self.current_balance),
            "icon": self.icon,
            "color": self.color,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
        }