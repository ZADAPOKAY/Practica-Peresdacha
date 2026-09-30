from datetime import datetime, timedelta
from sqlalchemy import (create_engine, Column, Integer, BigInteger, String, Text,
                        DateTime, func, select)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_Session = None


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)


class LogEntry(Base):
    __tablename__ = "log_entries"
    id = Column(BigInteger, primary_key=True)
    ip = Column(String(45), index=True, nullable=False)
    user = Column(String(128))
    time = Column(DateTime, index=True, nullable=False)  # UTC
    method = Column(String(16))
    url = Column(Text)
    protocol = Column(String(16))
    status = Column(Integer)
    size = Column(BigInteger, default=0)
    referer = Column(Text)
    user_agent = Column(Text)
    line_hash = Column(String(40), unique=True, nullable=False)  # защита от дублей


def init_db(cfg):
    """Создаёт подключение и таблицы."""
    global _Session
    d = cfg["database"]
    url = (f"mysql+pymysql://{d['user']}:{d['password']}@{d['host']}:{d['port']}"
           f"/{d['name']}?charset=utf8mb4")
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    _Session = sessionmaker(bind=engine)


def get_session():
    return _Session()


def parse_bound(value, end=False):
    """'2026-05-10' или '2026-05-10 13:00[:00]' -> datetime. Для конца дня берём следующий день."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(value, fmt)
            if end and fmt == "%Y-%m-%d":
                dt += timedelta(days=1)
            return dt
        except ValueError:
            pass
    raise ValueError(f"Неверная дата '{value}'. Формат: ГГГГ-ММ-ДД или ГГГГ-ММ-ДД ЧЧ:ММ")


def query_logs(session, date_from=None, date_to=None, ip=None, keyword=None,
               group_by=None, limit=100, offset=0):
    if group_by not in (None, "", "ip", "date"):
        raise ValueError("group_by может быть только 'ip' или 'date'")
    start, end = parse_bound(date_from), parse_bound(date_to, end=True)
    if start and end and start >= end:
        raise ValueError("Начало промежутка должно быть раньше конца")
    limit = max(1, min(int(limit), 1000))
    offset = max(0, int(offset))

    conds = []
    if start: conds.append(LogEntry.time >= start)
    if end: conds.append(LogEntry.time < end)
    if ip: conds.append(LogEntry.ip == ip)
    if keyword: conds.append(LogEntry.url.like(f"%{keyword}%"))

    if group_by in ("ip", "date"):
        key = LogEntry.ip if group_by == "ip" else func.date(LogEntry.time)
        q = (select(key.label("key"), func.count().label("requests"),
                    func.coalesce(func.sum(LogEntry.size), 0).label("bytes"))
             .where(*conds).group_by(key).order_by(func.count().desc())
             .limit(limit).offset(offset))
        return [{"key": str(r.key), "requests": int(r.requests), "bytes": int(r.bytes)}
                for r in session.execute(q)]

    q = (select(LogEntry).where(*conds).order_by(LogEntry.time.desc())
         .limit(limit).offset(offset))
    return [{"id": e.id, "ip": e.ip, "user": e.user, "time": e.time.isoformat(sep=" "),
             "method": e.method, "url": e.url, "protocol": e.protocol, "status": e.status,
             "size": e.size, "referer": e.referer, "user_agent": e.user_agent}
            for e in session.scalars(q)]
