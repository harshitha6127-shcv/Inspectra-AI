"""
src/models.py - SQLite Database Models & Authentication Layer
=============================================================
Implements:
- Prompt 11: SQLite `inspections` table storing inspection history
- Prompt 13: User authentication with `users` table, password hashing,
             and role-based permissions (admin vs operator).
"""

import os
import sqlite3
from datetime import datetime, timedelta
import random
from typing import Optional, Dict, Any, List
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "inspections.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


class InspectionRecord:
    """Represents an inspection result stored in SQLite."""
    def __init__(
        self,
        id: Optional[int],
        timestamp: str,
        filename: str,
        is_defective: bool,
        defect_type: str,
        confidence: float,
        defect_area: float,
        severity_score: float,
        severity_category: str,
        user_id: Optional[int] = None
    ):
        self.id = id
        self.timestamp = timestamp
        self.filename = filename
        self.is_defective = bool(is_defective)
        self.defect_type = defect_type
        self.confidence = float(confidence)
        self.defect_area = float(defect_area)
        self.severity_score = float(severity_score)
        self.severity_category = severity_category
        self.user_id = user_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "filename": self.filename,
            "is_defective": self.is_defective,
            "defect_type": self.defect_type,
            "confidence": round(self.confidence, 4),
            "defect_area": round(self.defect_area, 2),
            "severity_score": round(self.severity_score, 1),
            "severity_category": self.severity_category,
            "user_id": self.user_id
        }


class User:
    """User account representation with role-based access control (Prompt 13)."""
    def __init__(
        self,
        id: Optional[int],
        username: str,
        email: str,
        password_hash: str,
        role: str = "operator",
        created_at: Optional[str] = None
    ):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role.lower()  # "admin" or "operator"
        self.created_at = created_at or datetime.utcnow().isoformat()

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

    def is_admin(self) -> bool:
        return self.role == "admin"

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at
        }


class DatabaseManager:
    """Handles SQLite connection and transactions."""
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        """Initializes tables for inspections and users if not already existing."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Users Table (Prompt 13)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'operator',
                    created_at TEXT NOT NULL
                )
            """)

            # 2. Inspections Table (Prompt 11)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inspections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    is_defective INTEGER NOT NULL,
                    defect_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    defect_area REAL NOT NULL,
                    severity_score REAL NOT NULL,
                    severity_category TEXT NOT NULL,
                    user_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()

        # Seed initial admin and demo inspection dataset if empty
        self.seed_defaults()

    def seed_defaults(self):
        """Creates default admin/operator users and seeds demo inspections."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Seed Admin User if not exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            if cursor.fetchone()[0] == 0:
                admin_hash = generate_password_hash("admin123")
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                    ("admin", "admin@factory.local", admin_hash, "admin", datetime.utcnow().isoformat())
                )

            # Seed Operator User if not exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'operator'")
            if cursor.fetchone()[0] == 0:
                op_hash = generate_password_hash("operator123")
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                    ("operator", "operator@factory.local", op_hash, "operator", datetime.utcnow().isoformat())
                )

            # Seed realistic inspections if table is completely empty
            cursor.execute("SELECT COUNT(*) FROM inspections")
            count = cursor.fetchone()[0]
            if count == 0:
                self._seed_sample_inspections(cursor)

            conn.commit()

    def _seed_sample_inspections(self, cursor: sqlite3.Cursor):
        """Populates realistic baseline inspection data across the last 14 days."""
        defect_types = ["normal", "crack", "scratch", "dent", "stain", "discoloration", "dimensional_irregularity"]
        severities = {
            "normal": (0.0, "None"),
            "crack": (82.5, "Critical"),
            "scratch": (42.0, "Major"),
            "dent": (74.0, "Critical"),
            "stain": (24.5, "Minor"),
            "discoloration": (21.0, "Minor"),
            "dimensional_irregularity": (78.0, "Critical")
        }

        now = datetime.utcnow()
        for i in range(65):
            days_ago = random.uniform(0, 14)
            ts = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            # 70% conforming, 30% defective in realistic manufacturing setup
            if random.random() < 0.72:
                dtype = "normal"
                is_def = 0
                conf = round(random.uniform(0.92, 0.99), 3)
                area = 0.0
                score, cat = severities["normal"]
            else:
                dtype = random.choice([t for t in defect_types if t != "normal"])
                is_def = 1
                conf = round(random.uniform(0.84, 0.98), 3)
                area = round(random.uniform(120, 680), 1)
                base_score, cat = severities[dtype]
                score = round(max(5.0, min(99.0, base_score + random.uniform(-6, 6))), 1)
                if score < 30.0:
                    cat = "Minor"
                elif score <= 70.0:
                    cat = "Major"
                else:
                    cat = "Critical"

            cursor.execute("""
                INSERT INTO inspections
                (timestamp, filename, is_defective, defect_type, confidence, defect_area, severity_score, severity_category, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ts, f"part_{1000 + i}.png", is_def, dtype, conf, area, score, cat, 1))

    # --- User Management Operations ---
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, password_hash, role, created_at FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return User(row["id"], row["username"], row["email"], row["password_hash"], row["role"], row["created_at"])
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, password_hash, role, created_at FROM users WHERE username = ?", (username.strip(),))
            row = cursor.fetchone()
            if row:
                return User(row["id"], row["username"], row["email"], row["password_hash"], row["role"], row["created_at"])
            return None

    def create_user(self, username: str, email: str, password: str, role: str = "operator") -> User:
        pw_hash = generate_password_hash(password)
        created_at = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (username.strip(), email.strip().lower(), pw_hash, role.lower(), created_at)
            )
            user_id = cursor.lastrowid
            conn.commit()
            return User(user_id, username, email, pw_hash, role, created_at)

    def list_users(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id ASC")
            return [dict(row) for row in cursor.fetchall()]

    # --- Inspection Operations (Prompt 11) ---
    def add_inspection(
        self,
        filename: str,
        is_defective: bool,
        defect_type: str,
        confidence: float,
        defect_area: float,
        severity_score: float,
        severity_category: str,
        user_id: Optional[int] = None,
        timestamp: Optional[str] = None
    ) -> int:
        ts = timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inspections
                (timestamp, filename, is_defective, defect_type, confidence, defect_area, severity_score, severity_category, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts,
                filename,
                1 if is_defective else 0,
                defect_type,
                float(confidence),
                float(defect_area),
                float(severity_score),
                severity_category,
                user_id
            ))
            conn.commit()
            return cursor.lastrowid

    def get_dashboard_metrics(self, days: int = 30, defect_filter: Optional[str] = None, severity_filter: Optional[str] = None) -> Dict[str, Any]:
        """Calculates aggregated KPIs, timeline series, defect breakdown, and severity distribution."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Base totals
            cursor.execute("SELECT COUNT(*) FROM inspections")
            total_all = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM inspections WHERE is_defective = 1")
            total_defects_all = cursor.fetchone()[0]

            # In selected window
            cursor.execute("SELECT COUNT(*) FROM inspections WHERE timestamp >= ?", (cutoff,))
            window_total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM inspections WHERE timestamp >= ? AND is_defective = 1", (cutoff,))
            window_defects = cursor.fetchone()[0]

            window_conforming = window_total - window_defects
            rejection_rate = round((window_defects / max(1, window_total)) * 100, 2)

            cursor.execute("SELECT AVG(severity_score) FROM inspections WHERE timestamp >= ? AND is_defective = 1", (cutoff,))
            avg_sev = round(cursor.fetchone()[0] or 0.0, 1)

            # Timeline aggregation (by day)
            cursor.execute("""
                SELECT substr(timestamp, 1, 10) as day,
                       COUNT(*) as total_count,
                       SUM(CASE WHEN is_defective = 1 THEN 1 ELSE 0 END) as defect_count,
                       SUM(CASE WHEN is_defective = 0 THEN 1 ELSE 0 END) as conforming_count
                FROM inspections
                WHERE timestamp >= ?
                GROUP BY substr(timestamp, 1, 10)
                ORDER BY day ASC
            """, (cutoff,))
            timeline = [dict(row) for row in cursor.fetchall()]

            # Defect distribution (across defective items)
            cursor.execute("""
                SELECT defect_type, COUNT(*) as count
                FROM inspections
                WHERE timestamp >= ? AND is_defective = 1
                GROUP BY defect_type
                ORDER BY count DESC
            """, (cutoff,))
            defect_dist = {row["defect_type"]: row["count"] for row in cursor.fetchall()}

            # Severity breakdown
            cursor.execute("""
                SELECT severity_category, COUNT(*) as count
                FROM inspections
                WHERE timestamp >= ?
                GROUP BY severity_category
            """, (cutoff,))
            severity_breakdown = {"Minor": 0, "Major": 0, "Critical": 0, "None": 0}
            for row in cursor.fetchall():
                cat = row["severity_category"]
                if cat in severity_breakdown:
                    severity_breakdown[cat] = row["count"]

            # Recent 20 inspections with optional filtering
            query = "SELECT id, timestamp, filename, is_defective, defect_type, confidence, defect_area, severity_score, severity_category FROM inspections WHERE 1=1"
            params: List[Any] = []

            if defect_filter and defect_filter != "all":
                query += " AND defect_type = ?"
                params.append(defect_filter)

            if severity_filter and severity_filter != "all":
                query += " AND severity_category = ?"
                params.append(severity_filter)

            query += " ORDER BY id DESC LIMIT 20"
            cursor.execute(query, tuple(params))
            recent_inspections = [dict(row) for row in cursor.fetchall()]

            return {
                "summary": {
                    "total_inspections": total_all,
                    "total_defects": total_defects_all,
                    "total_conforming": total_all - total_defects_all,
                    "window_inspections": window_total,
                    "window_defects": window_defects,
                    "window_conforming": window_conforming,
                    "rejection_rate_percent": rejection_rate,
                    "avg_severity_score": avg_sev
                },
                "timeline": timeline,
                "defect_distribution": defect_dist,
                "severity_breakdown": severity_breakdown,
                "recent_inspections": recent_inspections
            }

    def clear_inspections(self):
        """Wipes the inspections table (Prompt 11 - Admin only)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inspections")
            conn.commit()

    def get_all_inspections_for_csv(self) -> List[Dict[str, Any]]:
        """Returns all rows in inspections table for CSV export."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, filename, is_defective, defect_type,
                       confidence, defect_area, severity_score, severity_category
                FROM inspections
                ORDER BY id ASC
            """)
            return [dict(row) for row in cursor.fetchall()]


# Singleton database manager instance
db = DatabaseManager()
