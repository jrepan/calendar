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
            cur.execute("SELECT DISTINCT ON(event) event as uid, date::text as date, title FROM events ORDER BY event, timestamp DESC")
            rows = cur.fetchall()
            return [dict(r) for r in rows]

def insert_events(events):
    with get_conn() as conn:
        with conn.cursor() as cur:
            for ev in events:
                cur.execute("INSERT INTO events (event, date, title, timestamp) VALUES (%s, %s, %s, NOW())", (ev['uid'], ev['date'], ev['title']))
            conn.commit()

def update_event(uid, date, title) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            # since we have a live connection to the database, we know our update is the most recent one
            cur.execute("DELETE FROM events WHERE event = %s", (uid,))

            cur.execute("INSERT INTO events (event, date, title, timestamp) VALUES (%s, %s, %s, NOW())", (uid, date, title))
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
