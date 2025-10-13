from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"), nullable=True)
    delivery_info: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    
    # Поля для оффлайн доставки
    delivery_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_fullname: Mapped[str | None] = mapped_column(String(200), nullable=True)
    delivery_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
