class Transfer:
    """Represents a row from the transfers table."""

    __slots__ = (
        "id", "user_id", "from_account_id", "to_account_id",
        "amount", "notes", "transfer_date", "created_at",
    )

    def __init__(self, row: tuple):
        (
            self.id, self.user_id, self.from_account_id, self.to_account_id,
            self.amount, self.notes, self.transfer_date, self.created_at,
        ) = row

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "from_account_id": self.from_account_id,
            "to_account_id": self.to_account_id,
            "amount": float(self.amount),
            "notes": self.notes,
            "transfer_date": str(self.transfer_date),
            "created_at": str(self.created_at),
        }