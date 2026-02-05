import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost/calendar')

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    timestamp TIMESTAMP NOT NULL,
                    event TEXT NOT NULL,
                    date DATE NOT NULL,
                    title TEXT
                );
                CREATE INDEX IF NOT EXISTS idx ON events USING BTREE (timestamp, event);
                """
            )
            conn.commit()

def fetch_events() -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT event as uid, date::text as date, title FROM events ORDER BY date")
            rows = cur.fetchall()
            return [dict(r) for r in rows]

def insert_event(uid, date, title):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO events (event, date, title, timestamp) VALUES (%s, %s, %s, NOW())", (uid, date, title))
            conn.commit()

def update_event(uid, date, title) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE events SET date = %s, title = %s, timestamp = NOW() WHERE event = %s", (date, title, uid))
            affected = cur.rowcount
            conn.commit()
    return affected > 0

def delete_event(uid) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE event = %s", (uid,))
            affected = cur.rowcount
            conn.commit()
    return affected > 0

def event_exists(uid) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM events WHERE event = %s LIMIT 1", (uid,))
            return cur.fetchone() is not None
