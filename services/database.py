import os
import sqlite3
import json

class DatabaseManager:
    def __init__(self, base_dir: str):
        self.db_path = os.path.join(base_dir, "vitality.db")
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    date_str TEXT PRIMARY KEY,
                    weight REAL,
                    sugar REAL,
                    exermet_m INTEGER DEFAULT 0,
                    exermet_e INTEGER DEFAULT 0,
                    soleus_m INTEGER DEFAULT 0,
                    soleus_e INTEGER DEFAULT 0,
                    pranayama INTEGER DEFAULT 0,
                    pelvic_yoga INTEGER DEFAULT 0,
                    other_exercises TEXT,
                    notes TEXT,
                    image_uri TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            conn.commit()

    def set_config(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_config(self, key: str, default=""):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cur.fetchone()
            return row[0] if row else default

    def save_day_log(self, date_str: str, weight: float, sugar: float,
                     ex_m: bool, ex_e: bool, sol_m: bool, sol_e: bool,
                     pran: bool, pelv: bool, other_ex: list, notes: str, image_uri: str = None):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO history (
                    date_str, weight, sugar, exermet_m, exermet_e,
                    soleus_m, soleus_e, pranayama, pelvic_yoga,
                    other_exercises, notes, image_uri
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_str, weight, sugar, int(ex_m), int(ex_e), int(sol_m), int(sol_e),
                  int(pran), int(pelv), json.dumps(other_ex), notes, image_uri))
            conn.commit()

    def get_day_log(self, date_str: str):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM history WHERE date_str = ?", (date_str,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "date_str": row[0],
                "weight": row[1],
                "sugar": row[2],
                "exermet_m": bool(row[3]),
                "exermet_e": bool(row[4]),
                "soleus_m": bool(row[5]),
                "soleus_e": bool(row[6]),
                "pranayama": bool(row[7]),
                "pelvic_yoga": bool(row[8]),
                "other_exercises": json.loads(row[9]) if row[9] else [],
                "notes": row[10] or "",
                "image_uri": row[11] or ""
            }

    def get_all_logs(self):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT date_str, weight, sugar FROM history ORDER BY date_str ASC")
            return cur.fetchall()