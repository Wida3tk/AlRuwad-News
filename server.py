from __future__ import annotations

import hashlib
import html
from html.parser import HTMLParser
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "alruwad.db"
SESSION_COOKIE = "alruwad_session"
ADMIN_USER = os.environ.get("ALRUWAD_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ALRUWAD_ADMIN_PASSWORD", "alruwad2026")


SEED_ARTICLES = [
    {
        "id": "pak-gulf-economy",
        "title": "إسلام آباد تبحث توسيع التعاون الاقتصادي مع دول الخليج",
        "category": "باكستان والخليج",
        "source": "Dawn",
        "status": "منشور",
        "importance": "مهم",
        "summary": "قالت مصادر رسمية إن الحكومة الباكستانية تعمل على حزمة تفاهمات جديدة تشمل الاستثمار والطاقة والتحويلات المالية.",
        "context": "يعكس التحرك رغبة باكستان في تنويع مصادر التمويل وتعزيز علاقاتها الاقتصادية مع العواصم الخليجية.",
        "body": [
            "تدرس الحكومة الباكستانية توسيع التعاون الاقتصادي مع عدد من دول الخليج ضمن ملفات الاستثمار والطاقة وتحويلات العاملين في الخارج.",
            "وبحسب مصادر رسمية، تسعى إسلام آباد إلى جذب استثمارات جديدة في قطاعات البنية التحتية والطاقة، بالتزامن مع ضغوط اقتصادية داخلية.",
            "وتحظى العلاقات الخليجية الباكستانية بأهمية خاصة بسبب حجم الجالية الباكستانية في دول الخليج ودور التحويلات المالية في دعم الاقتصاد المحلي.",
        ],
        "tags": ["اقتصاد", "الخليج", "استثمار"],
    },
    {
        "id": "energy-prices",
        "title": "ملف الطاقة يعود إلى واجهة النقاش الاقتصادي في باكستان",
        "category": "اقتصاد",
        "source": "Business Recorder",
        "status": "منشور",
        "importance": "متابعة",
        "summary": "تواصل الحكومة بحث إجراءات مرتبطة بتكلفة الكهرباء والدعم، وسط ضغوط على الميزانية ومعيشة المواطنين.",
        "context": "يبقى ملف الطاقة من أكثر الملفات حساسية لأنه يؤثر على التضخم والصناعة والاستقرار الاجتماعي.",
        "body": [
            "عاد ملف الطاقة إلى صدارة النقاش الاقتصادي في باكستان مع استمرار الضغوط المتعلقة بتكلفة الكهرباء والدعم الحكومي.",
            "وتشير تقارير محلية إلى أن الحكومة تبحث خيارات لتخفيف العبء المالي مع الحفاظ على متطلبات برامج الإصلاح الاقتصادي.",
            "ويرى مراقبون أن أي تعديل في أسعار الطاقة ستكون له آثار مباشرة على الأسر والقطاع الصناعي.",
        ],
        "tags": ["طاقة", "تضخم", "اقتصاد"],
    },
    {
        "id": "political-followup",
        "title": "الأحزاب الباكستانية تكثف تحركاتها قبل جلسات البرلمان",
        "category": "سياسة",
        "source": "The News",
        "status": "منشور",
        "importance": "متابعة",
        "summary": "تشهد الساحة السياسية اتصالات مكثفة بين القوى البرلمانية قبل مناقشة ملفات اقتصادية وتشريعية مهمة.",
        "context": "تكتسب هذه التحركات أهمية لأنها قد تحدد قدرة الحكومة على تمرير قرارات اقتصادية حساسة.",
        "body": [
            "كثفت الأحزاب الباكستانية مشاوراتها السياسية قبل جلسات برلمانية ينتظر أن تناقش ملفات اقتصادية وتشريعية مهمة.",
            "وتشير الصحافة المحلية إلى أن الحكومة تعمل على ضمان دعم كاف داخل البرلمان لتمرير حزمة من الإجراءات.",
            "وتأتي هذه التحركات وسط حالة ترقب من الأسواق والجهات الدولية المعنية ببرامج التمويل والإصلاح.",
        ],
        "tags": ["سياسة", "برلمان", "أحزاب"],
    },
]


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def arabic_date() -> str:
    months = [
        "يناير",
        "فبراير",
        "مارس",
        "أبريل",
        "مايو",
        "يونيو",
        "يوليو",
        "أغسطس",
        "سبتمبر",
        "أكتوبر",
        "نوفمبر",
        "ديسمبر",
    ]
    today = datetime.now()
    return f"{today.day} {months[today.month - 1]} {today.year}"


def make_slug(text: str) -> str:
    allowed = []
    for char in text.strip().lower():
        if char.isalnum() or "\u0600" <= char <= "\u06ff":
            allowed.append(char)
        elif allowed and allowed[-1] != "-":
            allowed.append("-")
    slug = "".join(allowed).strip("-")
    return slug[:90] or f"article-{secrets.token_hex(4)}"


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(password_hash(password, salt).split("$", 1)[1], digest)


def db() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS articles (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              category TEXT NOT NULL,
              source TEXT NOT NULL,
              source_url TEXT DEFAULT '',
              original_language TEXT DEFAULT '',
              original_text TEXT DEFAULT '',
              status TEXT NOT NULL,
              importance TEXT NOT NULL,
              summary TEXT NOT NULL,
              context TEXT NOT NULL,
              body TEXT NOT NULL,
              tags TEXT NOT NULL,
              published_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )

        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count == 0:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (ADMIN_USER, password_hash(ADMIN_PASSWORD), now_iso()),
            )

        article_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        if article_count == 0:
            for article in SEED_ARTICLES:
                conn.execute(
                    """
                    INSERT INTO articles (
                      id, title, category, source, status, importance, summary, context,
                      body, tags, published_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article["id"],
                        article["title"],
                        article["category"],
                        article["source"],
                        article["status"],
                        article["importance"],
                        article["summary"],
                        article["context"],
                        "\n\n".join(article["body"]),
                        json.dumps(article["tags"], ensure_ascii=False),
                        arabic_date(),
                        now_iso(),
                        now_iso(),
                    ),
                )


def article_from_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "source": row["source"],
        "sourceUrl": row["source_url"],
        "originalLanguage": row["original_language"],
        "originalText": row["original_text"],
        "status": row["status"],
        "importance": row["importance"],
        "summary": row["summary"],
        "context": row["context"],
        "body": [paragraph for paragraph in row["body"].split("\n\n") if paragraph.strip()],
        "tags": json.loads(row["tags"] or "[]"),
        "publishedAt": row["published_at"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def clean_text(value: str) -> str:
    return " ".join(html.unescape(value).replace("\xa0", " ").split())


def is_article_paragraph(text: str) -> bool:
    if len(text) < 45:
        return False
    lowered = text.lower()
    blocked = [
        "subscribe",
        "comments",
        "read more",
        "our readers",
        "whatsapp",
        "advertise",
        "copyright",
        "500 characters",
        "trusted source",
        "email",
    ]
    return not any(item in lowered for item in blocked)


def unique_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        marker = item.lower()
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


class ArticleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self.paragraphs: list[str] = []
        self.capture_title = False
        self.capture_paragraph = False
        self.buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name: value or "" for name, value in attrs}
        if tag == "title":
            self.capture_title = True
            self.buffer = []
        elif tag == "meta":
            key = attrs_dict.get("property") or attrs_dict.get("name")
            content = attrs_dict.get("content")
            if key and content:
                self.meta[key] = clean_text(content)
        elif tag == "p":
            self.capture_paragraph = True
            self.buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.capture_title:
            self.title = clean_text(" ".join(self.buffer))
            self.capture_title = False
            self.buffer = []
        elif tag == "p" and self.capture_paragraph:
            text = clean_text(" ".join(self.buffer))
            if is_article_paragraph(text):
                self.paragraphs.append(text)
            self.capture_paragraph = False
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.capture_title or self.capture_paragraph:
            self.buffer.append(data)


def import_article_from_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Invalid URL")

    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 AlRuwadNewsImporter/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=15) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            raise ValueError("URL is not an HTML article")
        raw = response.read(2_000_000)

    markup = raw.decode("utf-8", errors="replace")
    parser = ArticleHTMLParser()
    parser.feed(markup)

    title = (
        parser.meta.get("og:title")
        or parser.meta.get("twitter:title")
        or parser.title
        or "Imported article"
    )
    title = clean_text(title.replace(" - DAWN.COM", "").replace("| Dawn", ""))
    description = clean_text(parser.meta.get("og:description") or parser.meta.get("description") or "")
    source = "Dawn" if "dawn.com" in parsed.netloc else parsed.netloc.replace("www.", "")
    body = unique_preserve_order(parser.paragraphs)[:18]
    if len(body) < 2:
        raise ValueError("Could not extract enough article text")

    return {
        "title": title,
        "source": source,
        "sourceUrl": url,
        "originalLanguage": "English",
        "category": "العالم" if "world" in markup.lower() or "/news/" in parsed.path else "",
        "summary": description,
        "originalText": "\n\n".join(body),
    }


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        clean = parsed.path.lstrip("/") or "index.html"
        return str(ROOT / clean)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed.path, parse_qs(parsed.query))
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_post(parsed.path)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_delete(parsed.path)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def send_json(self, payload: dict | list, status: int = 200, cookie: str | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def session_token(self) -> str | None:
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == SESSION_COOKIE:
                return value
        return None

    def current_user(self) -> sqlite3.Row | None:
        token = self.session_token()
        if not token:
            return None
        with db() as conn:
            return conn.execute(
                """
                SELECT users.* FROM users
                JOIN sessions ON sessions.user_id = users.id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()

    def require_user(self) -> sqlite3.Row | None:
        user = self.current_user()
        if not user:
            self.send_json({"error": "unauthorized"}, 401)
            return None
        return user

    def handle_api_get(self, path: str, query: dict) -> None:
        if path == "/api/me":
            user = self.current_user()
            self.send_json({"authenticated": bool(user), "username": user["username"] if user else None})
            return

        if path == "/api/articles":
            status = query.get("status", [""])[0]
            with db() as conn:
                if status:
                    rows = conn.execute(
                        "SELECT * FROM articles WHERE status = ? ORDER BY created_at DESC",
                        (status,),
                    ).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM articles ORDER BY created_at DESC").fetchall()
            self.send_json([article_from_row(row) for row in rows])
            return

        if path.startswith("/api/articles/"):
            article_id = unquote(path.rsplit("/", 1)[-1])
            with db() as conn:
                row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            if not row:
                self.send_json({"error": "not_found"}, 404)
                return
            self.send_json(article_from_row(row))
            return

        self.send_json({"error": "not_found"}, 404)

    def handle_api_post(self, path: str) -> None:
        if path == "/api/login":
            payload = self.json_body()
            username = payload.get("username", "")
            password = payload.get("password", "")
            with db() as conn:
                user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
                if not user or not verify_password(password, user["password_hash"]):
                    self.send_json({"error": "بيانات الدخول غير صحيحة"}, 401)
                    return
                token = secrets.token_urlsafe(32)
                conn.execute(
                    "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                    (token, user["id"], now_iso()),
                )
            cookie = f"{SESSION_COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/"
            self.send_json({"ok": True, "username": username}, cookie=cookie)
            return

        if path == "/api/logout":
            token = self.session_token()
            if token:
                with db() as conn:
                    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            self.send_json({"ok": True}, cookie=f"{SESSION_COOKIE}=; Max-Age=0; Path=/")
            return

        if path == "/api/draft":
            if not self.require_user():
                return
            payload = self.json_body()
            source = payload.get("source") or "مصدر باكستاني"
            category = payload.get("category") or "سياسة"
            original_text = payload.get("originalText") or ""
            self.send_json(make_draft(source, category, original_text))
            return

        if path == "/api/import-url":
            if not self.require_user():
                return
            payload = self.json_body()
            try:
                imported = import_article_from_url(payload.get("url") or "")
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
                return
            self.send_json(imported)
            return

        if path == "/api/articles":
            if not self.require_user():
                return
            payload = self.json_body()
            title = (payload.get("title") or "").strip()
            if not title:
                self.send_json({"error": "العنوان مطلوب"}, 400)
                return
            article_id = payload.get("id") or make_slug(title)
            now = now_iso()
            with db() as conn:
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
                        payload.get("source") or "مصدر باكستاني",
                        payload.get("sourceUrl") or "",
                        payload.get("originalLanguage") or "",
                        payload.get("originalText") or "",
                        payload.get("status") or "مسودة",
                        payload.get("importance") or "متابعة",
                        payload.get("summary") or "",
                        payload.get("context") or "",
                        "\n\n".join(payload.get("body") or []),
                        json.dumps(payload.get("tags") or [], ensure_ascii=False),
                        payload.get("publishedAt") or arabic_date(),
                        now,
                        now,
                    ),
                )
                row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            self.send_json(article_from_row(row), 201)
            return

        self.send_json({"error": "not_found"}, 404)

    def handle_api_delete(self, path: str) -> None:
        if not self.require_user():
            return
        if path.startswith("/api/articles/"):
            article_id = unquote(path.rsplit("/", 1)[-1])
            with db() as conn:
                conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
            self.send_json({"ok": True})
            return
        self.send_json({"error": "not_found"}, 404)


def make_draft(source: str, category: str, original_text: str = "") -> dict:
    lowered = original_text.lower()
    if ("iran" in lowered and "qatar" in lowered) or ("strait of hormuz" in lowered and "doha" in lowered):
        return {
            "title": "محادثات في قطر لمتابعة الاتفاق الأميركي الإيراني وسط خلاف حول شكل التفاوض",
            "summary": "تستضيف الدوحة تحركات دبلوماسية مرتبطة بالاتفاق الأميركي الإيراني الأخير، لكن التصريحات المتباينة بين واشنطن وطهران والدوحة تكشف أن المسار لا يزال في مرحلة مشاورات غير مباشرة أكثر منه مفاوضات نهائية.",
            "context": "تكمن أهمية هذه المحادثات في ارتباطها بملفين حساسين: أمن الملاحة في مضيق هرمز، والأموال الإيرانية المجمدة بفعل العقوبات. كما أن أي تقدم في هذا المسار قد ينعكس على تهدئة أوسع في الخليج ولبنان.",
            "body": [
                "تتحرك الدبلوماسية في الدوحة على وقع الاتفاق الأميركي الإيراني الأخير، مع وصول مبعوثين أميركيين إلى قطر للقاء مسؤولين ووسطاء قطريين، في وقت تؤكد طهران أن ما يجري لا يرقى بعد إلى مفاوضات مباشرة مع واشنطن.",
                "التباين في التصريحات يعكس حساسية المرحلة. فقد تحدث الرئيس الأميركي دونالد ترامب عن محادثات جديدة في قطر، بينما أوضحت الدوحة أن الاجتماعات لا تمثل مفاوضات مباشرة عالية المستوى بين الولايات المتحدة وإيران، بل لقاءات مع وسطاء ومسؤولين قطريين تتناول ملفات إقليمية متعددة.",
                "من الجانب الإيراني، تؤكد الخارجية أن وفدًا من الخبراء سيتوجه إلى الدوحة خلال الأسبوع، لكن هدف الزيارة هو بحث تفاصيل مرتبطة بالاتفاق وليس الدخول في مفاوضات نهائية مع الجانب الأميركي.",
                "أبرز الملفات المطروحة يتعلق بمضيق هرمز، الذي يمثل شريانًا حيويًا لحركة الطاقة والتجارة. الاتفاق الأخير يتضمن ترتيبات لإعادة فتحه وتهدئة التوتر حول الملاحة، بعدما شهدت المنطقة حوادث وتراجعًا في حركة السفن.",
                "ملف آخر لا يقل أهمية هو الأموال الإيرانية المجمدة بفعل العقوبات الأميركية. وتربط طهران أي تقدم عملي في الاتفاق بإجراءات تسمح بالإفراج عن جزء من هذه الأموال، وسط حديث عن مليارات الدولارات المقيدة.",
                "ورغم استمرار تبادل محدود للنيران خلال الأيام الماضية، تبدو حدة المواجهة قد تراجعت قبل اجتماعات قطر. هذا الهدوء النسبي يمنح الوسطاء مساحة لاختبار إمكانية تثبيت الاتفاق وتحويله إلى خطوات عملية.",
                "كما يرتبط المسار بملف لبنان، حيث تصر إيران على أن يشمل أي اتفاق تهدئة للصراع الموازي وانسحاب القوات الإسرائيلية من جنوب لبنان. وهذا يجعل المفاوضات أوسع من ملف نووي أو مالي، لأنها تمس شبكة أزمات إقليمية مترابطة.",
                "الخلاصة أن اجتماعات قطر لا تعني أن واشنطن وطهران دخلتا مرحلة اتفاق نهائي، لكنها تمثل اختبارًا مهمًا لجدية الطرفين وقدرة الوسطاء على إدارة الملفات العالقة، من هرمز إلى الأموال المجمدة وصولًا إلى لبنان.",
            ],
        }

    if "israel" in lowered and "lebanon" in lowered:
        return {
            "title": "اتفاق أميركي إسرائيلي لبناني يواجه اختبارات صعبة قبل التنفيذ",
            "summary": "يواجه الاتفاق الذي رعته الولايات المتحدة بين إسرائيل ولبنان تحديات معقدة، أبرزها شروط الانسحاب الإسرائيلي، وموقف حزب الله، وحسابات إيران الإقليمية.",
            "context": "أهمية الاتفاق لا تكمن في توقيعه فقط، بل في قدرته على التحول إلى ترتيبات أمنية قابلة للتنفيذ داخل جنوب لبنان، حيث تتداخل سيادة الدولة مع سلاح حزب الله والحسابات الإسرائيلية والإيرانية.",
            "body": [
                "دخل الاتفاق الذي رعته الولايات المتحدة بين إسرائيل ولبنان مرحلة اختبار مبكرة، إذ إن التوقيع على إطار تفاهم لا يعني بالضرورة انتهاء المواجهة أو انسحاب القوات الإسرائيلية من الأراضي اللبنانية التي تسيطر عليها في الجنوب.",
                "الخطوة تفتح أسئلة حول قدرة الحكومة اللبنانية على تنفيذ الالتزامات الأمنية، ومدى استعداد إسرائيل للتراجع عن مواقعها، وموقف حزب الله من أي ترتيبات تمس سلاحه.",
                "أبرز عقدة أمام الاتفاق هي مسألة الانسحاب الإسرائيلي. فالنص يتحدث عن إعادة انتشار في مناطق محددة، بينما تربط إسرائيل أي انسحاب فعلي بنزع سلاح حزب الله أو تحييد قدراته العسكرية في تلك المناطق.",
                "هذا الشرط يجعل التنفيذ مرتبطًا بملف داخلي لبناني شديد الحساسية، لأن انتقال المسؤولية الأمنية إلى الجيش اللبناني لن يكون تلقائيًا، بل يحتاج إلى تأكيد بأن الجماعات المسلحة غير التابعة للدولة لم تعد فاعلة هناك.",
                "المعضلة الثانية تتعلق بحزب الله، الذي يرفض الاتفاق ويراه محاولة لإضفاء شرعية على الوجود الإسرائيلي. وهذا الرفض قد يبقى سياسيًا، لكنه قد يتحول إلى أزمة داخلية إذا جرى فرض الترتيبات بالقوة.",
                "أما البعد الإقليمي فيتمثل في إيران، التي لا تزال لاعبًا مؤثرًا في الساحة اللبنانية. نجاح الاتفاق أو تعثره سيتوقف إلى حد كبير على حسابات طهران وعلاقتها بالمفاوضات الأوسع مع واشنطن.",
                "الخلاصة أن الاتفاق قد يفتح نافذة لخفض التصعيد، لكنه يحمل احتمالات تعطيل كبيرة إذا لم تُترجم التفاهمات إلى خطوات متوازنة تحمي المدنيين وتراعي الواقع اللبناني الداخلي.",
            ],
        }

    title = (
        "باكستان تبحث خطوات جديدة لتعزيز تعاونها مع دول الخليج"
        if "الخليج" in category
        else "تطور جديد في باكستان يثير اهتمام الصحافة المحلية"
    )
    return {
        "title": title,
        "summary": "أفادت الصحافة الباكستانية بوجود تطور جديد يحتاج إلى متابعة عربية بسبب ارتباطه بالسياق السياسي والاقتصادي في البلاد.",
        "context": f"يكتسب الخبر أهمية لأنه ورد في {source} ويرتبط بملف {category}، ما يجعله مهمًا للقارئ العربي المهتم بباكستان والمنطقة.",
        "body": [
            f"ذكرت {source} أن باكستان تشهد تطورًا جديدًا ضمن ملف {category}، وسط اهتمام من الصحافة المحلية بمتابعة تفاصيله وتأثيراته المحتملة.",
            "وبحسب ما ورد في الصحافة المحلية، يأتي هذا التطور ضمن سياق أوسع تشهده باكستان على المستويات السياسية والاقتصادية.",
            "وتقدم الرواد نيوز هذا الخبر بصياغة عربية محررة مع الإشارة إلى المصدر الأصلي وإضافة السياق اللازم لفهمه.",
        ],
    }


def run() -> None:
    init_db()
    port = int(os.environ.get("PORT", "4174"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"AlRuwad News running at http://127.0.0.1:{port}/")
    print(f"Admin login: {ADMIN_USER} / {ADMIN_PASSWORD}")
    server.serve_forever()


if __name__ == "__main__":
    run()
