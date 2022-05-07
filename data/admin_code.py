import sqlalchemy
from .db_session import SqlAlchemyBase


class AdminCode(SqlAlchemyBase):
    __tablename__ = 'admin_codes'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    code = sqlalchemy.Column(sqlalchemy.String)
    is_used = sqlalchemy.Column(sqlalchemy.Boolean)
