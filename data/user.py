import sqlalchemy
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    surname = sqlalchemy.Column(sqlalchemy.String)
    birthday = sqlalchemy.Column(sqlalchemy.String)
    is_birthday = sqlalchemy.Column(sqlalchemy.Boolean)
    is_admin = sqlalchemy.Column(sqlalchemy.Boolean)
    is_banned = sqlalchemy.Column(sqlalchemy.Boolean)
