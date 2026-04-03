from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class BlogIndex(Base):
    __tablename__ = "blog_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String(256), nullable=False, unique=True)
    updated = Column(DateTime, nullable=False)
    tags = Column(String(4000), nullable=True)

    def __repr__(self):
        return f"<BlogIndex(id={self.id}, path='{self.path}', updated={self.updated})>"
