import sqlalchemy
from .db_session import SqlAlchemyBase


class RedemptionCode(SqlAlchemyBase):
    __tablename__ = 'redemption_codes'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    code = sqlalchemy.Column(sqlalchemy.String)
    end_date = sqlalchemy.Column(sqlalchemy.String)
