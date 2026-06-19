import aiosqlite
from typing import Optional
from config import DB_PATH


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id        INTEGER PRIMARY KEY,
                username       TEXT,
                full_name      TEXT,
                birth_date     TEXT,
                soul_number    INTEGER,
                destiny_number INTEGER,
                soul_stone     TEXT,
                destiny_stone  TEXT,
                desire_key     TEXT,
                desire_stone   TEXT,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                stone1     TEXT,
                stone2     TEXT,
                stone3     TEXT,
                size       TEXT,
                metal      TEXT,
                intention  TEXT,
                package    TEXT,
                price      INTEGER,
                address    TEXT,
                status     TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()


async def save_user(user_id: int, username: Optional[str], full_name: str, **fields) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username or "", full_name),
        )
        if fields:
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            await db.execute(
                f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (*fields.values(), user_id),
            )
        else:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (username or "", full_name, user_id),
            )
        await db.commit()


async def create_order(user_id: int, **fields) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" * len(fields))
        cursor = await db.execute(
            f"INSERT INTO orders (user_id, {cols}) VALUES (?, {placeholders})",
            (user_id, *fields.values()),
        )
        await db.commit()
        return cursor.lastrowid


async def set_order_status(order_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()
