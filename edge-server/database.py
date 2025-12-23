"""
Local SQLite Database for EDGE Server
Stores consumption records for offline operation and sync
"""
import sqlite3
import json
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager

from config import config


class SyncStatus(Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


@dataclass
class ConsumptionRecord:
    """Local consumption record"""
    id: str
    sale_id: str
    token_id: Optional[str]  # Token HMAC usado na autorização
    beverage_id: str
    tap_id: int
    volume_authorized_ml: int
    volume_dispensed_ml: float
    started_at: str
    finished_at: str
    duration_seconds: float
    pulse_count: int
    flow_rate_avg: float
    status: str  # completed, interrupted, error
    sync_status: str  # pending, synced, failed
    sync_attempts: int
    last_sync_attempt: Optional[str]
    error_message: Optional[str]
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_row(cls, row: tuple) -> 'ConsumptionRecord':
        return cls(
            id=row[0],
            sale_id=row[1],
            token_id=row[2],
            beverage_id=row[3],
            tap_id=row[4],
            volume_authorized_ml=row[5],
            volume_dispensed_ml=row[6],
            started_at=row[7],
            finished_at=row[8],
            duration_seconds=row[9],
            pulse_count=row[10],
            flow_rate_avg=row[11],
            status=row[12],
            sync_status=row[13],
            sync_attempts=row[14],
            last_sync_attempt=row[15],
            error_message=row[16],
            created_at=row[17]
        )


class Database:
    """
    SQLite database for local storage
    Handles offline consumption records and sync queue
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.DB_PATH
        self._initialized = False
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def initialize(self):
        """Create database tables if they don't exist"""
        if self._initialized:
            return
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Consumption records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS consumptions (
                    id TEXT PRIMARY KEY,
                    sale_id TEXT NOT NULL,
                    token_id TEXT,
                    beverage_id TEXT NOT NULL,
                    tap_id INTEGER NOT NULL,
                    volume_authorized_ml INTEGER NOT NULL,
                    volume_dispensed_ml REAL NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    pulse_count INTEGER NOT NULL,
                    flow_rate_avg REAL NOT NULL,
                    status TEXT NOT NULL,
                    sync_status TEXT NOT NULL DEFAULT 'pending',
                    sync_attempts INTEGER NOT NULL DEFAULT 0,
                    last_sync_attempt TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(sale_id)
                )
            ''')
            
            # Sync log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consumption_id TEXT NOT NULL,
                    attempted_at TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    response_code INTEGER,
                    response_body TEXT,
                    error_message TEXT,
                    FOREIGN KEY (consumption_id) REFERENCES consumptions(id)
                )
            ''')
            
            # Used tokens table (for single-use enforcement across restarts)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS used_tokens (
                    nonce TEXT PRIMARY KEY,
                    used_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_status ON consumptions(sync_status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON consumptions(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_token_expires ON used_tokens(expires_at)')
            
            conn.commit()
        
        self._initialized = True
        print(f"✅ Database initialized: {self.db_path}")
    
    # ==================== Consumption Methods ====================
    
    def save_consumption(self, 
                         sale_id: str,
                         token_id: str,
                         beverage_id: str,
                         tap_id: int,
                         volume_authorized_ml: int,
                         volume_dispensed_ml: float,
                         started_at: datetime,
                         finished_at: datetime,
                         pulse_count: int,
                         flow_rate_avg: float,
                         status: str = "completed",
                         error_message: str = None) -> ConsumptionRecord:
        """Save a new consumption record"""
        
        record_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        duration = (finished_at - started_at).total_seconds()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO consumptions (
                    id, sale_id, token_id, beverage_id, tap_id,
                    volume_authorized_ml, volume_dispensed_ml,
                    started_at, finished_at, duration_seconds,
                    pulse_count, flow_rate_avg, status,
                    sync_status, sync_attempts, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record_id, sale_id, token_id, beverage_id, tap_id,
                volume_authorized_ml, volume_dispensed_ml,
                started_at.isoformat(), finished_at.isoformat(), duration,
                pulse_count, flow_rate_avg, status,
                SyncStatus.PENDING.value, 0, error_message, now
            ))
        
        return self.get_consumption(record_id)
    
    def get_consumption(self, record_id: str) -> Optional[ConsumptionRecord]:
        """Get consumption by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM consumptions WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            return ConsumptionRecord.from_row(tuple(row)) if row else None
    
    def get_pending_consumptions(self, limit: int = 50) -> List[ConsumptionRecord]:
        """Get consumptions pending sync"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM consumptions 
                WHERE sync_status = ? 
                ORDER BY created_at ASC
                LIMIT ?
            ''', (SyncStatus.PENDING.value, limit))
            
            return [ConsumptionRecord.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def get_failed_consumptions(self, max_attempts: int = 5) -> List[ConsumptionRecord]:
        """Get failed consumptions that haven't exceeded retry limit"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM consumptions 
                WHERE sync_status = ? AND sync_attempts < ?
                ORDER BY last_sync_attempt ASC
                LIMIT 20
            ''', (SyncStatus.FAILED.value, max_attempts))
            
            return [ConsumptionRecord.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def mark_synced(self, record_id: str, response_code: int = 200, response_body: str = None):
        """Mark consumption as synced"""
        now = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update consumption
            cursor.execute('''
                UPDATE consumptions 
                SET sync_status = ?, sync_attempts = sync_attempts + 1, last_sync_attempt = ?
                WHERE id = ?
            ''', (SyncStatus.SYNCED.value, now, record_id))
            
            # Log sync attempt
            cursor.execute('''
                INSERT INTO sync_log (consumption_id, attempted_at, success, response_code, response_body)
                VALUES (?, ?, ?, ?, ?)
            ''', (record_id, now, 1, response_code, response_body))
    
    def mark_sync_failed(self, record_id: str, error_message: str, response_code: int = None):
        """Mark consumption sync as failed"""
        now = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update consumption
            cursor.execute('''
                UPDATE consumptions 
                SET sync_status = ?, sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = ?, error_message = ?
                WHERE id = ?
            ''', (SyncStatus.FAILED.value, now, error_message, record_id))
            
            # Log sync attempt
            cursor.execute('''
                INSERT INTO sync_log (consumption_id, attempted_at, success, response_code, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (record_id, now, 0, response_code, error_message))
    
    def get_consumption_stats(self) -> Dict[str, Any]:
        """Get consumption statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM consumptions')
            total = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM consumptions WHERE sync_status = ?', 
                          (SyncStatus.PENDING.value,))
            pending = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM consumptions WHERE sync_status = ?', 
                          (SyncStatus.SYNCED.value,))
            synced = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM consumptions WHERE sync_status = ?', 
                          (SyncStatus.FAILED.value,))
            failed = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(volume_dispensed_ml) FROM consumptions')
            total_volume = cursor.fetchone()[0] or 0
            
            return {
                "total_records": total,
                "pending_sync": pending,
                "synced": synced,
                "failed": failed,
                "total_volume_ml": total_volume
            }
    
    # ==================== Token Methods ====================
    
    def is_token_used(self, nonce: str) -> bool:
        """Check if token nonce has been used"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM used_tokens WHERE nonce = ?', (nonce,))
            return cursor.fetchone() is not None
    
    def mark_token_used(self, nonce: str, ttl_seconds: int = 300):
        """Mark token as used"""
        now = datetime.utcnow()
        expires = datetime.utcfromtimestamp(time.time() + ttl_seconds)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO used_tokens (nonce, used_at, expires_at)
                VALUES (?, ?, ?)
            ''', (nonce, now.isoformat(), expires.isoformat()))
    
    def cleanup_expired_tokens(self):
        """Remove expired token entries"""
        now = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM used_tokens WHERE expires_at < ?', (now,))
            deleted = cursor.rowcount
            if deleted > 0:
                print(f"🧹 Cleaned up {deleted} expired tokens")


# Global database instance
database = Database()


# Testing
if __name__ == "__main__":
    from datetime import datetime, timedelta
    
    db = Database("test_edge.db")
    db.initialize()
    
    # Test saving consumption
    print("\n--- Testing Database ---")
    
    started = datetime.utcnow()
    finished = started + timedelta(seconds=5)
    
    record = db.save_consumption(
        sale_id="test-sale-" + str(uuid.uuid4())[:8],
        token_id="test-token-hmac-123",
        beverage_id="550e8400-e29b-41d4-a716-446655440001",
        tap_id=1,
        volume_authorized_ml=500,
        volume_dispensed_ml=495.5,
        started_at=started,
        finished_at=finished,
        pulse_count=223,
        flow_rate_avg=99.1,
        status="completed"
    )
    print(f"Saved: {record.id}")
    
    # Get pending
    pending = db.get_pending_consumptions()
    print(f"Pending: {len(pending)}")
    
    # Get stats
    stats = db.get_consumption_stats()
    print(f"Stats: {stats}")
    
    # Test token usage
    test_nonce = "test-nonce-123"
    print(f"\nToken used (before): {db.is_token_used(test_nonce)}")
    db.mark_token_used(test_nonce)
    print(f"Token used (after): {db.is_token_used(test_nonce)}")
    
    print("\n✅ Database tests passed!")
