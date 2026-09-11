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
        user_id: Optional[int] = None,
        product_id: Optional[str] = None
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
        self.product_id = product_id

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
            "user_id": self.user_id,
            "product_id": self.product_id
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
        """Initializes tables for inspections, users, notifications, settings, and audits."""
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

            # 2. Inspections Table (Prompt 11 + Prompt 21 Traceability)
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
                    product_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Ensure product_id exists if upgrading existing DB
            cursor.execute("PRAGMA table_info(inspections)")
            cols = [row["name"] for row in cursor.fetchall()]
            if "product_id" not in cols:
                cursor.execute("ALTER TABLE inspections ADD COLUMN product_id TEXT")

            # 3. Notifications Table (Prompt 22 In-App Alerts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inspection_id INTEGER,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (inspection_id) REFERENCES inspections(id)
                )
            """)

            # 4. Settings Table (Prompt 23 Dynamic No-Code Tuning)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT NOT NULL,
                    min_val REAL,
                    max_val REAL,
                    setting_type TEXT NOT NULL DEFAULT 'float',
                    updated_at TEXT NOT NULL,
                    updated_by TEXT NOT NULL
                )
            """)

            # 5. Settings Audit History Table (Prompt 23)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT NOT NULL,
                    old_value TEXT NOT NULL,
                    new_value TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    changed_at TEXT NOT NULL
                )
            """)
            conn.commit()

        # Seed initial admin, settings, and demo inspection dataset if empty
        self.seed_defaults()

    def seed_defaults(self):
        """Creates default admin/operator users, system settings, and seeds demo inspections."""
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

            # Seed Default Dynamic Settings (Prompt 23)
            default_settings = [
                ("anomaly_threshold", "0.035", "Autoencoder reconstruction error cutoff for flagging defects", 0.005, 0.200, "float"),
                ("severity_minor_cutoff", "30.0", "Severity score threshold below which flaws are categorized as Minor", 10.0, 50.0, "float"),
                ("severity_major_cutoff", "70.0", "Severity score cutoff above which flaws are categorized as Critical", 50.0, 90.0, "float"),
                ("min_defect_area_px", "25.0", "Minimum contour area in pixels to eliminate sensor noise / false positives", 5.0, 500.0, "float"),
                ("ai_scan_provider", "gemini", "Multimodal AI engine for secondary scan arbitration (gemini, openai, claude)", None, None, "string"),
                ("alert_severity_threshold", "70.0", "Minimum severity score to trigger an urgent in-app alert", 30.0, 100.0, "float"),
                ("alert_rate_window_n", "20", "Number of recent inspections used to evaluate line rejection rate spikes", 5.0, 100.0, "int"),
                ("alert_rate_threshold_pct", "30.0", "Rejection rate percentage threshold that triggers a line yield warning", 5.0, 100.0, "float"),
                ("alerts_enabled", "1", "Master toggle enabling or disabling in-app notification alerts", 0.0, 1.0, "bool"),
            ]

            now_str = datetime.utcnow().isoformat()
            for key, val, desc, min_v, max_v, stype in default_settings:
                cursor.execute("SELECT COUNT(*) FROM settings WHERE key = ?", (key,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        INSERT INTO settings (key, value, description, min_val, max_val, setting_type, updated_at, updated_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (key, val, desc, min_v, max_v, stype, now_str, "system"))

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

    # --- Inspection Operations (Prompt 11 + Prompt 21 Traceability) ---
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
        timestamp: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Tuple[int, str]:
        """
        Inserts inspection record and triggers in-app notification rules (Prompt 22).
        Returns (inspection_id, assigned_product_id).
        """
        ts = timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Prompt 21: Auto-generate product_id if not provided
        pid = product_id.strip() if product_id and product_id.strip() else f"PROD-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inspections
                (timestamp, filename, is_defective, defect_type, confidence, defect_area, severity_score, severity_category, user_id, product_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts,
                filename,
                1 if is_defective else 0,
                defect_type,
                float(confidence),
                float(defect_area),
                float(severity_score),
                severity_category,
                user_id,
                pid
            ))
            inspection_id = cursor.lastrowid

            # Prompt 22: In-App Alert System evaluation
            self._evaluate_alerts(cursor, inspection_id, filename, pid, is_defective, defect_type, severity_score, severity_category)

            conn.commit()
            return inspection_id, pid

    def _evaluate_alerts(
        self,
        cursor: sqlite3.Cursor,
        inspection_id: int,
        filename: str,
        product_id: str,
        is_defective: bool,
        defect_type: str,
        severity_score: float,
        severity_category: str
    ):
        """Checks configurable alert rules (Prompt 22 & 23) and logs notifications."""
        # 1. Check if alerts are enabled
        cursor.execute("SELECT value FROM settings WHERE key = 'alerts_enabled'")
        row = cursor.fetchone()
        alerts_enabled = (row[0] != "0") if row else True
        if not alerts_enabled:
            return

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # 2. Rule A: Critical / Threshold-based Severity Alert
        cursor.execute("SELECT value FROM settings WHERE key = 'alert_severity_threshold'")
        s_row = cursor.fetchone()
        thresh_score = float(s_row[0]) if s_row else 70.0

        if severity_score >= thresh_score or severity_category.lower() == "critical":
            msg = f"CRITICAL DEFECT: {defect_type.replace('_', ' ').title()} on unit {product_id} ({filename}) · Severity {severity_score:.1f}/100"
            cursor.execute("""
                INSERT INTO notifications (inspection_id, message, severity, is_read, created_at)
                VALUES (?, ?, ?, 0, ?)
            """, (inspection_id, msg, "Critical", now_str))

        # 3. Rule B: Defect Rate Spike over last N inspections
        cursor.execute("SELECT value FROM settings WHERE key = 'alert_rate_window_n'")
        n_row = cursor.fetchone()
        window_n = int(float(n_row[0])) if n_row else 20

        cursor.execute("SELECT value FROM settings WHERE key = 'alert_rate_threshold_pct'")
        pct_row = cursor.fetchone()
        rate_thresh_pct = float(pct_row[0]) if pct_row else 30.0

        cursor.execute("""
            SELECT is_defective FROM inspections ORDER BY id DESC LIMIT ?
        """, (window_n,))
        recent_rows = cursor.fetchall()
        if len(recent_rows) >= 5:
            defect_cnt = sum(1 for r in recent_rows if r[0] == 1)
            defect_pct = (defect_cnt / len(recent_rows)) * 100.0
            if defect_pct >= rate_thresh_pct and is_defective:
                spike_msg = f"YIELD ALERT: Defect rate spike at {defect_pct:.1f}% across last {len(recent_rows)} units (Threshold: {rate_thresh_pct:.0f}%)"
                # Avoid flooding identical spike alert if one was generated in the last 2 minutes
                cursor.execute("""
                    SELECT COUNT(*) FROM notifications
                    WHERE message LIKE 'YIELD ALERT%' AND datetime(created_at) >= datetime('now', '-2 minutes')
                """)
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        INSERT INTO notifications (inspection_id, message, severity, is_read, created_at)
                        VALUES (?, ?, ?, 0, ?)
                    """, (inspection_id, spike_msg, "Major", now_str))

    # --- Product Traceability (Prompt 21) ---
    def get_inspections_by_product_id(self, product_id: str) -> List[Dict[str, Any]]:
        """Retrieves full timeline history of inspections for a specific product or batch ID."""
        clean_pid = product_id.strip()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.id, i.timestamp, i.filename, i.is_defective, i.defect_type,
                       i.confidence, i.defect_area, i.severity_score, i.severity_category,
                       i.user_id, i.product_id, u.username as inspector_name
                FROM inspections i
                LEFT JOIN users u ON i.user_id = u.id
                WHERE i.product_id = ? OR i.product_id LIKE ?
                ORDER BY i.timestamp ASC, i.id ASC
            """, (clean_pid, f"%{clean_pid}%"))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["is_defective"] = bool(d["is_defective"])
                results.append(d)
            return results

    # --- In-App Notifications (Prompt 22) ---
    def get_notifications(self, limit: int = 25, unread_only: bool = False) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT n.id, n.inspection_id, n.message, n.severity, n.is_read, n.created_at,
                       i.defect_type, i.filename, i.product_id
                FROM notifications n
                LEFT JOIN inspections i ON n.inspection_id = i.id
            """
            if unread_only:
                query += " WHERE n.is_read = 0"
            query += " ORDER BY n.id DESC LIMIT ?"
            cursor.execute(query, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_unread_notification_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE is_read = 0")
            return cursor.fetchone()[0]

    def mark_notification_as_read(self, notification_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
            conn.commit()
            return cursor.rowcount > 0

    def mark_all_notifications_as_read(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET is_read = 1 WHERE is_read = 0")
            affected = cursor.rowcount
            conn.commit()
            return affected

    # --- Dynamic Settings & Audit History (Prompt 23) ---
    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value, setting_type FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return default
            val_str, stype = row["value"], row["setting_type"]
            if stype == "float":
                try:
                    return float(val_str)
                except ValueError:
                    return default
            elif stype == "int":
                try:
                    return int(float(val_str))
                except ValueError:
                    return default
            elif stype == "bool":
                return val_str in ("1", "true", "True", "yes")
            return val_str

    def get_all_settings(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, description, min_val, max_val, setting_type, updated_at, updated_by FROM settings ORDER BY key ASC")
            return [dict(r) for r in cursor.fetchall()]

    def update_setting(self, key: str, new_value: Any, changed_by: str = "admin") -> Tuple[bool, str]:
        """Validates bounds and updates setting with audit trail logging (Prompt 23)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value, min_val, max_val, setting_type FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return False, f"Unknown setting '{key}'"

            old_val = str(row["value"])
            min_val = row["min_val"]
            max_val = row["max_val"]
            stype = row["setting_type"]

            # Validate input
            val_str = str(new_value).strip()
            if stype in ("float", "int"):
                try:
                    num_val = float(val_str)
                    if min_val is not None and num_val < float(min_val):
                        return False, f"Value {num_val} is below minimum allowed ({min_val})"
                    if max_val is not None and num_val > float(max_val):
                        return False, f"Value {num_val} exceeds maximum allowed ({max_val})"
                    if stype == "int":
                        val_str = str(int(num_val))
                    else:
                        val_str = str(num_val)
                except ValueError:
                    return False, f"Value '{new_value}' is not a valid number"

            now_str = datetime.utcnow().isoformat()
            cursor.execute("""
                UPDATE settings
                SET value = ?, updated_at = ?, updated_by = ?
                WHERE key = ?
            """, (val_str, now_str, changed_by, key))

            # Audit trail
            cursor.execute("""
                INSERT INTO settings_history (setting_key, old_value, new_value, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (key, old_val, val_str, changed_by, now_str))

            conn.commit()
            return True, "Setting updated successfully"

    def reset_settings_to_defaults(self, changed_by: str = "admin"):
        """Resets all settings to factory default baseline values."""
        defaults = {
            "anomaly_threshold": "0.035",
            "severity_minor_cutoff": "30.0",
            "severity_major_cutoff": "70.0",
            "min_defect_area_px": "25.0",
            "ai_scan_provider": "gemini",
            "alert_severity_threshold": "70.0",
            "alert_rate_window_n": "20",
            "alert_rate_threshold_pct": "30.0",
            "alerts_enabled": "1"
        }
        for k, v in defaults.items():
            self.update_setting(k, v, changed_by=f"{changed_by} (reset)")

    def get_settings_history(self, limit: int = 40) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, setting_key, old_value, new_value, changed_by, changed_at
                FROM settings_history
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

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
            query = "SELECT id, timestamp, filename, is_defective, defect_type, confidence, defect_area, severity_score, severity_category, product_id FROM inspections WHERE 1=1"
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

    def get_inspection_by_id(self, inspection_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single inspection record by ID for PDF certificate generation (Prompt 20)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.id, i.timestamp, i.filename, i.is_defective, i.defect_type,
                       i.confidence, i.defect_area, i.severity_score, i.severity_category,
                       i.user_id, i.product_id, u.username as inspector_name
                FROM inspections i
                LEFT JOIN users u ON i.user_id = u.id
                WHERE i.id = ?
            """, (inspection_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d["is_defective"] = bool(d["is_defective"])
                return d
            return None

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
                       confidence, defect_area, severity_score, severity_category, product_id
                FROM inspections
                ORDER BY id ASC
            """)
            return [dict(row) for row in cursor.fetchall()]


# Singleton database manager instance
db = DatabaseManager()
