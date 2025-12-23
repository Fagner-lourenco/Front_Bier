"""
Sync Service for EDGE Server
Background synchronization of consumption records with SaaS backend
"""
import time
import threading
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

from config import config
from database import database, ConsumptionRecord, SyncStatus


class SyncService:
    """
    Background service to sync consumption records with SaaS backend
    
    Features:
    - Periodic sync of pending records
    - Retry logic for failed syncs
    - Exponential backoff
    - Connection health monitoring
    """
    
    def __init__(self):
        self.base_url = config.saas.BASE_URL
        self.api_key = config.saas.API_KEY
        self.machine_id = config.saas.MACHINE_ID
        self.sync_interval = config.saas.SYNC_INTERVAL
        self.timeout = config.saas.TIMEOUT
        self.max_retries = config.saas.MAX_RETRIES
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_sync_time: Optional[datetime] = None
        self._last_sync_success = True
        self._consecutive_failures = 0
        
    @property
    def headers(self) -> Dict[str, str]:
        """Request headers with API key"""
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
    
    def check_connection(self) -> bool:
        """Check if SaaS backend is reachable"""
        try:
            url = f"{self.base_url}/api/v1/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def _format_datetime(self, dt_str: str) -> Optional[str]:
        """
        Formata datetime string para formato ISO com timezone UTC.
        O SaaS espera datetime com 'Z' no final.
        """
        if not dt_str:
            return None
        # Adiciona 'Z' se não tiver timezone
        if not dt_str.endswith('Z') and '+' not in dt_str and '-' not in dt_str[-6:]:
            return dt_str + "Z"
        return dt_str
    
    def sync_consumption(self, record: ConsumptionRecord) -> bool:
        """
        Sync a single consumption record to SaaS
        
        Returns True if sync successful
        """
        url = f"{self.base_url}/api/v1/consumptions"
        
        # Mapeamento de status EDGE -> SaaS
        STATUS_MAP = {
            "completed": "OK",
            "interrupted": "PARTIAL",
            "error": "ERROR",
            "cancelled": "CANCELLED",
        }
        
        # Payload no formato esperado pelo SaaS
        payload = {
            "machine_id": self.machine_id,
            "sale_id": record.sale_id,
            "token_id": record.token_id if hasattr(record, 'token_id') else None,
            "ml_served": round(record.volume_dispensed_ml),
            "ml_authorized": record.volume_authorized_ml,
            "status": STATUS_MAP.get(record.status, "ERROR"),
            "started_at": self._format_datetime(record.started_at),
            "finished_at": self._format_datetime(record.finished_at)
        }
        
        # Remove campos None para evitar problemas de validação
        payload = {k: v for k, v in payload.items() if v is not None}
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code in (200, 201):
                database.mark_synced(
                    record.id,
                    response_code=response.status_code,
                    response_body=response.text[:500]
                )
                print(f"✅ Synced: {record.id} ({record.volume_dispensed_ml:.0f}ml)")
                return True
            else:
                database.mark_sync_failed(
                    record.id,
                    error_message=f"HTTP {response.status_code}: {response.text[:200]}",
                    response_code=response.status_code
                )
                print(f"❌ Sync failed: {record.id} - HTTP {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            database.mark_sync_failed(record.id, "Connection timeout")
            print(f"⏱️ Sync timeout: {record.id}")
            return False
            
        except requests.exceptions.ConnectionError:
            database.mark_sync_failed(record.id, "Connection error - SaaS unreachable")
            print(f"🔌 Connection error: {record.id}")
            return False
            
        except Exception as e:
            database.mark_sync_failed(record.id, str(e))
            print(f"❌ Sync error: {record.id} - {e}")
            return False
    
    def sync_pending(self) -> Dict[str, int]:
        """
        Sync all pending consumption records
        
        Returns dict with counts: synced, failed, pending
        """
        pending = database.get_pending_consumptions()
        
        if not pending:
            return {"synced": 0, "failed": 0, "pending": 0}
        
        print(f"📤 Syncing {len(pending)} pending records...")
        
        synced = 0
        failed = 0
        
        for record in pending:
            if self.sync_consumption(record):
                synced += 1
            else:
                failed += 1
                # Stop on consecutive failures (likely connection issue)
                if failed >= 3:
                    print("⚠️ Multiple failures - stopping sync batch")
                    break
        
        # Get updated pending count
        remaining = len(database.get_pending_consumptions())
        
        return {"synced": synced, "failed": failed, "pending": remaining}
    
    def retry_failed(self) -> Dict[str, int]:
        """
        Retry failed consumption records
        
        Returns dict with counts: synced, failed, remaining
        """
        failed = database.get_failed_consumptions(max_attempts=self.max_retries)
        
        if not failed:
            return {"synced": 0, "failed": 0, "remaining": 0}
        
        print(f"🔄 Retrying {len(failed)} failed records...")
        
        synced = 0
        still_failed = 0
        
        for record in failed:
            if self.sync_consumption(record):
                synced += 1
            else:
                still_failed += 1
        
        remaining = len(database.get_failed_consumptions(max_attempts=self.max_retries))
        
        return {"synced": synced, "failed": still_failed, "remaining": remaining}
    
    def _sync_loop(self):
        """Main sync loop (runs in background thread)"""
        print(f"🔄 Sync service started (interval: {self.sync_interval}s)")
        
        while self._running:
            try:
                # Check connection first
                if not self.check_connection():
                    print("⚠️ SaaS unreachable - skipping sync")
                    self._last_sync_success = False
                    self._consecutive_failures += 1
                else:
                    # Sync pending records
                    result = self.sync_pending()
                    
                    # Also retry some failed records
                    if result["synced"] > 0 or result["pending"] == 0:
                        retry_result = self.retry_failed()
                        result["retried"] = retry_result["synced"]
                    
                    self._last_sync_time = datetime.utcnow()
                    self._last_sync_success = result["failed"] == 0
                    
                    if result["synced"] > 0 or result.get("retried", 0) > 0:
                        self._consecutive_failures = 0
                    
                # Clean up expired tokens
                database.cleanup_expired_tokens()
                
            except Exception as e:
                print(f"❌ Sync loop error: {e}")
                self._last_sync_success = False
                self._consecutive_failures += 1
            
            # Calculate backoff based on failures
            if self._consecutive_failures > 0:
                backoff = min(60, self.sync_interval * (2 ** min(self._consecutive_failures - 1, 4)))
                time.sleep(backoff)
            else:
                time.sleep(self.sync_interval)
        
        print("🛑 Sync service stopped")
    
    def start(self):
        """Start the background sync service"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the background sync service"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get sync service status"""
        stats = database.get_consumption_stats()
        
        return {
            "running": self._running,
            "last_sync": self._last_sync_time.isoformat() if self._last_sync_time else None,
            "last_success": self._last_sync_success,
            "consecutive_failures": self._consecutive_failures,
            "saas_reachable": self.check_connection(),
            "records": stats
        }
    
    def force_sync(self) -> Dict[str, Any]:
        """Force immediate sync (blocking)"""
        print("⚡ Force sync requested")
        result = self.sync_pending()
        retry_result = self.retry_failed()
        
        return {
            "synced": result["synced"] + retry_result["synced"],
            "failed": result["failed"],
            "pending": result["pending"],
            "retried": retry_result["synced"]
        }


# Global sync service instance
sync_service = SyncService()


# Testing
if __name__ == "__main__":
    # Initialize database
    database.initialize()
    
    print("\n--- Testing Sync Service ---")
    
    # Check connection
    print(f"SaaS reachable: {sync_service.check_connection()}")
    
    # Get status
    status = sync_service.get_status()
    print(f"Status: {status}")
    
    # Try to sync pending
    result = sync_service.sync_pending()
    print(f"Sync result: {result}")
    
    # Start background service
    print("\nStarting background sync...")
    sync_service.start()
    
    # Wait a bit
    time.sleep(5)
    
    # Check status again
    status = sync_service.get_status()
    print(f"Status after 5s: {status}")
    
    # Stop service
    sync_service.stop()
    print("\n✅ Sync service test complete")
