import os
import sqlite3
import json

class DatabaseManager:
    def __init__(self, base_dir: str):
        self.db_path = os.path.join(base_dir, "vitality.db")
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Daily logs table with UNIQUE constraint on log_date for upserts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_date TEXT UNIQUE NOT NULL,
                    weight REAL,
                    sugar REAL,
                    exermet_m INTEGER,
                    exermet_e INTEGER,
                    soleus_m INTEGER,
                    soleus_e INTEGER,
                    pranayama INTEGER,
                    pelvic_yoga INTEGER,
                    meals_json TEXT,
                    notes TEXT,
                    image_uri TEXT
                )
            ''')
            # App configuration table (stores BYOK Gemini keys)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.commit()

    def save_day_log(self, log_date: str, weight: float, sugar: float,
                     ex_m: bool, ex_e: bool, sol_m: bool, sol_e: bool,
                     pran: bool, pelv: bool, meals: list, notes: str, img_uri: str):
        """UPSERT statement: inserts new day or updates existing row for the date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO daily_logs (
                    log_date, weight, sugar, exermet_m, exermet_e,
                    soleus_m, soleus_e, pranayama, pelvic_yoga,
                    meals_json, notes, image_uri
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(log_date) DO UPDATE SET
                    weight=excluded.weight,
                    sugar=excluded.sugar,
                    exermet_m=excluded.exermet_m,
                    exermet_e=excluded.exermet_e,
                    soleus_m=excluded.soleus_m,
                    soleus_e=excluded.soleus_e,
                    pranayama=excluded.pranayama,
                    pelvic_yoga=excluded.pelvic_yoga,
                    meals_json=excluded.meals_json,
                    notes=excluded.notes,
                    image_uri=excluded.image_uri
            ''', (
                log_date, weight, sugar,
                int(ex_m), int(ex_e), int(sol_m), int(sol_e),
                int(pran), int(pelv), json.dumps(meals),
                notes, img_uri
            ))
            conn.commit()

    def get_day_log(self, log_date: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT weight, sugar, exermet_m, exermet_e,
                       soleus_m, soleus_e, pranayama, pelvic_yoga,
                       meals_json, notes, image_uri
                FROM daily_logs WHERE log_date = ?
            ''', (log_date,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "weight": row[0],
                "sugar": row[1],
                "exermet_m": bool(row[2]),
                "exermet_e": bool(row[3]),
                "soleus_m": bool(row[4]),
                "soleus_e": bool(row[5]),
                "pranayama": bool(row[6]),
                "pelvic_yoga": bool(row[7]),
                "meals": json.loads(row[8]) if row[8] else [],
                "notes": row[9] or "",
                "image_uri": row[10] or ""
            }

    def get_all_logs(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, log_date, weight, sugar, exermet_m, exermet_e,
                       soleus_m, soleus_e, pranayama, pelvic_yoga, notes
                FROM daily_logs ORDER BY log_date ASC
            ''')
            return cursor.fetchall()

    def set_config(self, key: str, value: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO app_config (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            ''', (key, value))
            conn.commit()

    def get_config(self, key: str, default: str = ""):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM app_config WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row[0] if row else default