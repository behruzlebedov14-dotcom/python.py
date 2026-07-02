import asyncio
import logging
import math
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineQuery,
    InlineQueryResultArticle, InputTextMessageContent,
    KeyboardButton, InlineKeyboardButton, FSInputFile
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import json
import os

# ══════════════════════════════════════════
#               SOZLAMALAR
# ══════════════════════════════════════════
BOT_TOKEN        = '8688115939:AAH0k_8l530CvZ9AT2IO-Ve3b3NH2XgkrF0'
ADMIN_IDS        = 7136222412
import logging
import math
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineQuery,
    InlineQueryResultArticle, InputTextMessageContent,
    KeyboardButton, InlineKeyboardButton, FSInputFile
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import json
import os

# ══════════════════════════════════════════
#               SOZLAMALAR
# ══════════════════════════════════════════
BOT_TOKEN        = '8688115939:AAH0k_8l530CvZ9AT2IO-Ve3b3NH2XgkrF0'
ADMIN_IDS        = [7136222412]  # ✅ Tuzatildi - list with one admin ID
CHANNEL_USERNAME = None    # "@kanalim" yoki None
DB_FILE          = "movies.db"
BOT_NAME         = "🎬 KinoBot"
PER_PAGE         = 6
BACKUP_DIR       = "backups"

# ══════════════════════════════════════════
#                LOGGING
# ══════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════
#              DATABASE
# ══════════════════════════════════════════
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()

    # Eski jadvallarni o'chirish (agar mavjud bo'lsa)
    conn.executescript("""
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS movies;
        DROP TABLE IF EXISTS favorites;
        DROP TABLE IF EXISTS watch_history;
        DROP TABLE IF EXISTS admin_logs;
    """)

    # Yangi jadvallarni yaratish
    conn.executescript("""
        CREATE TABLE users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            full_name  TEXT,
            is_premium INTEGER DEFAULT 0,
            is_banned  INTEGER DEFAULT 0,
            joined_at  TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE movies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            title_uz    TEXT,
            description TEXT,
            year        INTEGER,
            genre       TEXT,
            rating      REAL    DEFAULT 0,
            language    TEXT    DEFAULT 'UZ',
            file_id     TEXT,
            file_type   TEXT    DEFAULT 'video',
            views       INTEGER DEFAULT 0,
            is_premium  INTEGER DEFAULT 0,
            added_by    INTEGER,
            added_at    TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE favorites (
            user_id  INTEGER,
            movie_id INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, movie_id)
        );

        CREATE TABLE watch_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            movie_id   INTEGER,
            watched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE admin_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id   INTEGER,
            action     TEXT,
            target_id  TEXT,
            details    TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    log.info("✅ Database tayyor")

    # Backup papkasini yaratish
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

# ── Users ──
def user_save(uid, username, full_name):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?,?,?)",
        (uid, username, full_name)
    )
    conn.execute(
        "UPDATE users SET username=?, full_name=? WHERE user_id=?",
        (username, full_name, uid)
    )
    conn.commit()
    conn.close()

def user_get(uid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return row

def user_all_ids():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

def user_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return n

def user_set_ban(uid, val):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (val, uid))
    conn.commit()
    conn.close()

def user_set_premium(uid, val):
    conn = get_conn()
    conn.execute("UPDATE users SET is_premium=? WHERE user_id=?", (val, uid))
    conn.commit()
    conn.close()

def user_get_all(limit=100, offset=0):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return rows

def user_get_premium_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users WHERE is_premium=1").fetchone()[0]
    conn.close()
    return n

def user_get_banned_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
    conn.close()
    return n

# ── Movies ──
def movie_insert(title, title_uz, desc, year, genre, rating,
                 lang, file_id, file_type, is_premium, added_by):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO movies
            (title, title_uz, description, year, genre, rating,
             language, file_id, file_type, is_premium, added_by)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (title, title_uz, desc, year, genre, rating,
          lang, file_id, file_type, is_premium, added_by))
    mid = cur.lastrowid
    conn.commit()
    conn.close()

    # Admin logga yozish
    admin_log_add(added_by, "add_movie", str(mid), f"{title} ({title_uz})")
    return mid

def movie_get(mid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM movies WHERE id=?", (mid,)).fetchone()
    conn.close()
    return row

def movie_search(q, limit=10):
    conn = get_conn()
    p = f"%{q}%"
    rows = conn.execute(
        "SELECT * FROM movies WHERE title LIKE ? OR title_uz LIKE ? OR genre LIKE ? "
        "ORDER BY views DESC LIMIT ?",
        (p, p, p, limit)
    ).fetchall()
    conn.close()
    return rows

def movie_list(offset=0, limit=PER_PAGE, genre=None):
    conn = get_conn()
    sql = "SELECT * FROM movies WHERE 1=1"
    params = []
    if genre:
        sql += " AND genre LIKE ?"
        params.append(f"%{genre}%")
    sql += " ORDER BY added_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows

def movie_count(genre=None):
    conn = get_conn()
    if genre:
        n = conn.execute(
            "SELECT COUNT(*) FROM movies WHERE genre LIKE ?", (f"%{genre}%",)
        ).fetchone()[0]
    else:
        n = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    conn.close()
    return n

def movie_inc_views(mid):
    conn = get_conn()
    conn.execute("UPDATE movies SET views=views+1 WHERE id=?", (mid,))
    conn.commit()
    conn.close()

def movie_delete(mid):
    conn = get_conn()
    # Kinoni o'chirishdan oldin ma'lumotni olish
    movie = movie_get(mid)
    conn.execute("DELETE FROM movies WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    if movie:
        return movie
    return None

def movie_top(limit=PER_PAGE):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies ORDER BY views DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows

def movie_new(limit=PER_PAGE):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies ORDER BY added_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows

# Ruxsat etilgan ustunlar - SQL injection oldini olish uchun
ALLOWED_MOVIE_FIELDS = {
    "title", "title_uz", "description", "year", "genre",
    "rating", "language", "is_premium"
}

def movie_update(mid, field, value):
    if field not in ALLOWED_MOVIE_FIELDS:
        raise ValueError(f"Ruxsat etilmagan ustun: {field}")
    conn = get_conn()
    conn.execute(f"UPDATE movies SET {field}=? WHERE id=?", (value, mid))
    conn.commit()
    conn.close()

def movie_get_all(limit=50, offset=0):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies ORDER BY added_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return rows

def movie_get_by_genre(genre):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies WHERE genre LIKE ? ORDER BY views DESC",
        (f"%{genre}%",)
    ).fetchall()
    conn.close()
    return rows

def movie_get_stats():
    conn = get_conn()
    stats = conn.execute("""
        SELECT
            COUNT(*) as total_movies,
            SUM(CASE WHEN is_premium=1 THEN 1 ELSE 0 END) as premium_movies,
            SUM(CASE WHEN is_premium=0 THEN 1 ELSE 0 END) as free_movies,
            SUM(views) as total_views,
            AVG(rating) as avg_rating
        FROM movies
    """).fetchone()
    conn.close()
    return stats

# ── Favorites ──
def fav_add(uid, mid):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO favorites (user_id, movie_id) VALUES (?,?)", (uid, mid))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def fav_remove(uid, mid):
    conn = get_conn()
    conn.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?", (uid, mid))
    conn.commit()
    conn.close()

def fav_exists(uid, mid):
    conn = get_conn()
    r = conn.execute(
        "SELECT 1 FROM favorites WHERE user_id=? AND movie_id=?", (uid, mid)
    ).fetchone()
    conn.close()
    return r is not None

def fav_list(uid):
    conn = get_conn()
    rows = conn.execute("""
        SELECT m.* FROM movies m
        JOIN favorites f ON m.id = f.movie_id
        WHERE f.user_id = ?
        ORDER BY f.added_at DESC
    """, (uid,)).fetchall()
    conn.close()
    return rows

def fav_count(uid):
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    return n

# ── History ──
def hist_add(uid, mid):
    conn = get_conn()
    conn.execute(
        "INSERT INTO watch_history (user_id, movie_id) VALUES (?,?)", (uid, mid)
    )
    conn.commit()
    conn.close()

def hist_list(uid, limit=5):
    conn = get_conn()
    rows = conn.execute("""
        SELECT m.* FROM movies m
        JOIN watch_history wh ON m.id = wh.movie_id
        WHERE wh.user_id = ?
        ORDER BY wh.watched_at DESC LIMIT ?
    """, (uid, limit)).fetchall()
    conn.close()
    return rows

def hist_get_stats():
    conn = get_conn()
    stats = conn.execute("""
        SELECT
            COUNT(DISTINCT user_id) as active_users,
            COUNT(*) as total_watches
        FROM watch_history
        WHERE watched_at > datetime('now', '-7 days')
    """).fetchone()
    conn.close()
    return stats

# ── Admin Logs ──
def admin_log_add(admin_id, action, target_id, details):
    conn = get_conn()
    conn.execute(
        "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (?,?,?,?)",
        (admin_id, action, target_id, details)
    )
    conn.commit()
    conn.close()

def admin_log_get(limit=50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM admin_logs
        ORDER BY created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows

# ── Backup ──
def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"movies_backup_{timestamp}.db")

    import shutil
    shutil.copy2(DB_FILE, backup_file)
    return backup_file

def clear_old_backups(days=7):
    import time
    now = time.time()
    for filename in os.listdir(BACKUP_DIR):
        filepath = os.path.join(BACKUP_DIR, filename)
        if os.path.isfile(filepath):
            file_age = now - os.path.getmtime(filepath)
            if file_age > days * 86400:
                os.remove(filepath)

# ══════════════════════════════════════════
#              KEYBOARDS
# ══════════════════════════════════════════
def kb_main():
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="🎬 Kinolar"),      KeyboardButton(text="🔍 Qidirish"))
    kb.row(KeyboardButton(text="🔥 Top kinolar"),  KeyboardButton(text="🆕 Yangi kinolar"))
    kb.row(KeyboardButton(text="❤️ Sevimlilar"),   KeyboardButton(text="👤 Profil"))
    kb.row(KeyboardButton(text="ℹ️ Yordam"))
    return kb.as_markup(resize_keyboard=True)

def kb_admin():
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="✏️ Kinoni tahrirlash"))
    kb.row(KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Foydalanuvchilar"))
    kb.row(KeyboardButton(text="⭐ Premium boshqaruvi"), KeyboardButton(text="🚫 Ban boshqaruvi"))
    kb.row(KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="💾 Backup"))
    kb.row(KeyboardButton(text="📜 Admin loglar"), KeyboardButton(text="🎭 Janrlar ro'yxati"))
    kb.row(KeyboardButton(text="🏠 Bosh menyu"))
    return kb.as_markup(resize_keyboard=True)

def kb_admin_users():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="admin_list_users"))
    kb.row(InlineKeyboardButton(text="⭐ Premium foydalanuvchilar", callback_data="admin_list_premium"))
    kb.row(InlineKeyboardButton(text="🚫 Banlangan foydalanuvchilar", callback_data="admin_list_banned"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return kb.as_markup()

def kb_admin_premium():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Premium berish", callback_data="admin_add_premium"))
    kb.row(InlineKeyboardButton(text="➖ Premium olish", callback_data="admin_remove_premium"))
    kb.row(InlineKeyboardButton(text="📋 Premiumlar ro'yxati", callback_data="admin_list_premium"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return kb.as_markup()

def kb_admin_ban():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🚫 Ban qilish", callback_data="admin_ban_user"))
    kb.row(InlineKeyboardButton(text="✅ Ban bekor qilish", callback_data="admin_unban_user"))
    kb.row(InlineKeyboardButton(text="📋 Banlanganlar", callback_data="admin_list_banned"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return kb.as_markup()

def kb_user_list(users, page, total_pages):
    b = InlineKeyboardBuilder()
    for u in users[:PER_PAGE]:
        premium_icon = "⭐" if u["is_premium"] else "🆓"
        ban_icon = "🚫" if u["is_banned"] else "✅"
        text = f"{ban_icon} {premium_icon} {u['full_name'][:20]}"
        b.row(InlineKeyboardButton(text=text, callback_data=f"admin_user_{u['user_id']}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_users_page_{page+1}"))
    if nav:
        b.row(*nav)

    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return b.as_markup()

def kb_user_actions(user_id, is_banned, is_premium):
    b = InlineKeyboardBuilder()
    if not is_banned:
        b.row(InlineKeyboardButton(text="🚫 Ban qilish", callback_data=f"admin_ban_{user_id}"))
    else:
        b.row(InlineKeyboardButton(text="✅ Ban bekor qilish", callback_data=f"admin_unban_{user_id}"))

    if not is_premium:
        b.row(InlineKeyboardButton(text="⭐ Premium berish", callback_data=f"admin_premium_add_{user_id}"))
    else:
        b.row(InlineKeyboardButton(text="⭐ Premium olish", callback_data=f"admin_premium_rem_{user_id}"))

    b.row(InlineKeyboardButton(text="📊 Statistika", callback_data=f"admin_user_stats_{user_id}"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_list_users"))
    return b.as_markup()

def kb_movie_list_admin(movies, page, total_pages):
    b = InlineKeyboardBuilder()
    for m in movies[:PER_PAGE]:
        icon = "⭐" if m["is_premium"] else "🆓"
        title = m["title_uz"] or m["title"]
        b.row(InlineKeyboardButton(
            text=f"{icon} {title[:30]}",
            callback_data=f"admin_movie_{m['id']}"
        ))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_movies_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_movies_page_{page+1}"))
    if nav:
        b.row(*nav)

    b.row(InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="admin_add_movie"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return b.as_markup()

def kb_movie_actions(movie_id):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"admin_edit_movie_{movie_id}"))
    b.row(InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin_del_movie_{movie_id}"))
    b.row(InlineKeyboardButton(text="📊 Statistikani ko'rish", callback_data=f"admin_movie_stats_{movie_id}"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_movies_list"))
    return b.as_markup()

def kb_edit_movie_options(movie_id):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📝 Nomi", callback_data=f"edit_title_{movie_id}"))
    b.row(InlineKeyboardButton(text="📝 O'zbekcha nomi", callback_data=f"edit_title_uz_{movie_id}"))
    b.row(InlineKeyboardButton(text="📖 Tavsif", callback_data=f"edit_desc_{movie_id}"))
    b.row(InlineKeyboardButton(text="📅 Yil", callback_data=f"edit_year_{movie_id}"))
    b.row(InlineKeyboardButton(text="🎭 Janr", callback_data=f"edit_genre_{movie_id}"))
    b.row(InlineKeyboardButton(text="⭐ Reyting", callback_data=f"edit_rating_{movie_id}"))
    b.row(InlineKeyboardButton(text="🌍 Til", callback_data=f"edit_lang_{movie_id}"))
    b.row(InlineKeyboardButton(text="💎 Premium", callback_data=f"edit_premium_{movie_id}"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_movie_{movie_id}"))
    return b.as_markup()

def kb_cancel():
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="❌ Bekor qilish"))
    return kb.as_markup(resize_keyboard=True)

def kb_movie(mid, is_fav=False, is_premium=False):
    b = InlineKeyboardBuilder()
    fav_text = "💔 Sevimlilardan o'chirish" if is_fav else "❤️ Sevimlilarga qo'shish"
    b.row(InlineKeyboardButton(text=fav_text, callback_data=f"fav_{mid}"))
    watch_text = "⭐ Premium — Ko'rish" if is_premium else "▶️ Ko'rish"
    b.row(InlineKeyboardButton(text=watch_text, callback_data=f"watch_{mid}"))
    b.row(InlineKeyboardButton(text="📤 Ulashish", switch_inline_query=str(mid)))
    return b.as_markup()

def kb_movie_list(movies, page, total_pages, genre=""):
    b = InlineKeyboardBuilder()
    for m in movies:
        icon  = "⭐" if m["is_premium"] else "🆓"
        title = m["title_uz"] or m["title"]
        b.row(InlineKeyboardButton(
            text=f"{icon} {title} [{m['language'] or 'UZ'}]",
            callback_data=f"movie_{m['id']}"
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{page-1}_{genre}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}_{genre}"))
    if nav:
        b.row(*nav)
    return b.as_markup()

def kb_confirm(action, item_id):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Ha",   callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_cb")
    )
    return b.as_markup()

def kb_lang():
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇺🇿 O'zbek",  callback_data="lang_UZ"),
        InlineKeyboardButton(text="🇷🇺 Rus",      callback_data="lang_RU"),
        InlineKeyboardButton(text="🌍 Barchasi",  callback_data="lang_ALL"),
    )
    return b.as_markup()

def kb_sub(channel):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="📢 Kanalga o'tish",
        url=f"https://t.me/{channel.lstrip('@')}"
    ))
    b.row(InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="check_sub"))
    return b.as_markup()

def kb_genres(genres):
    b = InlineKeyboardBuilder()
    for genre in genres[:12]:
        b.row(InlineKeyboardButton(text=f"🎭 {genre}", callback_data=f"genre_{genre}"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu"))
    return b.as_markup()

# ══════════════════════════════════════════
#              HELPERS
# ══════════════════════════════════════════
def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

async def check_sub(bot: Bot, uid: int) -> bool:
    if not CHANNEL_USERNAME:
        return True
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status not in ("left", "kicked", "banned")
    except Exception:
        return True

def fmt_movie(m) -> str:
    premium = "⭐ Premium" if m["is_premium"] else "🆓 Bepul"
    stars   = "⭐" * int(m["rating"] or 0)
    title   = m["title"]
    text    = f"🎬 <b>{title}</b>\n"
    if m["title_uz"] and m["title_uz"] != title:
        text += f"📝 <i>{m['title_uz']}</i>\n"
    text += (
        f"\n📅 Yil: <b>{m['year'] or '—'}</b>"
        f"\n🎭 Janr: <b>{m['genre'] or '—'}</b>"
        f"\n🌍 Til: <b>{m['language'] or 'UZ'}</b>"
        f"\n⭐ Reyting: <b>{m['rating'] or '—'}</b> {stars}"
        f"\n💎 Tur: <b>{premium}</b>"
        f"\n👁 Ko'rildi: <b>{m['views'] or 0}</b> marta"
        f"\n\n📖 <i>{m['description'] or 'Tavsif yoq'}</i>"
    )
    return text

def get_all_genres():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT genre FROM movies WHERE genre IS NOT NULL AND genre != ''").fetchall()
    conn.close()
    genres = set()
    for row in rows:
        if row["genre"]:
            for g in row["genre"].split(","):
                genres.add(g.strip())
    return sorted(list(genres))

# ══════════════════════════════════════════
#               FSM STATES
# ══════════════════════════════════════════
class AddMovie(StatesGroup):
    title       = State()
    title_uz    = State()
    description = State()
    year        = State()
    genre       = State()
    rating      = State()
    language    = State()
    file        = State()
    premium     = State()

class EditMovie(StatesGroup):
    field = State()
    value = State()

class SearchSt(StatesGroup):
    query = State()

class BroadcastSt(StatesGroup):
    msg = State()

class AdminAddPremium(StatesGroup):
    user_id = State()

class AdminRemovePremium(StatesGroup):
    user_id = State()

class AdminBanUser(StatesGroup):
    user_id = State()

class AdminUnbanUser(StatesGroup):
    user_id = State()

# ══════════════════════════════════════════
#               HANDLERS
# ══════════════════════════════════════════
router = Router()

# ─── /start ───────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    u = message.from_user
    user_save(u.id, u.username or "", u.full_name or "")

    if CHANNEL_USERNAME and not await check_sub(bot, u.id):
        await message.answer(
            f"👋 Salom, <b>{u.first_name}</b>!\n\n"
            f"⚠️ Botdan foydalanish uchun avval kanalga a'zo bo'ling:",
            reply_markup=kb_sub(CHANNEL_USERNAME),
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"👋 Salom, <b>{u.first_name}</b>!\n\n"
        f"🎬 <b>{BOT_NAME}</b> ga xush kelibsiz!\n\n"
        f"• Kinolar ko'ring\n"
        f"• 🔍 Qidiring\n"
        f"• ❤️ Sevimlilarga saqlang",
        reply_markup=kb_main(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "check_sub")
async def on_check_sub(call: CallbackQuery, bot: Bot):
    if await check_sub(bot, call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Xush kelibsiz!", reply_markup=kb_main())
    else:
        await call.answer("❌ Hali a'zo bo'lmadingiz!", show_alert=True)

# ─── /admin ───────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Ruxsat yo'q!")

    stats = movie_get_stats()
    user_stats = hist_get_stats()
    avg_rating = stats['avg_rating'] if stats['avg_rating'] is not None else 0.0

    await message.answer(
        f"🔐 <b>Admin Panel</b>\n\n"
        f"📊 <b>Umumiy statistika:</b>\n"
        f"👥 Foydalanuvchilar: <b>{user_count()}</b>\n"
        f"⭐ Premium foydalanuvchilar: <b>{user_get_premium_count()}</b>\n"
        f"🚫 Banlanganlar: <b>{user_get_banned_count()}</b>\n\n"
        f"🎬 <b>Kinolar:</b>\n"
        f"Jami kinolar: <b>{stats['total_movies']}</b>\n"
        f"⭐ Premium kinolar: <b>{stats['premium_movies'] or 0}</b>\n"
        f"🆓 Bepul kinolar: <b>{stats['free_movies'] or 0}</b>\n"
        f"👁 Jami ko'rishlar: <b>{stats['total_views'] or 0}</b>\n"
        f"⭐ O'rtacha reyting: <b>{avg_rating:.1f}</b>\n\n"
        f"📈 <b>Faollik (7 kun):</b>\n"
        f"Aktiv foydalanuvchilar: <b>{user_stats['active_users'] or 0}</b>\n"
        f"Jami ko'rishlar: <b>{user_stats['total_watches'] or 0}</b>",
        reply_markup=kb_admin(),
        parse_mode="HTML"
    )

@router.message(F.text == "🏠 Bosh menyu")
async def go_home(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await message.answer("🏠 Bosh menyu:", reply_markup=kb_admin())
    else:
        await message.answer("🏠 Bosh menyu:", reply_markup=kb_main())

# ─── ADMIN: FOYDALANUVCHILAR ──────────────
@router.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "👥 <b>Foydalanuvchilar boshqaruvi</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=kb_admin_users(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_list_users")
async def admin_list_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    users = user_get_all(limit=100)
    if not users:
        return await call.message.edit_text("❌ Foydalanuvchilar topilmadi!")

    total_pages = max(1, math.ceil(len(users) / PER_PAGE))
    await call.message.edit_text(
        f"👥 <b>Barcha foydalanuvchilar</b> ({len(users)} ta):",
        reply_markup=kb_user_list(users, 0, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_users_page_"))
async def admin_users_page(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    page = int(call.data.split("_")[3])
    users = user_get_all(limit=100)
    total_pages = max(1, math.ceil(len(users) / PER_PAGE))

    start = page * PER_PAGE
    end = start + PER_PAGE
    page_users = users[start:end]

    await call.message.edit_reply_markup(
        reply_markup=kb_user_list(page_users, page, total_pages)
    )

@router.callback_query(F.data.startswith("admin_user_"), F.data.regexp(r"^admin_user_\d+$"))
async def admin_user_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[2])
    user = user_get(user_id)

    if not user:
        return await call.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)

    fav_count_val = fav_count(user_id)

    text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Ism: <b>{user['full_name']}</b>\n"
        f"📝 Username: @{user['username'] if user['username'] else '—'}\n"
        f"⭐ Premium: {'✅ Ha' if user['is_premium'] else '❌ Yoq'}\n"
        f"🚫 Ban: {'✅ Ha' if user['is_banned'] else '❌ Yoq'}\n"
        f"❤️ Sevimlilar: <b>{fav_count_val}</b> ta\n"
        f"📅 Qo'shilgan: <b>{user['joined_at']}</b>"
    )

    await call.message.edit_text(
        text,
        reply_markup=kb_user_actions(user_id, user['is_banned'], user['is_premium']),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_user_stats_"))
async def admin_user_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[3])
    history = hist_list(user_id, limit=10)
    favs = fav_list(user_id)

    text = (
        f"📊 <b>Foydalanuvchi statistikasi</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"❤️ Sevimlilar: <b>{len(favs)}</b> ta\n"
        f"📺 Ko'rilgan kinolar: <b>{len(history)}</b> ta (oxirgi 10 ta)\n\n"
    )

    if history:
        text += "<b>📽 Oxirgi ko'rilganlar:</b>\n"
        for h in history[:5]:
            text += f"• {h['title_uz'] or h['title']}\n"

    await call.message.edit_text(text, parse_mode="HTML")
    await asyncio.sleep(3)
    await admin_user_detail(call)

# ─── ADMIN: PREMIUM BOSHQARUVI ────────────
@router.message(F.text == "⭐ Premium boshqaruvi")
async def admin_premium(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "⭐ <b>Premium boshqaruvi</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=kb_admin_premium(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_add_premium")
async def admin_add_premium_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    await call.message.edit_text(
        "⭐ <b>Premium berish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "Masalan: <code>123456789</code>",
        parse_mode="HTML"
    )
    await state.set_state(AdminAddPremium.user_id)

@router.message(AdminAddPremium.user_id)
async def admin_add_premium_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Noto'g'ri ID! Iltimos, raqam kiriting.")

    user = user_get(user_id)
    if not user:
        return await message.answer(f"❌ ID {user_id} li foydalanuvchi topilmadi!")

    if user["is_premium"]:
        return await message.answer(f"❌ {user['full_name']} allaqachon premium!")

    user_set_premium(user_id, 1)
    admin_log_add(message.from_user.id, "add_premium", str(user_id), user['full_name'])

    await message.answer(f"✅ {user['full_name']} ga premium berildi!")
    await state.clear()

@router.callback_query(F.data == "admin_remove_premium")
async def admin_remove_premium_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    await call.message.edit_text(
        "⭐ <b>Premium olish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(AdminRemovePremium.user_id)

@router.message(AdminRemovePremium.user_id)
async def admin_remove_premium_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Noto'g'ri ID!")

    user = user_get(user_id)
    if not user:
        return await message.answer(f"❌ ID {user_id} li foydalanuvchi topilmadi!")

    if not user["is_premium"]:
        return await message.answer(f"❌ {user['full_name']} premium emas!")

    user_set_premium(user_id, 0)
    admin_log_add(message.from_user.id, "remove_premium", str(user_id), user['full_name'])

    await message.answer(f"✅ {user['full_name']} dan premium olib tashlandi!")
    await state.clear()

@router.callback_query(F.data.startswith("admin_premium_add_"))
async def admin_premium_add_from_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[3])
    user = user_get(user_id)

    if user["is_premium"]:
        return await call.answer("❌ Foydalanuvchi allaqachon premium!", show_alert=True)

    user_set_premium(user_id, 1)
    admin_log_add(call.from_user.id, "add_premium", str(user_id), user['full_name'])
    await call.answer(f"✅ {user['full_name']} ga premium berildi!")
    await admin_user_detail(call)

@router.callback_query(F.data.startswith("admin_premium_rem_"))
async def admin_premium_remove_from_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[3])
    user = user_get(user_id)

    if not user["is_premium"]:
        return await call.answer("❌ Foydalanuvchi premium emas!", show_alert=True)

    user_set_premium(user_id, 0)
    admin_log_add(call.from_user.id, "remove_premium", str(user_id), user['full_name'])
    await call.answer(f"✅ {user['full_name']} dan premium olib tashlandi!")
    await admin_user_detail(call)

# ─── ADMIN: BAN BOSHQARUVI ────────────────
@router.message(F.text == "🚫 Ban boshqaruvi")
async def admin_ban(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🚫 <b>Ban boshqaruvi</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=kb_admin_ban(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_ban_user")
async def admin_ban_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    await call.message.edit_text(
        "🚫 <b>Ban qilish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(AdminBanUser.user_id)

@router.message(AdminBanUser.user_id)
async def admin_ban_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Noto'g'ri ID!")

    if user_id in ADMIN_IDS:
        return await message.answer("❌ Adminni ban qilib bo'lmaydi!")

    user = user_get(user_id)
    if not user:
        return await message.answer(f"❌ ID {user_id} li foydalanuvchi topilmadi!")

    if user["is_banned"]:
        return await message.answer(f"❌ {user['full_name']} allaqachon banlangan!")

    user_set_ban(user_id, 1)
    admin_log_add(message.from_user.id, "ban_user", str(user_id), user['full_name'])

    await message.answer(f"✅ {user['full_name']} ban qilindi!")
    await state.clear()

@router.callback_query(F.data == "admin_unban_user")
async def admin_unban_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    await call.message.edit_text(
        "✅ <b>Ban bekor qilish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(AdminUnbanUser.user_id)

@router.message(AdminUnbanUser.user_id)
async def admin_unban_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Noto'g'ri ID!")

    user = user_get(user_id)
    if not user:
        return await message.answer(f"❌ ID {user_id} li foydalanuvchi topilmadi!")

    if not user["is_banned"]:
        return await message.answer(f"❌ {user['full_name']} banlanmagan!")

    user_set_ban(user_id, 0)
    admin_log_add(message.from_user.id, "unban_user", str(user_id), user['full_name'])

    await message.answer(f"✅ {user['full_name']} ning bani olib tashlandi!")
    await state.clear()

@router.callback_query(F.data.startswith("admin_ban_"), F.data.regexp(r"^admin_ban_\d+$"))
async def admin_ban_from_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[2])

    if user_id in ADMIN_IDS:
        return await call.answer("❌ Adminni ban qilib bo'lmaydi!", show_alert=True)

    user = user_get(user_id)
    if user["is_banned"]:
        return await call.answer("❌ Foydalanuvchi allaqachon banlangan!", show_alert=True)

    user_set_ban(user_id, 1)
    admin_log_add(call.from_user.id, "ban_user", str(user_id), user['full_name'])
    await call.answer(f"✅ {user['full_name']} ban qilindi!")
    await admin_user_detail(call)

@router.callback_query(F.data.startswith("admin_unban_"), F.data.regexp(r"^admin_unban_\d+$"))
async def admin_unban_from_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[2])
    user = user_get(user_id)

    if not user["is_banned"]:
        return await call.answer("❌ Foydalanuvchi banlanmagan!", show_alert=True)

    user_set_ban(user_id, 0)
    admin_log_add(call.from_user.id, "unban_user", str(user_id), user['full_name'])
    await call.answer(f"✅ {user['full_name']} ning bani olib tashlandi!")
    await admin_user_detail(call)

@router.callback_query(F.data == "admin_list_banned")
async def admin_list_banned(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    conn = get_conn()
    users = conn.execute("SELECT * FROM users WHERE is_banned=1").fetchall()
    conn.close()

    if not users:
        return await call.message.edit_text("✅ Banlangan foydalanuvchilar yo'q!")

    text = "🚫 <b>Banlangan foydalanuvchilar:</b>\n\n"
    for u in users:
        text += f"🆔 <code>{u['user_id']}</code> — {u['full_name']}\n"

    await call.message.edit_text(text, parse_mode="HTML")

@router.callback_query(F.data == "admin_list_premium")
async def admin_list_premium(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    conn = get_conn()
    users = conn.execute("SELECT * FROM users WHERE is_premium=1").fetchall()
    conn.close()

    if not users:
        return await call.message.edit_text("⭐ Premium foydalanuvchilar yo'q!")

    text = "⭐ <b>Premium foydalanuvchilar:</b>\n\n"
    for u in users:
        text += f"🆔 <code>{u['user_id']}</code> — {u['full_name']}\n"

    await call.message.edit_text(text, parse_mode="HTML")

# ─── ADMIN: KINOLAR BOSHQARUVI ────────────
@router.message(F.text == "✏️ Kinoni tahrirlash")
async def admin_movies_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    movies = movie_get_all(limit=50)
    if not movies:
        return await message.answer("❌ Hozircha kinolar yo'q!")

    total_pages = max(1, math.ceil(len(movies) / PER_PAGE))
    await message.answer(
        "✏️ <b>Kinoni tahrirlash</b>\n\n"
        "Tahrirlamoqchi bo'lgan kinoni tanlang:",
        reply_markup=kb_movie_list_admin(movies, 0, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_movies_list")
async def admin_movies_list_cb(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movies = movie_get_all(limit=50)
    if not movies:
        return await call.message.edit_text("❌ Hozircha kinolar yo'q!")

    total_pages = max(1, math.ceil(len(movies) / PER_PAGE))
    await call.message.edit_text(
        "✏️ <b>Kinoni tahrirlash</b>\n\n"
        "Tahrirlamoqchi bo'lgan kinoni tanlang:",
        reply_markup=kb_movie_list_admin(movies, 0, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_movies_page_"))
async def admin_movies_page(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    page = int(call.data.split("_")[3])
    movies = movie_get_all(limit=50)
    total_pages = max(1, math.ceil(len(movies) / PER_PAGE))

    start = page * PER_PAGE
    end = start + PER_PAGE
    page_movies = movies[start:end]

    await call.message.edit_reply_markup(
        reply_markup=kb_movie_list_admin(page_movies, page, total_pages)
    )

@router.callback_query(F.data.startswith("admin_movie_"), F.data.regexp(r"^admin_movie_\d+$"))
async def admin_movie_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[2])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    await call.message.edit_text(
        fmt_movie(movie),
        reply_markup=kb_movie_actions(movie_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_edit_movie_"))
async def admin_edit_movie_start(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[3])
    await call.message.edit_text(
        "✏️ <b>Kinoni tahrirlash</b>\n\n"
        "Qaysi ma'lumotni o'zgartirmoqchisiz?",
        reply_markup=kb_edit_movie_options(movie_id),
        parse_mode="HTML"
    )

# Kino tahrirlash uchun handlerlar
edit_fields = {
    "edit_title_uz_": "title_uz",
    "edit_title_": "title",
    "edit_desc_": "description",
    "edit_year_": "year",
    "edit_genre_": "genre",
    "edit_rating_": "rating",
    "edit_lang_": "language",
    "edit_premium_": "is_premium"
}

@router.callback_query(F.data.startswith(tuple(edit_fields.keys())))
async def admin_edit_field_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    for prefix, field in edit_fields.items():
        if call.data.startswith(prefix):
            movie_id = int(call.data.replace(prefix, ""))
            await state.update_data(movie_id=movie_id, field=field)

            prompts = {
                "title": "Yangi nomini kiriting:",
                "title_uz": "Yangi o'zbekcha nomini kiriting:",
                "description": "Yangi tavsifini kiriting:",
                "year": "Yangi yilini kiriting (masalan: 2024):",
                "genre": "Yangi janrini kiriting:",
                "rating": "Yangi reytingini kiriting (0-10):",
                "language": "Yangi tilini kiriting (UZ, RU, EN):",
                "is_premium": "Premium kinomi? (ha/yo'q):"
            }

            await call.message.edit_text(prompts[field])
            await state.set_state(EditMovie.value)
            break

@router.message(EditMovie.value)
async def admin_edit_field_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    movie_id = data["movie_id"]
    field = data["field"]
    value = message.text.strip()

    if field == "year":
        if not value.isdigit():
            return await message.answer("❌ Yil raqam bo'lishi kerak!")
        value = int(value)
    elif field == "rating":
        try:
            value = float(value.replace(",", "."))
            value = max(0.0, min(10.0, value))
        except ValueError:
            return await message.answer("❌ Reyting 0-10 oralig'ida bo'lishi kerak!")
    elif field == "is_premium":
        value = 1 if value.lower() in ["ha", "yes", "1", "true"] else 0

    movie_update(movie_id, field, value)
    admin_log_add(message.from_user.id, f"edit_movie_{field}", str(movie_id), str(value))

    await message.answer(f"✅ {field} muvaffaqiyatli o'zgartirildi!", reply_markup=kb_admin())
    await state.clear()

@router.callback_query(F.data.startswith("admin_del_movie_"))
async def admin_del_movie_confirm(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[3])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    await call.message.edit_text(
        f"🗑 <b>{movie['title_uz'] or movie['title']}</b> kinosini o'chirishni tasdiqlaysizmi?",
        reply_markup=kb_confirm("del_movie", movie_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("confirm_del_movie_"))
async def admin_del_movie_execute(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[3])
    movie = movie_delete(movie_id)

    if movie:
        admin_log_add(call.from_user.id, "delete_movie", str(movie_id), movie['title'])
        await call.message.edit_text(f"✅ <b>{movie['title_uz'] or movie['title']}</b> o'chirildi!", parse_mode="HTML")
    else:
        await call.message.edit_text("❌ Kino topilmadi!")

@router.callback_query(F.data.startswith("admin_movie_stats_"))
async def admin_movie_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[3])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    conn = get_conn()
    fav_count_val = conn.execute(
        "SELECT COUNT(*) FROM favorites WHERE movie_id=?", (movie_id,)
    ).fetchone()[0]
    hist_count = conn.execute(
        "SELECT COUNT(*) FROM watch_history WHERE movie_id=?", (movie_id,)
    ).fetchone()[0]
    conn.close()

    text = (
        f"📊 <b>Kino statistikasi</b>\n\n"
        f"🎬 Nomi: <b>{movie['title_uz'] or movie['title']}</b>\n"
        f"👁 Ko'rishlar: <b>{movie['views']}</b>\n"
        f"❤️ Sevimlilarga qo'shilgan: <b>{fav_count_val}</b>\n"
        f"📺 Ko'rilganlar: <b>{hist_count}</b>\n"
        f"⭐ Reyting: <b>{movie['rating']}</b>\n"
        f"💎 Tur: <b>{'Premium' if movie['is_premium'] else 'Bepul'}</b>"
    )

    await call.message.edit_text(text, parse_mode="HTML")
    await asyncio.sleep(3)
    await admin_movie_detail(call)

# ─── ADMIN: BACKUP ────────────────────────
@router.message(F.text == "💾 Backup")
async def admin_backup(message: Message):
    if not is_admin(message.from_user.id):
        return

    status_msg = await message.answer("💾 <b>Backup yaratilmoqda...</b>", parse_mode="HTML")

    try:
        backup_file = backup_database()
        clear_old_backups(days=7)

        await status_msg.delete()

        # Faylni yuborish
        await message.answer_document(
            document=FSInputFile(backup_file),
            caption=f"✅ <b>Backup yaratildi!</b>\n\n"
                   f"📅 Sana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                   f"💾 Fayl hajmi: {os.path.getsize(backup_file) / 1024:.2f} KB",
            parse_mode="HTML"
        )

        admin_log_add(message.from_user.id, "backup", backup_file, "Database backup created")

    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik: {str(e)}")

# ─── ADMIN: LOGLAR ────────────────────────
@router.message(F.text == "📜 Admin loglar")
async def admin_logs(message: Message):
    if not is_admin(message.from_user.id):
        return

    logs = admin_log_get(limit=30)
    if not logs:
        return await message.answer("📜 Hech qanday log yo'q!")

    text = "📜 <b>Admin loglari (oxirgi 30 ta):</b>\n\n"
    for log_entry in logs:
        text += f"🕒 {log_entry['created_at']}\n"
        text += f"👤 Admin: <code>{log_entry['admin_id']}</code>\n"
        text += f"📝 Amal: <b>{log_entry['action']}</b>\n"
        text += f"🎯 Target: <code>{log_entry['target_id']}</code>\n"
        text += f"📄 Detail: {(log_entry['details'] or '')[:50]}\n"
        text += "─" * 30 + "\n"

    # Agar xabar juda uzun bo'lsa, qismlarga bo'lib yuborish
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

# ─── ADMIN: JANRLAR RO'YXATI ──────────────
@router.message(F.text == "🎭 Janrlar ro'yxati")
async def admin_genres(message: Message):
    if not is_admin(message.from_user.id):
        return

    genres = get_all_genres()
    if not genres:
        return await message.answer("❌ Hech qanday janr topilmadi!")

    text = "🎭 <b>Barcha janrlar:</b>\n\n"
    for i, genre in enumerate(genres, 1):
        # Janrdagi kinolar sonini olish
        count = movie_count(genre=genre)
        text += f"{i}. {genre} — <b>{count}</b> ta kino\n"

    await message.answer(text, parse_mode="HTML")

# ─── ADMIN: STATISTIKA ────────────────────
@router.message(F.text == "📊 Statistika")
async def admin_stats_btn(message: Message):
    if not is_admin(message.from_user.id):
        return
    await cmd_admin(message)

# ─── ADMIN: ORQAGA ────────────────────────
@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    stats = movie_get_stats()
    user_stats = hist_get_stats()
    avg_rating = stats['avg_rating'] if stats['avg_rating'] is not None else 0.0

    await call.message.edit_text(
        f"🔐 <b>Admin Panel</b>\n\n"
        f"📊 <b>Umumiy statistika:</b>\n"
        f"👥 Foydalanuvchilar: <b>{user_count()}</b>\n"
        f"⭐ Premium foydalanuvchilar: <b>{user_get_premium_count()}</b>\n"
        f"🚫 Banlanganlar: <b>{user_get_banned_count()}</b>\n\n"
        f"🎬 <b>Kinolar:</b>\n"
        f"Jami kinolar: <b>{stats['total_movies']}</b>\n"
        f"⭐ Premium kinolar: <b>{stats['premium_movies'] or 0}</b>\n"
        f"🆓 Bepul kinolar: <b>{stats['free_movies'] or 0}</b>\n"
        f"👁 Jami ko'rishlar: <b>{stats['total_views'] or 0}</b>\n"
        f"⭐ O'rtacha reyting: <b>{avg_rating:.1f}</b>\n\n"
        f"📈 <b>Faollik (7 kun):</b>\n"
        f"Aktiv foydalanuvchilar: <b>{user_stats['active_users'] or 0}</b>\n"
        f"Jami ko'rishlar: <b>{user_stats['total_watches'] or 0}</b>",
        parse_mode="HTML"
    )

# ─── KINO QO'SHISH ────────────────────────
@router.message(F.text == "➕ Kino qo'shish")
async def add_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🎬 Kino nomini kiriting (inglizcha):", reply_markup=kb_cancel())
    await state.set_state(AddMovie.title)

@router.callback_query(F.data == "admin_add_movie")
async def add_start_cb(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
    await call.message.answer("🎬 Kino nomini kiriting (inglizcha):", reply_markup=kb_cancel())
    await state.set_state(AddMovie.title)

@router.message(AddMovie.title)
async def add_title(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    await state.update_data(title=message.text.strip())
    await message.answer("📝 O'zbekcha nomini kiriting:")
    await state.set_state(AddMovie.title_uz)

@router.message(AddMovie.title_uz)
async def add_title_uz(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    await state.update_data(title_uz=message.text.strip())
    await message.answer("📖 Tavsifini kiriting:")
    await state.set_state(AddMovie.description)

@router.message(AddMovie.description)
async def add_desc(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    await state.update_data(description=message.text.strip())
    await message.answer("📅 Yilini kiriting (masalan: 2024):")
    await state.set_state(AddMovie.year)

@router.message(AddMovie.year)
async def add_year(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    if not message.text.isdigit():
        return await message.answer("❌ Faqat raqam kiriting! Masalan: 2024")
    await state.update_data(year=int(message.text))
    await message.answer("🎭 Janrini kiriting (Aksion, Drama, Komediya...):")
    await state.set_state(AddMovie.genre)

@router.message(AddMovie.genre)
async def add_genre(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    await state.update_data(genre=message.text.strip())
    await message.answer("⭐ Reytingini kiriting (0-10, masalan: 8.5):")
    await state.set_state(AddMovie.rating)

@router.message(AddMovie.rating)
async def add_rating(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    try:
        rating = float(message.text.replace(",", "."))
        rating = max(0.0, min(10.0, rating))
    except ValueError:
        return await message.answer("❌ Raqam kiriting! Masalan: 8.5")
    await state.update_data(rating=rating)
    await message.answer("🌍 Tilini tanlang:", reply_markup=kb_lang())
    await state.set_state(AddMovie.language)

@router.callback_query(AddMovie.language, F.data.startswith("lang_"))
async def add_lang(call: CallbackQuery, state: FSMContext):
    lang = call.data.replace("lang_", "")
    await state.update_data(language=lang)
    await call.message.edit_text("🎬 Kino faylini yuboring (video yoki hujjat):")
    await state.set_state(AddMovie.file)

@router.message(AddMovie.file)
async def add_file(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    if message.video:
        await state.update_data(file_id=message.video.file_id, file_type="video")
    elif message.document:
        await state.update_data(file_id=message.document.file_id, file_type="document")
    else:
        return await message.answer("❌ Iltimos, video yoki hujjat yuboring!")
    await message.answer("💎 Bu premium kino bo'lsinmi?", reply_markup=kb_confirm("premium", 1))
    await state.set_state(AddMovie.premium)

@router.callback_query(AddMovie.premium, F.data.startswith("confirm_premium_"))
async def add_premium_yes(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    mid = movie_insert(
        data.get("title", ""), data.get("title_uz", ""),
        data.get("description", ""), data.get("year", 0),
        data.get("genre", ""), data.get("rating", 0.0),
        data.get("language", "UZ"), data.get("file_id", ""),
        data.get("file_type", "video"), 1, call.from_user.id
    )
    await call.message.edit_text(
        f"✅ <b>Premium kino</b> qo'shildi!\n🆔 ID: <code>{mid}</code>",
        parse_mode="HTML"
    )
    await call.message.answer("Admin panel:", reply_markup=kb_admin())

@router.callback_query(AddMovie.premium, F.data == "cancel_cb")
async def add_premium_no(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    mid = movie_insert(
        data.get("title", ""), data.get("title_uz", ""),
        data.get("description", ""), data.get("year", 0),
        data.get("genre", ""), data.get("rating", 0.0),
        data.get("language", "UZ"), data.get("file_id", ""),
        data.get("file_type", "video"), 0, call.from_user.id
    )
    await call.message.edit_text(
        f"✅ <b>Bepul kino</b> qo'shildi!\n🆔 ID: <code>{mid}</code>",
        parse_mode="HTML"
    )
    await call.message.answer("Admin panel:", reply_markup=kb_admin())

# ─── FOYDALANUVCHI: KINOLAR RO'YXATI ──────
@router.message(F.text == "🎬 Kinolar")
async def user_movies(message: Message):
    movies = movie_list(offset=0, limit=PER_PAGE)
    if not movies:
        return await message.answer("❌ Hozircha kinolar yo'q!")

    total = movie_count()
    total_pages = max(1, math.ceil(total / PER_PAGE))
    await message.answer(
        "🎬 <b>Barcha kinolar:</b>",
        reply_markup=kb_movie_list(movies, 0, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("page_"))
async def user_movies_page(call: CallbackQuery):
    parts = call.data.split("_", 2)
    page = int(parts[1])
    genre = parts[2] if len(parts) > 2 and parts[2] else None

    movies = movie_list(offset=page * PER_PAGE, limit=PER_PAGE, genre=genre)
    total = movie_count(genre=genre)
    total_pages = max(1, math.ceil(total / PER_PAGE))

    await call.message.edit_reply_markup(
        reply_markup=kb_movie_list(movies, page, total_pages, genre or "")
    )

@router.callback_query(F.data.startswith("movie_"))
async def user_movie_detail(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    is_fav = fav_exists(call.from_user.id, movie_id)
    await call.message.answer(
        fmt_movie(movie),
        reply_markup=kb_movie(movie_id, is_fav, bool(movie["is_premium"])),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("watch_"))
async def user_watch_movie(call: CallbackQuery, bot: Bot):
    movie_id = int(call.data.split("_")[1])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    user = user_get(call.from_user.id)
    if movie["is_premium"] and not (user and user["is_premium"]):
        return await call.answer("⭐ Bu kino faqat premium foydalanuvchilar uchun!", show_alert=True)

    movie_inc_views(movie_id)
    hist_add(call.from_user.id, movie_id)

    if movie["file_type"] == "video":
        await bot.send_video(call.from_user.id, movie["file_id"], caption=movie["title_uz"] or movie["title"])
    else:
        await bot.send_document(call.from_user.id, movie["file_id"], caption=movie["title_uz"] or movie["title"])
    await call.answer()

@router.callback_query(F.data.startswith("fav_"))
async def user_toggle_fav(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])
    uid = call.from_user.id

    if fav_exists(uid, movie_id):
        fav_remove(uid, movie_id)
        await call.answer("💔 Sevimlilardan o'chirildi")
    else:
        fav_add(uid, movie_id)
        await call.answer("❤️ Sevimlilarga qo'shildi")

    movie = movie_get(movie_id)
    is_fav = fav_exists(uid, movie_id)
    try:
        await call.message.edit_reply_markup(
            reply_markup=kb_movie(movie_id, is_fav, bool(movie["is_premium"]))
        )
    except Exception:
        pass

# ─── FOYDALANUVCHI: TOP / YANGI ───────────
@router.message(F.text == "🔥 Top kinolar")
async def user_top_movies(message: Message):
    movies = movie_top(limit=PER_PAGE)
    if not movies:
        return await message.answer("❌ Hozircha kinolar yo'q!")
    await message.answer(
        "🔥 <b>Top kinolar:</b>",
        reply_markup=kb_movie_list(movies, 0, 1),
        parse_mode="HTML"
    )

@router.message(F.text == "🆕 Yangi kinolar")
async def user_new_movies(message: Message):
    movies = movie_new(limit=PER_PAGE)
    if not movies:
        return await message.answer("❌ Hozircha kinolar yo'q!")
    await message.answer(
        "🆕 <b>Yangi kinolar:</b>",
        reply_markup=kb_movie_list(movies, 0, 1),
        parse_mode="HTML"
    )

# ─── FOYDALANUVCHI: SEVIMLILAR ────────────
@router.message(F.text == "❤️ Sevimlilar")
async def user_favorites(message: Message):
    movies = fav_list(message.from_user.id)
    if not movies:
        return await message.answer("❌ Sevimlilar ro'yxati bo'sh!")
    await message.answer(
        "❤️ <b>Sevimli kinolaringiz:</b>",
        reply_markup=kb_movie_list(movies, 0, 1),
        parse_mode="HTML"
    )

# ─── FOYDALANUVCHI: QIDIRISH ───────────────
@router.message(F.text == "🔍 Qidirish")
async def user_search_start(message: Message, state: FSMContext):
    await message.answer("🔍 Qidirmoqchi bo'lgan kino nomini kiriting:", reply_markup=kb_cancel())
    await state.set_state(SearchSt.query)

@router.message(SearchSt.query)
async def user_search_process(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_main())

    results = movie_search(message.text.strip())
    await state.clear()

    if not results:
        return await message.answer("❌ Hech narsa topilmadi!", reply_markup=kb_main())

    await message.answer(
        f"🔍 <b>Qidiruv natijalari</b> ({len(results)} ta):",
        reply_markup=kb_movie_list(results, 0, 1),
        parse_mode="HTML"
    )

# ─── FOYDALANUVCHI: PROFIL ─────────────────
@router.message(F.text == "👤 Profil")
async def user_profile(message: Message):
    user = user_get(message.from_user.id)
    if not user:
        return await message.answer("❌ Ma'lumot topilmadi!")

    favs = fav_count(message.from_user.id)
    history = hist_list(message.from_user.id, limit=100)

    text = (
        f"👤 <b>Sizning profilingiz</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Ism: <b>{user['full_name']}</b>\n"
        f"⭐ Premium: {'✅ Ha' if user['is_premium'] else '❌ Yoq'}\n"
        f"❤️ Sevimlilar: <b>{favs}</b> ta\n"
        f"📺 Ko'rilgan kinolar: <b>{len(history)}</b> ta\n"
        f"📅 Ro'yxatdan o'tgan: <b>{user['joined_at']}</b>"
    )
    await message.answer(text, parse_mode="HTML")

# ─── FOYDALANUVCHI: YORDAM ─────────────────
@router.message(F.text == "ℹ️ Yordam")
async def user_help(message: Message):
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "🎬 Kinolar — barcha kinolarni ko'rish\n"
        "🔍 Qidirish — kino qidirish\n"
        "🔥 Top kinolar — eng ko'p ko'rilganlar\n"
        "🆕 Yangi kinolar — so'nggi qo'shilganlar\n"
        "❤️ Sevimlilar — saqlangan kinolar\n"
        "👤 Profil — shaxsiy ma'lumotlar",
        parse_mode="HTML"
    )

# ─── ADMIN: BROADCAST ──────────────────────
@router.message(F.text == "📢 Broadcast")
async def admin_broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📢 Yubormoqchi bo'lgan xabarni kiriting:", reply_markup=kb_cancel())
    await state.set_state(BroadcastSt.msg)

@router.message(BroadcastSt.msg)
async def admin_broadcast_process(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())

    await state.clear()
    ids = user_all_ids()
    status = await message.answer(f"📢 Yuborilmoqda... 0/{len(ids)}")

    sent, failed = 0, 0
    for i, uid in enumerate(ids):
        try:
            await message.copy_to(uid)
            sent += 1
        except Exception:
            failed += 1
        if i % 25 == 0:
            try:
                await status.edit_text(f"📢 Yuborilmoqda... {i}/{len(ids)}")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    admin_log_add(message.from_user.id, "broadcast", "-", f"sent={sent}, failed={failed}")
    await status.edit_text(f"✅ Yakunlandi!\n✅ Yuborildi: {sent}\n❌ Xato: {failed}", reply_markup=None)
    await message.answer("Admin panel:", reply_markup=kb_admin())

# ─── NOOP ───────────────────────────────────
@router.callback_query(F.data == "noop")
async def noop_cb(call: CallbackQuery):
    await call.answer()

# ══════════════════════════════════════════
#               MAIN
# ══════════════════════════════════════════
async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    log.info("🚀 Bot ishga tushdi")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())  # ✅ Tuzatildi - list with one admin ID
CHANNEL_USERNAME = None    # "@kanalim" yoki None
DB_FILE          = "movies.db"
BOT_NAME         = "🎬 KinoBot"
PER_PAGE         = 6
BACKUP_DIR       = "backups"

# ══════════════════════════════════════════
#                LOGGING
# ══════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════
#              DATABASE
# ══════════════════════════════════════════
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()

    # Eski jadvallarni o'chirish (agar mavjud bo'lsa)
    conn.executescript("""
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS movies;
        DROP TABLE IF EXISTS favorites;
        DROP TABLE IF EXISTS watch_history;
        DROP TABLE IF EXISTS admin_logs;
    """)

    # Yangi jadvallarni yaratish
    conn.executescript("""
        CREATE TABLE users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            full_name  TEXT,
            is_premium INTEGER DEFAULT 0,
            is_banned  INTEGER DEFAULT 0,
            joined_at  TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE movies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            title_uz    TEXT,
            description TEXT,
            year        INTEGER,
            genre       TEXT,
            rating      REAL    DEFAULT 0,
            language    TEXT    DEFAULT 'UZ',
            file_id     TEXT,
            file_type   TEXT    DEFAULT 'video',
            views       INTEGER DEFAULT 0,
            is_premium  INTEGER DEFAULT 0,
            added_by    INTEGER,
            added_at    TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE favorites (
            user_id  INTEGER,
            movie_id INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, movie_id)
        );

        CREATE TABLE watch_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            movie_id   INTEGER,
            watched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE admin_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id   INTEGER,
            action     TEXT,
            target_id  TEXT,
            details    TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    log.info("✅ Database tayyor")

    # Backup papkasini yaratish
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

# ── Users ──
def user_save(uid, username, full_name):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?,?,?)",
        (uid, username, full_name)
    )
    conn.execute(
        "UPDATE users SET username=?, full_name=? WHERE user_id=?",
        (username, full_name, uid)
    )
    conn.commit()
    conn.close()

def user_get(uid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return row

def user_all_ids():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

def user_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return n

def user_set_ban(uid, val):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (val, uid))
    conn.commit()
    conn.close()

def user_set_premium(uid, val):
    conn = get_conn()
    conn.execute("UPDATE users SET is_premium=? WHERE user_id=?", (val, uid))
    conn.commit()
    conn.close()

def user_get_all(limit=100, offset=0):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return rows

def user_get_premium_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users WHERE is_premium=1").fetchone()[0]
    conn.close()
    return n

def user_get_banned_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
    conn.close()
    return n

# ── Movies ──
def movie_insert(title, title_uz, desc, year, genre, rating,
                 lang, file_id, file_type, is_premium, added_by):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO movies
            (title, title_uz, description, year, genre, rating,
             language, file_id, file_type, is_premium, added_by)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (title, title_uz, desc, year, genre, rating,
          lang, file_id, file_type, is_premium, added_by))
    mid = cur.lastrowid
    conn.commit()
    conn.close()

    # Admin logga yozish
    admin_log_add(added_by, "add_movie", str(mid), f"{title} ({title_uz})")
    return mid

def movie_get(mid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM movies WHERE id=?", (mid,)).fetchone()
    conn.close()
    return row

def movie_search(q, limit=10):
    conn = get_conn()
    p = f"%{q}%"
    rows = conn.execute(
        "SELECT * FROM movies WHERE title LIKE ? OR title_uz LIKE ? OR genre LIKE ? "
        "ORDER BY views DESC LIMIT ?",
        (p, p, p, limit)
    ).fetchall()
    conn.close()
    return rows

def movie_list(offset=0, limit=PER_PAGE, genre=None):
    conn = get_conn()
    sql = "SELECT * FROM movies WHERE 1=1"
    params = []
    if genre:
        sql += " AND genre LIKE ?"
        params.append(f"%{genre}%")
    sql += " ORDER BY added_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows

def movie_count(genre=None):
    conn = get_conn()
    if genre:
        n = conn.execute(
            "SELECT COUNT(*) FROM movies WHERE genre LIKE ?", (f"%{genre}%",)
        ).fetchone()[0]
    else:
        n = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    conn.close()
    return n

def movie_inc_views(mid):
    conn = get_conn()
    conn.execute("UPDATE movies SET views=views+1 WHERE id=?", (mid,))
    conn.commit()
    conn.close()

def movie_delete(mid):
    conn = get_conn()
    # Kinoni o'chirishdan oldin ma'lumotni olish
    movie = movie_get(mid)
    conn.execute("DELETE FROM movies WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    if movie:
        return movie
    return None

def movie_top(limit=PER_PAGE):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies ORDER BY views DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows

def movie_new(limit=PER_PAGE):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies ORDER BY added_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows

# Ruxsat etilgan ustunlar - SQL injection oldini olish uchun
ALLOWED_MOVIE_FIELDS = {
    "title", "title_uz", "description", "year", "genre",
    "rating", "language", "is_premium"
}

def movie_update(mid, field, value):
    if field not in ALLOWED_MOVIE_FIELDS:
        raise ValueError(f"Ruxsat etilmagan ustun: {field}")
    conn = get_conn()
    conn.execute(f"UPDATE movies SET {field}=? WHERE id=?", (value, mid))
    conn.commit()
    conn.close()

def movie_get_all(limit=50, offset=0):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies ORDER BY added_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return rows

def movie_get_by_genre(genre):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM movies WHERE genre LIKE ? ORDER BY views DESC",
        (f"%{genre}%",)
    ).fetchall()
    conn.close()
    return rows

def movie_get_stats():
    conn = get_conn()
    stats = conn.execute("""
        SELECT
            COUNT(*) as total_movies,
            SUM(CASE WHEN is_premium=1 THEN 1 ELSE 0 END) as premium_movies,
            SUM(CASE WHEN is_premium=0 THEN 1 ELSE 0 END) as free_movies,
            SUM(views) as total_views,
            AVG(rating) as avg_rating
        FROM movies
    """).fetchone()
    conn.close()
    return stats

# ── Favorites ──
def fav_add(uid, mid):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO favorites (user_id, movie_id) VALUES (?,?)", (uid, mid))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def fav_remove(uid, mid):
    conn = get_conn()
    conn.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?", (uid, mid))
    conn.commit()
    conn.close()

def fav_exists(uid, mid):
    conn = get_conn()
    r = conn.execute(
        "SELECT 1 FROM favorites WHERE user_id=? AND movie_id=?", (uid, mid)
    ).fetchone()
    conn.close()
    return r is not None

def fav_list(uid):
    conn = get_conn()
    rows = conn.execute("""
        SELECT m.* FROM movies m
        JOIN favorites f ON m.id = f.movie_id
        WHERE f.user_id = ?
        ORDER BY f.added_at DESC
    """, (uid,)).fetchall()
    conn.close()
    return rows

def fav_count(uid):
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    return n

# ── History ──
def hist_add(uid, mid):
    conn = get_conn()
    conn.execute(
        "INSERT INTO watch_history (user_id, movie_id) VALUES (?,?)", (uid, mid)
    )
    conn.commit()
    conn.close()

def hist_list(uid, limit=5):
    conn = get_conn()
    rows = conn.execute("""
        SELECT m.* FROM movies m
        JOIN watch_history wh ON m.id = wh.movie_id
        WHERE wh.user_id = ?
        ORDER BY wh.watched_at DESC LIMIT ?
    """, (uid, limit)).fetchall()
    conn.close()
    return rows

def hist_get_stats():
    conn = get_conn()
    stats = conn.execute("""
        SELECT
            COUNT(DISTINCT user_id) as active_users,
            COUNT(*) as total_watches
        FROM watch_history
        WHERE watched_at > datetime('now', '-7 days')
    """).fetchone()
    conn.close()
    return stats

# ── Admin Logs ──
def admin_log_add(admin_id, action, target_id, details):
    conn = get_conn()
    conn.execute(
        "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (?,?,?,?)",
        (admin_id, action, target_id, details)
    )
    conn.commit()
    conn.close()

def admin_log_get(limit=50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM admin_logs
        ORDER BY created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows

# ── Backup ──
def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"movies_backup_{timestamp}.db")

    import shutil
    shutil.copy2(DB_FILE, backup_file)
    return backup_file

def clear_old_backups(days=7):
    import time
    now = time.time()
    for filename in os.listdir(BACKUP_DIR):
        filepath = os.path.join(BACKUP_DIR, filename)
        if os.path.isfile(filepath):
            file_age = now - os.path.getmtime(filepath)
            if file_age > days * 86400:
                os.remove(filepath)

# ══════════════════════════════════════════
#              KEYBOARDS
# ══════════════════════════════════════════
def kb_main():
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="🎬 Kinolar"),      KeyboardButton(text="🔍 Qidirish"))
    kb.row(KeyboardButton(text="🔥 Top kinolar"),  KeyboardButton(text="🆕 Yangi kinolar"))
    kb.row(KeyboardButton(text="❤️ Sevimlilar"),   KeyboardButton(text="👤 Profil"))
    kb.row(KeyboardButton(text="ℹ️ Yordam"))
    return kb.as_markup(resize_keyboard=True)

def kb_admin():
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="✏️ Kinoni tahrirlash"))
    kb.row(KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Foydalanuvchilar"))
    kb.row(KeyboardButton(text="⭐ Premium boshqaruvi"), KeyboardButton(text="🚫 Ban boshqaruvi"))
    kb.row(KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="💾 Backup"))
    kb.row(KeyboardButton(text="📜 Admin loglar"), KeyboardButton(text="🎭 Janrlar ro'yxati"))
    kb.row(KeyboardButton(text="🏠 Bosh menyu"))
    return kb.as_markup(resize_keyboard=True)

def kb_admin_users():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="admin_list_users"))
    kb.row(InlineKeyboardButton(text="⭐ Premium foydalanuvchilar", callback_data="admin_list_premium"))
    kb.row(InlineKeyboardButton(text="🚫 Banlangan foydalanuvchilar", callback_data="admin_list_banned"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return kb.as_markup()

def kb_admin_premium():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Premium berish", callback_data="admin_add_premium"))
    kb.row(InlineKeyboardButton(text="➖ Premium olish", callback_data="admin_remove_premium"))
    kb.row(InlineKeyboardButton(text="📋 Premiumlar ro'yxati", callback_data="admin_list_premium"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return kb.as_markup()

def kb_admin_ban():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🚫 Ban qilish", callback_data="admin_ban_user"))
    kb.row(InlineKeyboardButton(text="✅ Ban bekor qilish", callback_data="admin_unban_user"))
    kb.row(InlineKeyboardButton(text="📋 Banlanganlar", callback_data="admin_list_banned"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return kb.as_markup()

def kb_user_list(users, page, total_pages):
    b = InlineKeyboardBuilder()
    for u in users[:PER_PAGE]:
        premium_icon = "⭐" if u["is_premium"] else "🆓"
        ban_icon = "🚫" if u["is_banned"] else "✅"
        text = f"{ban_icon} {premium_icon} {u['full_name'][:20]}"
        b.row(InlineKeyboardButton(text=text, callback_data=f"admin_user_{u['user_id']}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_users_page_{page+1}"))
    if nav:
        b.row(*nav)

    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return b.as_markup()

def kb_user_actions(user_id, is_banned, is_premium):
    b = InlineKeyboardBuilder()
    if not is_banned:
        b.row(InlineKeyboardButton(text="🚫 Ban qilish", callback_data=f"admin_ban_{user_id}"))
    else:
        b.row(InlineKeyboardButton(text="✅ Ban bekor qilish", callback_data=f"admin_unban_{user_id}"))

    if not is_premium:
        b.row(InlineKeyboardButton(text="⭐ Premium berish", callback_data=f"admin_premium_add_{user_id}"))
    else:
        b.row(InlineKeyboardButton(text="⭐ Premium olish", callback_data=f"admin_premium_rem_{user_id}"))

    b.row(InlineKeyboardButton(text="📊 Statistika", callback_data=f"admin_user_stats_{user_id}"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_list_users"))
    return b.as_markup()

def kb_movie_list_admin(movies, page, total_pages):
    b = InlineKeyboardBuilder()
    for m in movies[:PER_PAGE]:
        icon = "⭐" if m["is_premium"] else "🆓"
        title = m["title_uz"] or m["title"]
        b.row(InlineKeyboardButton(
            text=f"{icon} {title[:30]}",
            callback_data=f"admin_movie_{m['id']}"
        ))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_movies_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_movies_page_{page+1}"))
    if nav:
        b.row(*nav)

    b.row(InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="admin_add_movie"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return b.as_markup()

def kb_movie_actions(movie_id):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"admin_edit_movie_{movie_id}"))
    b.row(InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin_del_movie_{movie_id}"))
    b.row(InlineKeyboardButton(text="📊 Statistikani ko'rish", callback_data=f"admin_movie_stats_{movie_id}"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_movies_list"))
    return b.as_markup()

def kb_edit_movie_options(movie_id):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📝 Nomi", callback_data=f"edit_title_{movie_id}"))
    b.row(InlineKeyboardButton(text="📝 O'zbekcha nomi", callback_data=f"edit_title_uz_{movie_id}"))
    b.row(InlineKeyboardButton(text="📖 Tavsif", callback_data=f"edit_desc_{movie_id}"))
    b.row(InlineKeyboardButton(text="📅 Yil", callback_data=f"edit_year_{movie_id}"))
    b.row(InlineKeyboardButton(text="🎭 Janr", callback_data=f"edit_genre_{movie_id}"))
    b.row(InlineKeyboardButton(text="⭐ Reyting", callback_data=f"edit_rating_{movie_id}"))
    b.row(InlineKeyboardButton(text="🌍 Til", callback_data=f"edit_lang_{movie_id}"))
    b.row(InlineKeyboardButton(text="💎 Premium", callback_data=f"edit_premium_{movie_id}"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_movie_{movie_id}"))
    return b.as_markup()

def kb_cancel():
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="❌ Bekor qilish"))
    return kb.as_markup(resize_keyboard=True)

def kb_movie(mid, is_fav=False, is_premium=False):
    b = InlineKeyboardBuilder()
    fav_text = "💔 Sevimlilardan o'chirish" if is_fav else "❤️ Sevimlilarga qo'shish"
    b.row(InlineKeyboardButton(text=fav_text, callback_data=f"fav_{mid}"))
    watch_text = "⭐ Premium — Ko'rish" if is_premium else "▶️ Ko'rish"
    b.row(InlineKeyboardButton(text=watch_text, callback_data=f"watch_{mid}"))
    b.row(InlineKeyboardButton(text="📤 Ulashish", switch_inline_query=str(mid)))
    return b.as_markup()

def kb_movie_list(movies, page, total_pages, genre=""):
    b = InlineKeyboardBuilder()
    for m in movies:
        icon  = "⭐" if m["is_premium"] else "🆓"
        title = m["title_uz"] or m["title"]
        b.row(InlineKeyboardButton(
            text=f"{icon} {title} [{m['language'] or 'UZ'}]",
            callback_data=f"movie_{m['id']}"
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{page-1}_{genre}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}_{genre}"))
    if nav:
        b.row(*nav)
    return b.as_markup()

def kb_confirm(action, item_id):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Ha",   callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_cb")
    )
    return b.as_markup()

def kb_lang():
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇺🇿 O'zbek",  callback_data="lang_UZ"),
        InlineKeyboardButton(text="🇷🇺 Rus",      callback_data="lang_RU"),
        InlineKeyboardButton(text="🌍 Barchasi",  callback_data="lang_ALL"),
    )
    return b.as_markup()

def kb_sub(channel):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="📢 Kanalga o'tish",
        url=f"https://t.me/{channel.lstrip('@')}"
    ))
    b.row(InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="check_sub"))
    return b.as_markup()

def kb_genres(genres):
    b = InlineKeyboardBuilder()
    for genre in genres[:12]:
        b.row(InlineKeyboardButton(text=f"🎭 {genre}", callback_data=f"genre_{genre}"))
    b.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu"))
    return b.as_markup()

# ══════════════════════════════════════════
#              HELPERS
# ══════════════════════════════════════════
def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

async def check_sub(bot: Bot, uid: int) -> bool:
    if not CHANNEL_USERNAME:
        return True
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status not in ("left", "kicked", "banned")
    except Exception:
        return True

def fmt_movie(m) -> str:
    premium = "⭐ Premium" if m["is_premium"] else "🆓 Bepul"
    stars   = "⭐" * int(m["rating"] or 0)
    title   = m["title"]
    text    = f"🎬 <b>{title}</b>\n"
    if m["title_uz"] and m["title_uz"] != title:
        text += f"📝 <i>{m['title_uz']}</i>\n"
    text += (
        f"\n📅 Yil: <b>{m['year'] or '—'}</b>"
        f"\n🎭 Janr: <b>{m['genre'] or '—'}</b>"
        f"\n🌍 Til: <b>{m['language'] or 'UZ'}</b>"
        f"\n⭐ Reyting: <b>{m['rating'] or '—'}</b> {stars}"
        f"\n💎 Tur: <b>{premium}</b>"
        f"\n👁 Ko'rildi: <b>{m['views'] or 0}</b> marta"
        f"\n\n📖 <i>{m['description'] or 'Tavsif yoq'}</i>"
    )
    return text

def get_all_genres():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT genre FROM movies WHERE genre IS NOT NULL AND genre != ''").fetchall()
    conn.close()
    genres = set()
    for row in rows:
        if row["genre"]:
            for g in row["genre"].split(","):
                genres.add(g.strip())
    return sorted(list(genres))

# ══════════════════════════════════════════
#               FSM STATES
# ══════════════════════════════════════════
class AddMovie(StatesGroup):
    title       = State()
    title_uz    = State()
    description = State()
    year        = State()
    genre       = State()
    rating      = State()
    language    = State()
    file        = State()
    premium     = State()

class EditMovie(StatesGroup):
    field = State()
    value = State()

class SearchSt(StatesGroup):
    query = State()

class BroadcastSt(StatesGroup):
    msg = State()

class AdminAddPremium(StatesGroup):
    user_id = State()

class AdminRemovePremium(StatesGroup):
    user_id = State()

class AdminBanUser(StatesGroup):
    user_id = State()

class AdminUnbanUser(StatesGroup):
    user_id = State()

# ══════════════════════════════════════════
#               HANDLERS
# ══════════════════════════════════════════
router = Router()

# ─── /start ───────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    u = message.from_user
    user_save(u.id, u.username or "", u.full_name or "")

    if CHANNEL_USERNAME and not await check_sub(bot, u.id):
        await message.answer(
            f"👋 Salom, <b>{u.first_name}</b>!\n\n"
            f"⚠️ Botdan foydalanish uchun avval kanalga a'zo bo'ling:",
            reply_markup=kb_sub(CHANNEL_USERNAME),
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"👋 Salom, <b>{u.first_name}</b>!\n\n"
        f"🎬 <b>{BOT_NAME}</b> ga xush kelibsiz!\n\n"
        f"• Kinolar ko'ring\n"
        f"• 🔍 Qidiring\n"
        f"• ❤️ Sevimlilarga saqlang",
        reply_markup=kb_main(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "check_sub")
async def on_check_sub(call: CallbackQuery, bot: Bot):
    if await check_sub(bot, call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Xush kelibsiz!", reply_markup=kb_main())
    else:
        await call.answer("❌ Hali a'zo bo'lmadingiz!", show_alert=True)

# ─── /admin ───────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Ruxsat yo'q!")

    stats = movie_get_stats()
    user_stats = hist_get_stats()
    avg_rating = stats['avg_rating'] if stats['avg_rating'] is not None else 0.0

    await message.answer(
        f"🔐 <b>Admin Panel</b>\n\n"
        f"📊 <b>Umumiy statistika:</b>\n"
        f"👥 Foydalanuvchilar: <b>{user_count()}</b>\n"
        f"⭐ Premium foydalanuvchilar: <b>{user_get_premium_count()}</b>\n"
        f"🚫 Banlanganlar: <b>{user_get_banned_count()}</b>\n\n"
        f"🎬 <b>Kinolar:</b>\n"
        f"Jami kinolar: <b>{stats['total_movies']}</b>\n"
        f"⭐ Premium kinolar: <b>{stats['premium_movies'] or 0}</b>\n"
        f"🆓 Bepul kinolar: <b>{stats['free_movies'] or 0}</b>\n"
        f"👁 Jami ko'rishlar: <b>{stats['total_views'] or 0}</b>\n"
        f"⭐ O'rtacha reyting: <b>{avg_rating:.1f}</b>\n\n"
        f"📈 <b>Faollik (7 kun):</b>\n"
        f"Aktiv foydalanuvchilar: <b>{user_stats['active_users'] or 0}</b>\n"
        f"Jami ko'rishlar: <b>{user_stats['total_watches'] or 0}</b>",
        reply_markup=kb_admin(),
        parse_mode="HTML"
    )

@router.message(F.text == "🏠 Bosh menyu")
async def go_home(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await message.answer("🏠 Bosh menyu:", reply_markup=kb_admin())
    else:
        await message.answer("🏠 Bosh menyu:", reply_markup=kb_main())

# ─── ADMIN: FOYDALANUVCHILAR ──────────────
@router.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "👥 <b>Foydalanuvchilar boshqaruvi</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=kb_admin_users(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_list_users")
async def admin_list_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    users = user_get_all(limit=100)
    if not users:
        return await call.message.edit_text("❌ Foydalanuvchilar topilmadi!")

    total_pages = max(1, math.ceil(len(users) / PER_PAGE))
    await call.message.edit_text(
        f"👥 <b>Barcha foydalanuvchilar</b> ({len(users)} ta):",
        reply_markup=kb_user_list(users, 0, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_users_page_"))
async def admin_users_page(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    page = int(call.data.split("_")[3])
    users = user_get_all(limit=100)
    total_pages = max(1, math.ceil(len(users) / PER_PAGE))

    start = page * PER_PAGE
    end = start + PER_PAGE
    page_users = users[start:end]

    await call.message.edit_reply_markup(
        reply_markup=kb_user_list(page_users, page, total_pages)
    )

@router.callback_query(F.data.startswith("admin_user_"), F.data.regexp(r"^admin_user_\d+$"))
async def admin_user_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[2])
    user = user_get(user_id)

    if not user:
        return await call.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)

    fav_count_val = fav_count(user_id)

    text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Ism: <b>{user['full_name']}</b>\n"
        f"📝 Username: @{user['username'] if user['username'] else '—'}\n"
        f"⭐ Premium: {'✅ Ha' if user['is_premium'] else '❌ Yoq'}\n"
        f"🚫 Ban: {'✅ Ha' if user['is_banned'] else '❌ Yoq'}\n"
        f"❤️ Sevimlilar: <b>{fav_count_val}</b> ta\n"
        f"📅 Qo'shilgan: <b>{user['joined_at']}</b>"
    )

    await call.message.edit_text(
        text,
        reply_markup=kb_user_actions(user_id, user['is_banned'], user['is_premium']),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_user_stats_"))
async def admin_user_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[3])
    history = hist_list(user_id, limit=10)
    favs = fav_list(user_id)

    text = (
        f"📊 <b>Foydalanuvchi statistikasi</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"❤️ Sevimlilar: <b>{len(favs)}</b> ta\n"
        f"📺 Ko'rilgan kinolar: <b>{len(history)}</b> ta (oxirgi 10 ta)\n\n"
    )

    if history:
        text += "<b>📽 Oxirgi ko'rilganlar:</b>\n"
        for h in history[:5]:
            text += f"• {h['title_uz'] or h['title']}\n"

    await call.message.edit_text(text, parse_mode="HTML")
    await asyncio.sleep(3)
    await admin_user_detail(call)

# ─── ADMIN: PREMIUM BOSHQARUVI ────────────
@router.message(F.text == "⭐ Premium boshqaruvi")
async def admin_premium(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "⭐ <b>Premium boshqaruvi</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=kb_admin_premium(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_add_premium")
async def admin_add_premium_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    await call.message.edit_text(
        "⭐ <b>Premium berish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "Masalan: <code>123456789</code>",
        parse_mode="HTML"
    )
    await state.set_state(AdminAddPremium.user_id)

@router.message(AdminAddPremium.user_id)
async def admin_add_premium_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Noto'g'ri ID! Iltimos, raqam kiriting.")

    user = user_get(user_id)
    if not user:
        return await message.answer(f"❌ ID {user_id} li foydalanuvchi topilmadi!")

    if user["is_premium"]:
        return await message.answer(f"❌ {user['full_name']} allaqachon premium!")

    user_set_premium(user_id, 1)
    admin_log_add(message.from_user.id, "add_premium", str(user_id), user['full_name'])

    await message.answer(f"✅ {user['full_name']} ga premium berildi!")
    await state.clear()

@router.callback_query(F.data == "admin_remove_premium")
async def admin_remove_premium_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    await call.message.edit_text(
        "⭐ <b>Premium olish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(AdminRemovePremium.user_id)

@router.message(AdminRemovePremium.user_id)
async def admin_remove_premium_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Noto'g'ri ID!")

    user = user_get(user_id)
    if not user:
        return await message.answer(f"❌ ID {user_id} li foydalanuvchi topilmadi!")

    if not user["is_premium"]:
        return await message.answer(f"❌ {user['full_name']} premium emas!")

    user_set_premium(user_id, 0)
    admin_log_add(message.from_user.id, "remove_premium", str(user_id), user['full_name'])

    await message.answer(f"✅ {user['full_name']} dan premium olib tashlandi!")
    await state.clear()

@router.callback_query(F.data.startswith("admin_premium_add_"))
async def admin_premium_add_from_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[3])
    user = user_get(user_id)

    if user["is_premium"]:
        return await call.answer("❌ Foydalanuvchi allaqachon premium!", show_alert=True)

    user_set_premium(user_id, 1)
    admin_log_add(call.from_user.id, "add_premium", str(user_id), user['full_name'])
    await call.answer(f"✅ {user['full_name']} ga premium berildi!")
    await admin_user_detail(call)

@router.callback_query(F.data.startswith("admin_premium_rem_"))
async def admin_premium_remove_from_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[3])
    user = user_get(user_id)

    if not user["is_premium"]:
        return await call.answer("❌ Foydalanuvchi premium emas!", show_alert=True)

    user_set_premium(user_id, 0)
    admin_log_add(call.from_user.id, "remove_premium", str(user_id), user['full_name'])
    await call.answer(f"✅ {user['full_name']} dan premium olib tashlandi!")
    await admin_user_detail(call)

# ─── ADMIN: BAN BOSHQARUVI ────────────────
@router.message(F.text == "🚫 Ban boshqaruvi")
async def admin_ban(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🚫 <b>Ban boshqaruvi</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=kb_admin_ban(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_ban_user")
async def admin_ban_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    await call.message.edit_text(
        "🚫 <b>Ban qilish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(AdminBanUser.user_id)

@router.message(AdminBanUser.user_id)
async def admin_ban_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Noto'g'ri ID!")

    if user_id in ADMIN_IDS:
        return await message.answer("❌ Adminni ban qilib bo'lmaydi!")

    user = user_get(user_id)
    if not user:
        return await message.answer(f"❌ ID {user_id} li foydalanuvchi topilmadi!")

    if user["is_banned"]:
        return await message.answer(f"❌ {user['full_name']} allaqachon banlangan!")

    user_set_ban(user_id, 1)
    admin_log_add(message.from_user.id, "ban_user", str(user_id), user['full_name'])

    await message.answer(f"✅ {user['full_name']} ban qilindi!")
    await state.clear()

@router.callback_query(F.data == "admin_unban_user")
async def admin_unban_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    await call.message.edit_text(
        "✅ <b>Ban bekor qilish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(AdminUnbanUser.user_id)

@router.message(AdminUnbanUser.user_id)
async def admin_unban_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Noto'g'ri ID!")

    user = user_get(user_id)
    if not user:
        return await message.answer(f"❌ ID {user_id} li foydalanuvchi topilmadi!")

    if not user["is_banned"]:
        return await message.answer(f"❌ {user['full_name']} banlanmagan!")

    user_set_ban(user_id, 0)
    admin_log_add(message.from_user.id, "unban_user", str(user_id), user['full_name'])

    await message.answer(f"✅ {user['full_name']} ning bani olib tashlandi!")
    await state.clear()

@router.callback_query(F.data.startswith("admin_ban_"), F.data.regexp(r"^admin_ban_\d+$"))
async def admin_ban_from_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[2])

    if user_id in ADMIN_IDS:
        return await call.answer("❌ Adminni ban qilib bo'lmaydi!", show_alert=True)

    user = user_get(user_id)
    if user["is_banned"]:
        return await call.answer("❌ Foydalanuvchi allaqachon banlangan!", show_alert=True)

    user_set_ban(user_id, 1)
    admin_log_add(call.from_user.id, "ban_user", str(user_id), user['full_name'])
    await call.answer(f"✅ {user['full_name']} ban qilindi!")
    await admin_user_detail(call)

@router.callback_query(F.data.startswith("admin_unban_"), F.data.regexp(r"^admin_unban_\d+$"))
async def admin_unban_from_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    user_id = int(call.data.split("_")[2])
    user = user_get(user_id)

    if not user["is_banned"]:
        return await call.answer("❌ Foydalanuvchi banlanmagan!", show_alert=True)

    user_set_ban(user_id, 0)
    admin_log_add(call.from_user.id, "unban_user", str(user_id), user['full_name'])
    await call.answer(f"✅ {user['full_name']} ning bani olib tashlandi!")
    await admin_user_detail(call)

@router.callback_query(F.data == "admin_list_banned")
async def admin_list_banned(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    conn = get_conn()
    users = conn.execute("SELECT * FROM users WHERE is_banned=1").fetchall()
    conn.close()

    if not users:
        return await call.message.edit_text("✅ Banlangan foydalanuvchilar yo'q!")

    text = "🚫 <b>Banlangan foydalanuvchilar:</b>\n\n"
    for u in users:
        text += f"🆔 <code>{u['user_id']}</code> — {u['full_name']}\n"

    await call.message.edit_text(text, parse_mode="HTML")

@router.callback_query(F.data == "admin_list_premium")
async def admin_list_premium(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    conn = get_conn()
    users = conn.execute("SELECT * FROM users WHERE is_premium=1").fetchall()
    conn.close()

    if not users:
        return await call.message.edit_text("⭐ Premium foydalanuvchilar yo'q!")

    text = "⭐ <b>Premium foydalanuvchilar:</b>\n\n"
    for u in users:
        text += f"🆔 <code>{u['user_id']}</code> — {u['full_name']}\n"

    await call.message.edit_text(text, parse_mode="HTML")

# ─── ADMIN: KINOLAR BOSHQARUVI ────────────
@router.message(F.text == "✏️ Kinoni tahrirlash")
async def admin_movies_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    movies = movie_get_all(limit=50)
    if not movies:
        return await message.answer("❌ Hozircha kinolar yo'q!")

    total_pages = max(1, math.ceil(len(movies) / PER_PAGE))
    await message.answer(
        "✏️ <b>Kinoni tahrirlash</b>\n\n"
        "Tahrirlamoqchi bo'lgan kinoni tanlang:",
        reply_markup=kb_movie_list_admin(movies, 0, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_movies_list")
async def admin_movies_list_cb(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movies = movie_get_all(limit=50)
    if not movies:
        return await call.message.edit_text("❌ Hozircha kinolar yo'q!")

    total_pages = max(1, math.ceil(len(movies) / PER_PAGE))
    await call.message.edit_text(
        "✏️ <b>Kinoni tahrirlash</b>\n\n"
        "Tahrirlamoqchi bo'lgan kinoni tanlang:",
        reply_markup=kb_movie_list_admin(movies, 0, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_movies_page_"))
async def admin_movies_page(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    page = int(call.data.split("_")[3])
    movies = movie_get_all(limit=50)
    total_pages = max(1, math.ceil(len(movies) / PER_PAGE))

    start = page * PER_PAGE
    end = start + PER_PAGE
    page_movies = movies[start:end]

    await call.message.edit_reply_markup(
        reply_markup=kb_movie_list_admin(page_movies, page, total_pages)
    )

@router.callback_query(F.data.startswith("admin_movie_"), F.data.regexp(r"^admin_movie_\d+$"))
async def admin_movie_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[2])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    await call.message.edit_text(
        fmt_movie(movie),
        reply_markup=kb_movie_actions(movie_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_edit_movie_"))
async def admin_edit_movie_start(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[3])
    await call.message.edit_text(
        "✏️ <b>Kinoni tahrirlash</b>\n\n"
        "Qaysi ma'lumotni o'zgartirmoqchisiz?",
        reply_markup=kb_edit_movie_options(movie_id),
        parse_mode="HTML"
    )

# Kino tahrirlash uchun handlerlar
edit_fields = {
    "edit_title_uz_": "title_uz",
    "edit_title_": "title",
    "edit_desc_": "description",
    "edit_year_": "year",
    "edit_genre_": "genre",
    "edit_rating_": "rating",
    "edit_lang_": "language",
    "edit_premium_": "is_premium"
}

@router.callback_query(F.data.startswith(tuple(edit_fields.keys())))
async def admin_edit_field_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    for prefix, field in edit_fields.items():
        if call.data.startswith(prefix):
            movie_id = int(call.data.replace(prefix, ""))
            await state.update_data(movie_id=movie_id, field=field)

            prompts = {
                "title": "Yangi nomini kiriting:",
                "title_uz": "Yangi o'zbekcha nomini kiriting:",
                "description": "Yangi tavsifini kiriting:",
                "year": "Yangi yilini kiriting (masalan: 2024):",
                "genre": "Yangi janrini kiriting:",
                "rating": "Yangi reytingini kiriting (0-10):",
                "language": "Yangi tilini kiriting (UZ, RU, EN):",
                "is_premium": "Premium kinomi? (ha/yo'q):"
            }

            await call.message.edit_text(prompts[field])
            await state.set_state(EditMovie.value)
            break

@router.message(EditMovie.value)
async def admin_edit_field_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    movie_id = data["movie_id"]
    field = data["field"]
    value = message.text.strip()

    if field == "year":
        if not value.isdigit():
            return await message.answer("❌ Yil raqam bo'lishi kerak!")
        value = int(value)
    elif field == "rating":
        try:
            value = float(value.replace(",", "."))
            value = max(0.0, min(10.0, value))
        except ValueError:
            return await message.answer("❌ Reyting 0-10 oralig'ida bo'lishi kerak!")
    elif field == "is_premium":
        value = 1 if value.lower() in ["ha", "yes", "1", "true"] else 0

    movie_update(movie_id, field, value)
    admin_log_add(message.from_user.id, f"edit_movie_{field}", str(movie_id), str(value))

    await message.answer(f"✅ {field} muvaffaqiyatli o'zgartirildi!", reply_markup=kb_admin())
    await state.clear()

@router.callback_query(F.data.startswith("admin_del_movie_"))
async def admin_del_movie_confirm(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[3])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    await call.message.edit_text(
        f"🗑 <b>{movie['title_uz'] or movie['title']}</b> kinosini o'chirishni tasdiqlaysizmi?",
        reply_markup=kb_confirm("del_movie", movie_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("confirm_del_movie_"))
async def admin_del_movie_execute(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[3])
    movie = movie_delete(movie_id)

    if movie:
        admin_log_add(call.from_user.id, "delete_movie", str(movie_id), movie['title'])
        await call.message.edit_text(f"✅ <b>{movie['title_uz'] or movie['title']}</b> o'chirildi!", parse_mode="HTML")
    else:
        await call.message.edit_text("❌ Kino topilmadi!")

@router.callback_query(F.data.startswith("admin_movie_stats_"))
async def admin_movie_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    movie_id = int(call.data.split("_")[3])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    conn = get_conn()
    fav_count_val = conn.execute(
        "SELECT COUNT(*) FROM favorites WHERE movie_id=?", (movie_id,)
    ).fetchone()[0]
    hist_count = conn.execute(
        "SELECT COUNT(*) FROM watch_history WHERE movie_id=?", (movie_id,)
    ).fetchone()[0]
    conn.close()

    text = (
        f"📊 <b>Kino statistikasi</b>\n\n"
        f"🎬 Nomi: <b>{movie['title_uz'] or movie['title']}</b>\n"
        f"👁 Ko'rishlar: <b>{movie['views']}</b>\n"
        f"❤️ Sevimlilarga qo'shilgan: <b>{fav_count_val}</b>\n"
        f"📺 Ko'rilganlar: <b>{hist_count}</b>\n"
        f"⭐ Reyting: <b>{movie['rating']}</b>\n"
        f"💎 Tur: <b>{'Premium' if movie['is_premium'] else 'Bepul'}</b>"
    )

    await call.message.edit_text(text, parse_mode="HTML")
    await asyncio.sleep(3)
    await admin_movie_detail(call)

# ─── ADMIN: BACKUP ────────────────────────
@router.message(F.text == "💾 Backup")
async def admin_backup(message: Message):
    if not is_admin(message.from_user.id):
        return

    status_msg = await message.answer("💾 <b>Backup yaratilmoqda...</b>", parse_mode="HTML")

    try:
        backup_file = backup_database()
        clear_old_backups(days=7)

        await status_msg.delete()

        # Faylni yuborish
        await message.answer_document(
            document=FSInputFile(backup_file),
            caption=f"✅ <b>Backup yaratildi!</b>\n\n"
                   f"📅 Sana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                   f"💾 Fayl hajmi: {os.path.getsize(backup_file) / 1024:.2f} KB",
            parse_mode="HTML"
        )

        admin_log_add(message.from_user.id, "backup", backup_file, "Database backup created")

    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik: {str(e)}")

# ─── ADMIN: LOGLAR ────────────────────────
@router.message(F.text == "📜 Admin loglar")
async def admin_logs(message: Message):
    if not is_admin(message.from_user.id):
        return

    logs = admin_log_get(limit=30)
    if not logs:
        return await message.answer("📜 Hech qanday log yo'q!")

    text = "📜 <b>Admin loglari (oxirgi 30 ta):</b>\n\n"
    for log_entry in logs:
        text += f"🕒 {log_entry['created_at']}\n"
        text += f"👤 Admin: <code>{log_entry['admin_id']}</code>\n"
        text += f"📝 Amal: <b>{log_entry['action']}</b>\n"
        text += f"🎯 Target: <code>{log_entry['target_id']}</code>\n"
        text += f"📄 Detail: {(log_entry['details'] or '')[:50]}\n"
        text += "─" * 30 + "\n"

    # Agar xabar juda uzun bo'lsa, qismlarga bo'lib yuborish
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

# ─── ADMIN: JANRLAR RO'YXATI ──────────────
@router.message(F.text == "🎭 Janrlar ro'yxati")
async def admin_genres(message: Message):
    if not is_admin(message.from_user.id):
        return

    genres = get_all_genres()
    if not genres:
        return await message.answer("❌ Hech qanday janr topilmadi!")

    text = "🎭 <b>Barcha janrlar:</b>\n\n"
    for i, genre in enumerate(genres, 1):
        # Janrdagi kinolar sonini olish
        count = movie_count(genre=genre)
        text += f"{i}. {genre} — <b>{count}</b> ta kino\n"

    await message.answer(text, parse_mode="HTML")

# ─── ADMIN: STATISTIKA ────────────────────
@router.message(F.text == "📊 Statistika")
async def admin_stats_btn(message: Message):
    if not is_admin(message.from_user.id):
        return
    await cmd_admin(message)

# ─── ADMIN: ORQAGA ────────────────────────
@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)

    stats = movie_get_stats()
    user_stats = hist_get_stats()
    avg_rating = stats['avg_rating'] if stats['avg_rating'] is not None else 0.0

    await call.message.edit_text(
        f"🔐 <b>Admin Panel</b>\n\n"
        f"📊 <b>Umumiy statistika:</b>\n"
        f"👥 Foydalanuvchilar: <b>{user_count()}</b>\n"
        f"⭐ Premium foydalanuvchilar: <b>{user_get_premium_count()}</b>\n"
        f"🚫 Banlanganlar: <b>{user_get_banned_count()}</b>\n\n"
        f"🎬 <b>Kinolar:</b>\n"
        f"Jami kinolar: <b>{stats['total_movies']}</b>\n"
        f"⭐ Premium kinolar: <b>{stats['premium_movies'] or 0}</b>\n"
        f"🆓 Bepul kinolar: <b>{stats['free_movies'] or 0}</b>\n"
        f"👁 Jami ko'rishlar: <b>{stats['total_views'] or 0}</b>\n"
        f"⭐ O'rtacha reyting: <b>{avg_rating:.1f}</b>\n\n"
        f"📈 <b>Faollik (7 kun):</b>\n"
        f"Aktiv foydalanuvchilar: <b>{user_stats['active_users'] or 0}</b>\n"
        f"Jami ko'rishlar: <b>{user_stats['total_watches'] or 0}</b>",
        parse_mode="HTML"
    )

# ─── KINO QO'SHISH ────────────────────────
@router.message(F.text == "➕ Kino qo'shish")
async def add_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🎬 Kino nomini kiriting (inglizcha):", reply_markup=kb_cancel())
    await state.set_state(AddMovie.title)

@router.callback_query(F.data == "admin_add_movie")
async def add_start_cb(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
    await call.message.answer("🎬 Kino nomini kiriting (inglizcha):", reply_markup=kb_cancel())
    await state.set_state(AddMovie.title)

@router.message(AddMovie.title)
async def add_title(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    await state.update_data(title=message.text.strip())
    await message.answer("📝 O'zbekcha nomini kiriting:")
    await state.set_state(AddMovie.title_uz)

@router.message(AddMovie.title_uz)
async def add_title_uz(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    await state.update_data(title_uz=message.text.strip())
    await message.answer("📖 Tavsifini kiriting:")
    await state.set_state(AddMovie.description)

@router.message(AddMovie.description)
async def add_desc(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    await state.update_data(description=message.text.strip())
    await message.answer("📅 Yilini kiriting (masalan: 2024):")
    await state.set_state(AddMovie.year)

@router.message(AddMovie.year)
async def add_year(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    if not message.text.isdigit():
        return await message.answer("❌ Faqat raqam kiriting! Masalan: 2024")
    await state.update_data(year=int(message.text))
    await message.answer("🎭 Janrini kiriting (Aksion, Drama, Komediya...):")
    await state.set_state(AddMovie.genre)

@router.message(AddMovie.genre)
async def add_genre(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    await state.update_data(genre=message.text.strip())
    await message.answer("⭐ Reytingini kiriting (0-10, masalan: 8.5):")
    await state.set_state(AddMovie.rating)

@router.message(AddMovie.rating)
async def add_rating(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    try:
        rating = float(message.text.replace(",", "."))
        rating = max(0.0, min(10.0, rating))
    except ValueError:
        return await message.answer("❌ Raqam kiriting! Masalan: 8.5")
    await state.update_data(rating=rating)
    await message.answer("🌍 Tilini tanlang:", reply_markup=kb_lang())
    await state.set_state(AddMovie.language)

@router.callback_query(AddMovie.language, F.data.startswith("lang_"))
async def add_lang(call: CallbackQuery, state: FSMContext):
    lang = call.data.replace("lang_", "")
    await state.update_data(language=lang)
    await call.message.edit_text("🎬 Kino faylini yuboring (video yoki hujjat):")
    await state.set_state(AddMovie.file)

@router.message(AddMovie.file)
async def add_file(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())
    if message.video:
        await state.update_data(file_id=message.video.file_id, file_type="video")
    elif message.document:
        await state.update_data(file_id=message.document.file_id, file_type="document")
    else:
        return await message.answer("❌ Iltimos, video yoki hujjat yuboring!")
    await message.answer("💎 Bu premium kino bo'lsinmi?", reply_markup=kb_confirm("premium", 1))
    await state.set_state(AddMovie.premium)

@router.callback_query(AddMovie.premium, F.data.startswith("confirm_premium_"))
async def add_premium_yes(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    mid = movie_insert(
        data.get("title", ""), data.get("title_uz", ""),
        data.get("description", ""), data.get("year", 0),
        data.get("genre", ""), data.get("rating", 0.0),
        data.get("language", "UZ"), data.get("file_id", ""),
        data.get("file_type", "video"), 1, call.from_user.id
    )
    await call.message.edit_text(
        f"✅ <b>Premium kino</b> qo'shildi!\n🆔 ID: <code>{mid}</code>",
        parse_mode="HTML"
    )
    await call.message.answer("Admin panel:", reply_markup=kb_admin())

@router.callback_query(AddMovie.premium, F.data == "cancel_cb")
async def add_premium_no(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    mid = movie_insert(
        data.get("title", ""), data.get("title_uz", ""),
        data.get("description", ""), data.get("year", 0),
        data.get("genre", ""), data.get("rating", 0.0),
        data.get("language", "UZ"), data.get("file_id", ""),
        data.get("file_type", "video"), 0, call.from_user.id
    )
    await call.message.edit_text(
        f"✅ <b>Bepul kino</b> qo'shildi!\n🆔 ID: <code>{mid}</code>",
        parse_mode="HTML"
    )
    await call.message.answer("Admin panel:", reply_markup=kb_admin())

# ─── FOYDALANUVCHI: KINOLAR RO'YXATI ──────
@router.message(F.text == "🎬 Kinolar")
async def user_movies(message: Message):
    movies = movie_list(offset=0, limit=PER_PAGE)
    if not movies:
        return await message.answer("❌ Hozircha kinolar yo'q!")

    total = movie_count()
    total_pages = max(1, math.ceil(total / PER_PAGE))
    await message.answer(
        "🎬 <b>Barcha kinolar:</b>",
        reply_markup=kb_movie_list(movies, 0, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("page_"))
async def user_movies_page(call: CallbackQuery):
    parts = call.data.split("_", 2)
    page = int(parts[1])
    genre = parts[2] if len(parts) > 2 and parts[2] else None

    movies = movie_list(offset=page * PER_PAGE, limit=PER_PAGE, genre=genre)
    total = movie_count(genre=genre)
    total_pages = max(1, math.ceil(total / PER_PAGE))

    await call.message.edit_reply_markup(
        reply_markup=kb_movie_list(movies, page, total_pages, genre or "")
    )

@router.callback_query(F.data.startswith("movie_"))
async def user_movie_detail(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    is_fav = fav_exists(call.from_user.id, movie_id)
    await call.message.answer(
        fmt_movie(movie),
        reply_markup=kb_movie(movie_id, is_fav, bool(movie["is_premium"])),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("watch_"))
async def user_watch_movie(call: CallbackQuery, bot: Bot):
    movie_id = int(call.data.split("_")[1])
    movie = movie_get(movie_id)

    if not movie:
        return await call.answer("❌ Kino topilmadi!", show_alert=True)

    user = user_get(call.from_user.id)
    if movie["is_premium"] and not (user and user["is_premium"]):
        return await call.answer("⭐ Bu kino faqat premium foydalanuvchilar uchun!", show_alert=True)

    movie_inc_views(movie_id)
    hist_add(call.from_user.id, movie_id)

    if movie["file_type"] == "video":
        await bot.send_video(call.from_user.id, movie["file_id"], caption=movie["title_uz"] or movie["title"])
    else:
        await bot.send_document(call.from_user.id, movie["file_id"], caption=movie["title_uz"] or movie["title"])
    await call.answer()

@router.callback_query(F.data.startswith("fav_"))
async def user_toggle_fav(call: CallbackQuery):
    movie_id = int(call.data.split("_")[1])
    uid = call.from_user.id

    if fav_exists(uid, movie_id):
        fav_remove(uid, movie_id)
        await call.answer("💔 Sevimlilardan o'chirildi")
    else:
        fav_add(uid, movie_id)
        await call.answer("❤️ Sevimlilarga qo'shildi")

    movie = movie_get(movie_id)
    is_fav = fav_exists(uid, movie_id)
    try:
        await call.message.edit_reply_markup(
            reply_markup=kb_movie(movie_id, is_fav, bool(movie["is_premium"]))
        )
    except Exception:
        pass

# ─── FOYDALANUVCHI: TOP / YANGI ───────────
@router.message(F.text == "🔥 Top kinolar")
async def user_top_movies(message: Message):
    movies = movie_top(limit=PER_PAGE)
    if not movies:
        return await message.answer("❌ Hozircha kinolar yo'q!")
    await message.answer(
        "🔥 <b>Top kinolar:</b>",
        reply_markup=kb_movie_list(movies, 0, 1),
        parse_mode="HTML"
    )

@router.message(F.text == "🆕 Yangi kinolar")
async def user_new_movies(message: Message):
    movies = movie_new(limit=PER_PAGE)
    if not movies:
        return await message.answer("❌ Hozircha kinolar yo'q!")
    await message.answer(
        "🆕 <b>Yangi kinolar:</b>",
        reply_markup=kb_movie_list(movies, 0, 1),
        parse_mode="HTML"
    )

# ─── FOYDALANUVCHI: SEVIMLILAR ────────────
@router.message(F.text == "❤️ Sevimlilar")
async def user_favorites(message: Message):
    movies = fav_list(message.from_user.id)
    if not movies:
        return await message.answer("❌ Sevimlilar ro'yxati bo'sh!")
    await message.answer(
        "❤️ <b>Sevimli kinolaringiz:</b>",
        reply_markup=kb_movie_list(movies, 0, 1),
        parse_mode="HTML"
    )

# ─── FOYDALANUVCHI: QIDIRISH ───────────────
@router.message(F.text == "🔍 Qidirish")
async def user_search_start(message: Message, state: FSMContext):
    await message.answer("🔍 Qidirmoqchi bo'lgan kino nomini kiriting:", reply_markup=kb_cancel())
    await state.set_state(SearchSt.query)

@router.message(SearchSt.query)
async def user_search_process(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_main())

    results = movie_search(message.text.strip())
    await state.clear()

    if not results:
        return await message.answer("❌ Hech narsa topilmadi!", reply_markup=kb_main())

    await message.answer(
        f"🔍 <b>Qidiruv natijalari</b> ({len(results)} ta):",
        reply_markup=kb_movie_list(results, 0, 1),
        parse_mode="HTML"
    )

# ─── FOYDALANUVCHI: PROFIL ─────────────────
@router.message(F.text == "👤 Profil")
async def user_profile(message: Message):
    user = user_get(message.from_user.id)
    if not user:
        return await message.answer("❌ Ma'lumot topilmadi!")

    favs = fav_count(message.from_user.id)
    history = hist_list(message.from_user.id, limit=100)

    text = (
        f"👤 <b>Sizning profilingiz</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Ism: <b>{user['full_name']}</b>\n"
        f"⭐ Premium: {'✅ Ha' if user['is_premium'] else '❌ Yoq'}\n"
        f"❤️ Sevimlilar: <b>{favs}</b> ta\n"
        f"📺 Ko'rilgan kinolar: <b>{len(history)}</b> ta\n"
        f"📅 Ro'yxatdan o'tgan: <b>{user['joined_at']}</b>"
    )
    await message.answer(text, parse_mode="HTML")

# ─── FOYDALANUVCHI: YORDAM ─────────────────
@router.message(F.text == "ℹ️ Yordam")
async def user_help(message: Message):
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "🎬 Kinolar — barcha kinolarni ko'rish\n"
        "🔍 Qidirish — kino qidirish\n"
        "🔥 Top kinolar — eng ko'p ko'rilganlar\n"
        "🆕 Yangi kinolar — so'nggi qo'shilganlar\n"
        "❤️ Sevimlilar — saqlangan kinolar\n"
        "👤 Profil — shaxsiy ma'lumotlar",
        parse_mode="HTML"
    )

# ─── ADMIN: BROADCAST ──────────────────────
@router.message(F.text == "📢 Broadcast")
async def admin_broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📢 Yubormoqchi bo'lgan xabarni kiriting:", reply_markup=kb_cancel())
    await state.set_state(BroadcastSt.msg)

@router.message(BroadcastSt.msg)
async def admin_broadcast_process(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=kb_admin())

    await state.clear()
    ids = user_all_ids()
    status = await message.answer(f"📢 Yuborilmoqda... 0/{len(ids)}")

    sent, failed = 0, 0
    for i, uid in enumerate(ids):
        try:
            await message.copy_to(uid)
            sent += 1
        except Exception:
            failed += 1
        if i % 25 == 0:
            try:
                await status.edit_text(f"📢 Yuborilmoqda... {i}/{len(ids)}")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    admin_log_add(message.from_user.id, "broadcast", "-", f"sent={sent}, failed={failed}")
    await status.edit_text(f"✅ Yakunlandi!\n✅ Yuborildi: {sent}\n❌ Xato: {failed}", reply_markup=None)
    await message.answer("Admin panel:", reply_markup=kb_admin())

# ─── NOOP ───────────────────────────────────
@router.callback_query(F.data == "noop")
async def noop_cb(call: CallbackQuery):
    await call.answer()

# ══════════════════════════════════════════
#               MAIN
# ══════════════════════════════════════════
async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    log.info("🚀 Bot ishga tushdi")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
