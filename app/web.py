from functools import wraps

from flask import (Flask, jsonify, redirect, render_template, request, session, url_for)
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash

from .db import User, get_session, query_logs
from .parser import parse_logs


def create_app(cfg):
    app = Flask(__name__)
    app.secret_key = cfg["web"]["secret_key"]

    def login_required(view):
        @wraps(view)
        def wrapper(*a, **kw):
            if "user" not in session:
                if request.path.startswith("/api/"):
                    return jsonify(error="Требуется авторизация"), 401
                return redirect(url_for("login"))
            return view(*a, **kw)
        return wrapper

    @app.errorhandler(SQLAlchemyError)
    def db_error(e):
        return jsonify(error="Ошибка базы данных. Проверьте, что MySQL запущена."), 500

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Не найдено"), 404

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            s = get_session()
            try:
                u = s.query(User).filter_by(username=request.form.get("username", "")).first()
                if u and check_password_hash(u.password_hash, request.form.get("password", "")):
                    session["user"] = u.username
                    return redirect(url_for("index"))
                error = "Неверный логин или пароль"
            except SQLAlchemyError:
                error = "Ошибка базы данных"
            finally:
                s.close()
        return render_template("login.html", error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def index():
        return render_template("index.html", user=session["user"])

    @app.route("/api/logs")
    @login_required
    def api_logs():
        a = request.args
        s = get_session()
        try:
            data = query_logs(s, a.get("from"), a.get("to"), a.get("ip"), a.get("keyword"),
                              a.get("group_by"), a.get("limit", 100), a.get("offset", 0))
        except ValueError as e:
            return jsonify(error=str(e)), 400
        finally:
            s.close()
        return jsonify(count=len(data), items=data)

    @app.route("/api/parse", methods=["POST"])
    @login_required
    def api_parse():
        return jsonify(parse_logs(cfg))

    return app
