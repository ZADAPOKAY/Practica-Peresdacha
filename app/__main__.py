import argparse
import sys
from getpass import getpass

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from .config import ConfigError, load_config
from .db import User, get_session, init_db, query_logs
from .parser import parse_logs


def main():
    p = argparse.ArgumentParser(prog="python -m app", description="Агрегатор access-логов Apache")
    p.add_argument("--config", help="путь к config.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("parse", help="разобрать логи и сохранить в БД")
    u = sub.add_parser("create-user", help="создать пользователя")
    u.add_argument("username")
    sh = sub.add_parser("show", help="показать данные из БД")
    sh.add_argument("--from", dest="date_from", help="начало, напр. 2026-05-10")
    sh.add_argument("--to", dest="date_to", help="конец, напр. 2026-05-12")
    sh.add_argument("--ip")
    sh.add_argument("--keyword", help="часть URL")
    sh.add_argument("--group-by", choices=["ip", "date"])
    sh.add_argument("--limit", type=int, default=50)
    sub.add_parser("runserver", help="запустить веб-интерфейс и API")
    args = p.parse_args()

    try:
        cfg = load_config(args.config)
        init_db(cfg)

        if args.cmd == "parse":
            st = parse_logs(cfg)
            print(f"Файлов: {st['files']}, строк: {st['lines']}, "
                  f"добавлено: {st['inserted']}, битых: {st['bad']}")
            for e in st["errors"]:
                print("ОШИБКА:", e)
            if st["bad"]:
                print(f"Нераспознанные строки записаны в {cfg['errors_log']}")

        elif args.cmd == "create-user":
            pw = getpass("Пароль: ")
            if len(pw) < 4:
                sys.exit("Пароль слишком короткий (минимум 4 символа)")
            if pw != getpass("Повторите пароль: "):
                sys.exit("Пароли не совпадают")
            s = get_session()
            try:
                if s.query(User).filter_by(username=args.username).first():
                    sys.exit("Такой пользователь уже существует")
                s.add(User(username=args.username, password_hash=generate_password_hash(pw)))
                s.commit()
                print("Пользователь создан")
            finally:
                s.close()

        elif args.cmd == "show":
            s = get_session()
            try:
                rows = query_logs(s, args.date_from, args.date_to, args.ip, args.keyword,
                                  args.group_by, args.limit)
            finally:
                s.close()
            if not rows:
                print("Ничего не найдено")
            elif args.group_by:
                print(f"{args.group_by.upper():<20}{'ЗАПРОСОВ':>10}{'БАЙТ':>12}")
                for r in rows:
                    print(f"{r['key']:<20}{r['requests']:>10}{r['bytes']:>12}")
            else:
                for r in rows:
                    print(f"{r['time']}  {r['ip']:<15} {r['status']}  {r['method']:<6} {r['url']}")

        elif args.cmd == "runserver":
            from .web import create_app
            create_app(cfg).run(host=cfg["web"]["host"], port=cfg["web"]["port"])

    except ConfigError as e:
        sys.exit(f"Ошибка настроек: {e}")
    except ValueError as e:
        sys.exit(f"Ошибка: {e}")
    except SQLAlchemyError:
        sys.exit("Ошибка базы данных. Проверьте, что MySQL запущена и данные в config.yaml верны.")
    except KeyboardInterrupt:
        sys.exit(1)


main()
