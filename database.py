import os

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, BigInteger
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Status(Base):
    __tablename__ = "status"
    status_id = Column(Integer, primary_key=True)
    status_name = Column(String, nullable=False)
    users = relationship("User", back_populates="status")


class User(Base):
    __tablename__ = "user"
    user_id = Column(BigInteger, primary_key=True, autoincrement=False)
    fio = Column(String, nullable=True)
    status_id = Column(Integer, ForeignKey("status.status_id"))

    status = relationship("Status", back_populates="users", uselist=False)
    cars = relationship("Cars", back_populates="user")


class Cars(Base):
    __tablename__ = "cars"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("user.user_id"), nullable=False)
    car_number = Column(String, nullable=False)
    brand = Column(String)
    user = relationship("User", back_populates="cars", uselist=False)


def create_db_connection():
    USER_DB = os.getenv('USER_DB')
    PASSWORD_DB = os.getenv('PASSWORD_DB')
    HOST_DB = os.getenv('HOST_DB')
    PORT_DB = 5432
    NAME_DB = os.getenv('NAME_DB')
    conn = f"postgresql://{USER_DB}:{PASSWORD_DB}@{HOST_DB}:{PORT_DB}/{NAME_DB}"
    engine = create_engine(conn)
    Session = sessionmaker(bind=engine)
    return Session
