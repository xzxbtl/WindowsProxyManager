from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from proxy.database.config import Base


class Proxy(Base):
    __tablename__ = 'proxy'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)

    type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    host: Mapped[str] = mapped_column(String, nullable=False, index=True)
    port: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    user: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    password: Mapped[str | None] = mapped_column(String, nullable=True)

    proxy_to_str: Mapped[str] = mapped_column(String, nullable=False, index=True)
    public: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True, default=False)


    def __repr__(self) -> str:
        return f"<Proxy {self.host}:{self.port} user={self.user}>"
