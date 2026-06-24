class Transaction:
    """Represents a row from the expenses table (multi-account)."""

    __slots__ = (
        "id", "user_id", "account_id", "category_id", "subcategory_id",
        "type", "amount", "pay_method", "note",
        "exp_date", "created_at",
    )

    def __init__(self, row: tuple):
        (
            self.id, self.user_id, self.account_id,
            self.category_id, self.subcategory_id,
            self.type, self.amount, self.pay_method,
            self.note, self.exp_date, self.created_at,
        ) = row

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "category_id": self.category_id,
            "subcategory_id": self.subcategory_id,
            "type": self.type,
            "amount": float(self.amount),
            "pay_method": self.pay_method,
            "note": self.note,
            "exp_date": str(self.exp_date),
            "created_at": str(self.created_at),
        }