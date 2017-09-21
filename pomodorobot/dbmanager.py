from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from discord.user import User

import pomodorobot.lib as lib

DB_DEBUG = False

engine = create_engine('sqlite:///test.db', echo=DB_DEBUG, encoding='utf-8')
SqlBase = declarative_base()


class TimerUser(SqlBase):
    __tablename__ = 'timer_users'

    # The database ID
    id = Column(Integer, primary_key=True)
    # The discord ID
    discord_id = Column(String, index=True, unique=True)
    # The discord name (not nick), stored for easier access/chaining
    name = Column(String, index=True, unique=True)

    # Last recorded timer use
    last_seen = Column(DateTime, nullable=True)
    # Time spent using the timer in the last session, in seconds.
    last_session = Column(Integer, nullable=True)
    # Total time spent using the timer, in seconds.
    total_recorded = Column(Integer, nullable=True)

    def __repr__(self):
        return ("pomodorobot.dbmanager.TimerUser: [{}]\n<{}/{}>\n"
                "\t{}\n\tLast:{}; Total:{}")\
            .format(self.id, self.discord_id, self.name,
                    self.last_seen, self.last_session, self.total_recorded)

SqlBase.metadata.create_all(engine)
SqlSession = sessionmaker(bind=engine)


class SqlManager:
    """ Represents a SQL Manager
    """

    def __init__(self):
        self._sql_session = SqlSession()

    def get_record(self, user: User):
        record = self._sql_session.query(TimerUser)\
            .filter_by(discord_id=user.id).first()
        if record is None:
            lib.log("DB queried for non-existent user {},"
                    " registry will be created.".format(str(user)))
            record = TimerUser(discord_id=user.id, name=str(user))
            self._sql_session.add(record)
            self._sql_session.commit()

        return record

    def get_record_by_name(self, name: str):
        return self._sql_session.query(TimerUser).filter_by(name=name).first()

    def get_all_records(self):
        return self._sql_session.query(TimerUser)

    def get_leaderboard(self):
        return self.get_all_records().order_by(TimerUser.total_recorded).all()

    def get_user_attendance(self, user):
        record = self.get_record_by_name(user) if isinstance(user, str) \
            else self.get_record(user)

        return record.last_seen if record is not None else None

    def get_user_last_session(self, user: User):
        record = self.get_record_by_name(user) if isinstance(user, str) \
            else self.get_record(user)
        return record.last_session if record is not None else None

    def get_user_total(self, user: User):
        return self.get_record(user).total_recorded

    def set_user_attendance(self, user: User, attendance: datetime):
        record = self.get_record(user)
        record.last_seen = attendance

        self._sql_session.add(record)
        self._sql_session.commit()

    def set_user_last_session(self, user: User, session: int):
        record = self.get_record(user)
        record.last_session = session
        if record.total_recorded is not None:
            record.total_recorded += session
        else:
            record.total_recorded = session

        self._sql_session.add(record)
        self._sql_session.commit()

    def set_user_total(self, user: User, total: int):
        record = self.get_record(user)
        record.last_session = total

        self._sql_session.add(record)
        self._sql_session.commit()


db_manager = SqlManager()
