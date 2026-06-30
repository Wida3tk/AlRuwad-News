from __future__ import annotations

import json
import mimetypes
import secrets
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, unquote

import server


ROOT = Path(__file__).resolve().parent


def json_response(start_response, payload, status=200, extra_headers=None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    phrase = HTTPStatus(status).phrase if status in HTTPStatus._value2member_map_ else "OK"
    start_response(f"{status} {phrase}", headers)
    return [body]


def static_response(start_response, path):
    clean = path.lstrip("/") or "index.html"
    file_path = (ROOT / clean).resolve()
    if not str(file_path).startswith(str(ROOT)) or not file_path.is_file():
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Not found"]

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body = file_path.read_bytes()
    start_response(
        "200 OK",
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def read_json(environ):
    try:
      length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError:
      length = 0
    if not length:
        return {}
    raw = environ["wsgi.input"].read(length).decode("utf-8")
    return json.loads(raw or "{}")


def cookie_value(environ, name):
    cookie = environ.get("HTTP_COOKIE", "")
    for part in cookie.split(";"):
        key, _, value = part.strip().partition("=")
        if key == name:
            return value
    return None


def current_user(environ):
    token = cookie_value(environ, server.SESSION_COOKIE)
    if not token:
        return None
    with server.db() as conn:
        return conn.execute(
            """
            SELECT users.* FROM users
            JOIN sessions ON sessions.user_id = users.id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()


def require_user(environ, start_response):
    user = current_user(environ)
    if not user:
        return None, json_response(start_response, {"error": "unauthorized"}, 401)
    return user, None


def article_rows(status=""):
    with server.db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM articles WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM articles ORDER BY created_at DESC").fetchall()
    return [server.article_from_row(row) for row in rows]


def save_article(payload):
    title = (payload.get("title") or "").strip()
    if not title:
        raise ValueError("العنوان مطلوب")

    article_id = payload.get("id") or server.make_slug(title)
    now = server.now_iso()
    with server.db() as conn:
        conn.execute(
            """
            INSERT INTO articles (
              id, title, category, source, source_url, original_language, original_text,
              status, importance, summary, context, body, tags, published_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              title=excluded.title,
              category=excluded.category,
              source=excluded.source,
              source_url=excluded.source_url,
              original_language=excluded.original_language,
              original_text=excluded.original_text,
              status=excluded.status,
              importance=excluded.importance,
              summary=excluded.summary,
              context=excluded.context,
              body=excluded.body,
              tags=excluded.tags,
              published_at=excluded.published_at,
              updated_at=excluded.updated_at
            """,
            (
                article_id,
                title,
                payload.get("category") or "سياسة",
                payload.get("source") or "مصدر",
                payload.get("sourceUrl") or "",
                payload.get("originalLanguage") or "",
                payload.get("originalText") or "",
                payload.get("status") or "مسودة",
                payload.get("importance") or "متابعة",
                payload.get("summary") or "",
                payload.get("context") or "",
                "\n\n".join(payload.get("body") or []),
                json.dumps(payload.get("tags") or [], ensure_ascii=False),
                payload.get("publishedAt") or server.arabic_date(),
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    return server.article_from_row(row)


def application(environ, start_response):
    server.init_db()
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")
    query = parse_qs(environ.get("QUERY_STRING", ""))

    if not path.startswith("/api/"):
        return static_response(start_response, path)

    try:
        if method == "GET" and path == "/api/me":
            user = current_user(environ)
            return json_response(start_response, {"authenticated": bool(user), "username": user["username"] if user else None})

        if method == "GET" and path == "/api/articles":
            return json_response(start_response, article_rows(query.get("status", [""])[0]))

        if method == "GET" and path.startswith("/api/articles/"):
            article_id = unquote(path.rsplit("/", 1)[-1])
            with server.db() as conn:
                row = server.find_article_by_id(conn, article_id)
            if not row:
                return json_response(start_response, {"error": "not_found"}, 404)
            return json_response(start_response, server.article_from_row(row))

        if method == "POST" and path == "/api/login":
            payload = read_json(environ)
            username = payload.get("username", "")
            password = payload.get("password", "")
            with server.db() as conn:
                user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
                if not user or not server.verify_password(password, user["password_hash"]):
                    return json_response(start_response, {"error": "بيانات الدخول غير صحيحة"}, 401)
                token = secrets.token_urlsafe(32)
                conn.execute(
                    "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                    (token, user["id"], server.now_iso()),
                )
            return json_response(
                start_response,
                {"ok": True, "username": username},
                extra_headers=[("Set-Cookie", f"{server.SESSION_COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/")],
            )

        if method == "POST" and path == "/api/logout":
            token = cookie_value(environ, server.SESSION_COOKIE)
            if token:
                with server.db() as conn:
                    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return json_response(start_response, {"ok": True}, extra_headers=[("Set-Cookie", f"{server.SESSION_COOKIE}=; Max-Age=0; Path=/")])

        if method == "POST" and path == "/api/import-url":
            _, denied = require_user(environ, start_response)
            if denied:
                return denied
            payload = read_json(environ)
            return json_response(start_response, server.import_article_from_url(payload.get("url") or ""))

        if method == "POST" and path == "/api/draft":
            _, denied = require_user(environ, start_response)
            if denied:
                return denied
            payload = read_json(environ)
            return json_response(
                start_response,
                server.make_draft(payload.get("source") or "مصدر", payload.get("category") or "سياسة", payload.get("originalText") or ""),
            )

        if method == "POST" and path == "/api/articles":
            _, denied = require_user(environ, start_response)
            if denied:
                return denied
            return json_response(start_response, save_article(read_json(environ)), 201)

        if method == "DELETE" and path.startswith("/api/articles/"):
            _, denied = require_user(environ, start_response)
            if denied:
                return denied
            article_id = unquote(path.rsplit("/", 1)[-1])
            with server.db() as conn:
                conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
            return json_response(start_response, {"ok": True})

        return json_response(start_response, {"error": "not_found"}, 404)
    except Exception as exc:
        return json_response(start_response, {"error": str(exc)}, 500)
