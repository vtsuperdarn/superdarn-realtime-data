from sqlalchemy.orm import Mapped, mapped_column
from app import db
from datetime import datetime

class EchoCounts(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    site_name: Mapped[str] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(
        db.DateTime, server_default=db.func.now(), nullable=False
    )
    total_echoes: Mapped[int] = mapped_column()
    ionospheric_echoes: Mapped[int] = mapped_column()
    ground_scatter_echoes: Mapped[int] = mapped_column()

    def to_dict(self):
        return {
            c.name: (
                getattr(self, c.name).isoformat() if c.name == "timestamp" and getattr(self, c.name) else getattr(self, c.name) # Format timestamp as ISO string
            )
            for c in self.__table__.columns
        }