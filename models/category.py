class Category:
    """Represents a row from the categories table."""

    __slots__ = ("id", "user_id", "name", "icon", "color", "created_at")

    def __init__(self, row: tuple):
        self.id, self.user_id, self.name, self.icon, self.color, self.created_at = row

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "created_at": str(self.created_at),
        }


class Subcategory:
    """Represents a row from the subcategories table."""

    __slots__ = ("id", "category_id", "name", "created_at")

    def __init__(self, row: tuple):
        self.id, self.category_id, self.name, self.created_at = row

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category_id": self.category_id,
            "name": self.name,
            "created_at": str(self.created_at),
        }