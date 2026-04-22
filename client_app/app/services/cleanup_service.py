"""
File cleanup service for client application.

Handles automatic deletion of old files from data folders
based on configurable retention policies.

Runs on application startup (after a delay) if the retention
period has passed since the last cleanup.
"""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import (
    CleanupSchedulerConfig,
    CleanupPolicy,
    CleanupLog
)


# Default cleanup policies
DEFAULT_POLICIES = [
    {
        "folder_type": "uploads",
        "folder_path": "data/uploads",
        "retention_days": 7,
        "file_patterns": "*",
        "enabled": True
    },
    {
        "folder_type": "etl",
        "folder_path": "data/uploads/etl",
        "retention_days": 7,
        "file_patterns": "*",
        "enabled": True
    },
    {
        "folder_type": "results",
        "folder_path": "data/resultados",
        "retention_days": 30,
        "file_patterns": "*",
        "enabled": True
    },
    {
        "folder_type": "execution",
        "folder_path": "data/executions",
        "retention_days": 1,
        "file_patterns": "*",
        "enabled": True
    },
    {
        "folder_type": "screenshots",
        "folder_path": "data/screenshots",
        "retention_days": 14,
        "file_patterns": "*",
        "enabled": True
    },
]


class CleanupService:
    """
    Singleton service for managing file cleanup operations.
    """

    _instance: Optional["CleanupService"] = None
    _cleanup_task: Optional[asyncio.Task] = None
    _periodic_task: Optional[asyncio.Task] = None
    _notification_callback = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_notification_callback(self, callback):
        """Set callback for UI notifications."""
        self._notification_callback = callback

    def _notify(self, message: str, msg_type: str = "info"):
        """Send notification if callback is set."""
        if self._notification_callback:
            try:
                self._notification_callback(message, msg_type)
            except Exception:
                pass  # UI might not be ready

    async def _get_config(self) -> CleanupSchedulerConfig:
        """Get or create cleanup scheduler config."""
        async with AsyncSession(client_engine) as session:
            config = await session.get(CleanupSchedulerConfig, 1)
            if not config:
                config = CleanupSchedulerConfig(id=1)
                session.add(config)
                await session.commit()
                await session.refresh(config)
            return config

    async def _get_policies(self) -> List[CleanupPolicy]:
        """Get all cleanup policies."""
        async with AsyncSession(client_engine) as session:
            result = await session.exec(select(CleanupPolicy))
            return list(result.all())

    async def seed_default_policies(self):
        """Seed default cleanup policies if they don't exist."""
        async with AsyncSession(client_engine) as session:
            for policy_data in DEFAULT_POLICIES:
                result = await session.exec(
                    select(CleanupPolicy).where(
                        CleanupPolicy.folder_type == policy_data["folder_type"]
                    )
                )
                existing = result.first()

                if not existing:
                    policy = CleanupPolicy(**policy_data)
                    session.add(policy)
                    print(f"[Cleanup] Seeding policy for {policy_data['folder_type']}")

            await session.commit()

    async def should_run_cleanup(self) -> bool:
        """
        Check if cleanup should run based on last run time.
        Returns True if never run or if interval has passed.
        """
        config = await self._get_config()

        if not config.enabled:
            return False

        if config.last_run is None:
            return True

        # Run if interval (default 24h) has passed since last cleanup
        interval = timedelta(hours=config.interval_hours or 24)
        time_since_last = datetime.utcnow() - config.last_run
        return time_since_last >= interval

    async def _is_session_active(self) -> bool:
        """
        Check if any script recording or flow execution is active.
        Prompt 14 requirement: Session Protection.
        """
        try:
            from client_app.app.core.state import state
            from client_app.app.database.models import TaskLog
            from automatia_shared.enums import TaskStatus

            # 1. Check RPA recording
            if state.rpa and getattr(state.rpa, '_recording_active', False):
                return True
            
            # 2. Check active flow executions in DB
            async with AsyncSession(client_engine) as session:
                # We check for any task that is not in a terminal state
                active_statuses = [
                    TaskStatus.PENDING.value,
                    TaskStatus.IN_PROGRESS.value,
                    TaskStatus.PENDING_USER_VALIDATION.value
                ]
                stmt = select(TaskLog).where(TaskLog.status.in_(active_statuses))
                result = await session.exec(stmt)
                if result.first():
                    return True
        except Exception as e:
            print(f"[Cleanup] Error checking active sessions: {e}")
            # Err on the side of caution? Or proceed?
            # If we can't check, maybe it's safer to proceed if the app is otherwise idle.
            # But usually this means some init issue.
        
        return False

    def _get_files_to_delete(
        self,
        folder_path: Path,
        retention_days: int,
        patterns: List[str]
    ) -> List[Tuple[Path, int]]:
        """
        Get list of files older than retention period.
        Returns list of (file_path, file_size) tuples.
        """
        if not folder_path.exists():
            return []

        cutoff_time = datetime.now() - timedelta(days=retention_days)
        files_to_delete = []

        for pattern in patterns:
            for file_path in folder_path.rglob(pattern.strip()):
                if file_path.is_file():
                    try:
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if mtime < cutoff_time:
                            size = file_path.stat().st_size
                            files_to_delete.append((file_path, size))
                    except (OSError, PermissionError):
                        continue

        return files_to_delete

    def _delete_empty_dirs(self, folder_path: Path):
        """Delete empty subdirectories recursively."""
        if not folder_path.exists():
            return
        
        # Sort by depth to delete children before parents
        for dirpath in sorted(folder_path.rglob("*"), reverse=True):
            if dirpath.is_dir():
                try:
                    # Only delete if empty
                    if not any(dirpath.iterdir()):
                        dirpath.rmdir()
                except (OSError, PermissionError):
                    continue

    async def _run_cleanup_for_policy(self, policy: CleanupPolicy) -> Dict:
        """
        Run cleanup for a single policy.
        Returns dict with stats.
        """
        folder_path = Path(policy.folder_path)
        patterns = [p.strip() for p in policy.file_patterns.split(",")]

        files_to_delete = self._get_files_to_delete(
            folder_path,
            policy.retention_days,
            patterns
        )

        files_deleted = 0
        bytes_freed = 0
        errors = []

        for file_path, file_size in files_to_delete:
            try:
                file_path.unlink()
                files_deleted += 1
                bytes_freed += file_size
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")

        # Clean empty directories if enabled
        if policy.delete_empty_dirs:
            self._delete_empty_dirs(folder_path)

        # Log individual policy cleanup (optional, but keep it for detail)
        async with AsyncSession(client_engine) as session:
            log_entry = CleanupLog(
                folder_type=policy.folder_type,
                files_deleted=files_deleted,
                bytes_freed=bytes_freed,
                errors="\n".join(errors) if errors else None
            )
            session.add(log_entry)
            await session.commit()

        return {
            "folder_type": policy.folder_type,
            "files_deleted": files_deleted,
            "bytes_freed": bytes_freed,
            "errors": errors
        }

    async def run_cleanup(self, manual: bool = False) -> Dict:
        """
        Run cleanup for all enabled policies.
        Returns summary of cleanup operation.
        """
        config = await self._get_config()

        if not config.enabled and not manual:
            return {"skipped": True, "reason": "Cleanup disabled"}

        # Session Protection (Prompt 14)
        if not manual and await self._is_session_active():
            print("[Cleanup] Skipping cleanup: active session (recording or execution) detected.")
            return {"skipped": True, "reason": "Active session detected"}

        policies = await self._get_policies()
        enabled_policies = [p for p in policies if p.enabled]

        if not enabled_policies:
            return {"skipped": True, "reason": "No enabled policies"}

        print(f"[Cleanup] Starting cleanup for {len(enabled_policies)} folders...")

        total_files = 0
        total_bytes = 0
        results = []

        for policy in enabled_policies:
            result = await self._run_cleanup_for_policy(policy)
            results.append(result)
            total_files += result["files_deleted"]
            total_bytes += result["bytes_freed"]

        # Update config with stats
        async with AsyncSession(client_engine) as session:
            config = await session.get(CleanupSchedulerConfig, 1)
            if config:
                config.last_run = datetime.utcnow()
                config.last_files_deleted = total_files
                config.last_bytes_freed = total_bytes
                config.updated_at = datetime.utcnow()
                session.add(config)
                
                # Maintenance Log (Prompt 14)
                mb_freed = total_bytes / (1024 * 1024)
                log_msg = f"Mantenimiento {'automático' if not manual else 'manual'} realizado: {mb_freed:.2f} MB liberados"
                
                summary_log = CleanupLog(
                    folder_type="summary",
                    files_deleted=total_files,
                    bytes_freed=total_bytes,
                    message=log_msg
                )
                session.add(summary_log)
                
                await session.commit()

        summary = {
            "success": True,
            "total_files_deleted": total_files,
            "total_bytes_freed": total_bytes,
            "details": results,
            "message": log_msg
        }

        # Notify user (only if not silent background or if manual)
        if total_files > 0 or manual:
            self._notify(
                f"Limpieza completada: {total_files} archivos eliminados ({mb_freed:.1f} MB)",
                "positive"
            )

        print(f"[Cleanup] Completed: {total_files} files deleted, {total_bytes} bytes freed")

        return summary

    async def schedule_startup_cleanup(self):
        """
        Schedule cleanup to run after startup delay.
        Also starts the periodic background loop.
        Called during application startup.
        """
        config = await self._get_config()

        if not config.enabled:
            print("[Cleanup] Cleanup is disabled, skipping startup schedule")
            return

        # Start periodic loop (Prompt 14)
        if self._periodic_task is None:
            self._periodic_task = asyncio.create_task(self._periodic_cleanup_loop())
            print("[Cleanup] Periodic cleanup loop started")

        should_run = await self.should_run_cleanup()

        if not should_run:
            print("[Cleanup] Cleanup not needed (ran recently)")
            return

        delay_minutes = config.startup_delay_minutes
        print(f"[Cleanup] Scheduling startup cleanup in {delay_minutes} minutes...")

        async def delayed_cleanup():
            await asyncio.sleep(delay_minutes * 60)
            await self.run_cleanup()

        self._cleanup_task = asyncio.create_task(delayed_cleanup())

    async def _periodic_cleanup_loop(self):
        """
        Background loop for periodic cleanup (Prompt 14).
        Checks every hour if cleanup should run.
        """
        while True:
            try:
                # Check every hour if it's time to run
                await asyncio.sleep(3600)
                
                if await self.should_run_cleanup():
                    await self.run_cleanup()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Cleanup] Error in periodic loop: {e}")
                await asyncio.sleep(60) # Retry after 1 min on error

    async def update_config(self, enabled: bool, delay_minutes: int, interval_hours: int = 24):
        """Update cleanup scheduler configuration."""
        async with AsyncSession(client_engine) as session:
            config = await session.get(CleanupSchedulerConfig, 1)
            if not config:
                config = CleanupSchedulerConfig(id=1)

            config.enabled = enabled
            config.startup_delay_minutes = delay_minutes
            config.interval_hours = interval_hours
            config.updated_at = datetime.utcnow()

            session.add(config)
            await session.commit()
            
            # Restart or stop periodic task if enabled changed
            if enabled and self._periodic_task is None:
                self._periodic_task = asyncio.create_task(self._periodic_cleanup_loop())
            elif not enabled and self._periodic_task:
                self._periodic_task.cancel()
                self._periodic_task = None

    async def update_policy(
        self,
        folder_type: str,
        enabled: bool,
        retention_days: int
    ):
        """Update a specific cleanup policy."""
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(CleanupPolicy).where(CleanupPolicy.folder_type == folder_type)
            )
            policy = result.scalars().first()

            if policy:
                policy.enabled = enabled
                policy.retention_days = retention_days
                policy.updated_at = datetime.utcnow()
                session.add(policy)
                await session.commit()

    async def get_status(self) -> Dict:
        """Get current cleanup service status including storage stats."""
        config = await self._get_config()
        policies = await self._get_policies()

        # Calculate pending cleanup stats
        pending_files = 0
        pending_bytes = 0

        for policy in policies:
            if policy.enabled:
                folder_path = Path(policy.folder_path)
                patterns = [p.strip() for p in policy.file_patterns.split(",")]
                files = self._get_files_to_delete(
                    folder_path,
                    policy.retention_days,
                    patterns
                )
                pending_files += len(files)
                pending_bytes += sum(size for _, size in files)

        # Get storage usage stats (Prompt 15)
        storage_stats = await self.get_storage_stats()

        return {
            "enabled": config.enabled,
            "interval_hours": config.interval_hours,
            "startup_delay_minutes": config.startup_delay_minutes,
            "last_run": config.last_run.isoformat() if config.last_run else None,
            "last_files_deleted": config.last_files_deleted,
            "last_bytes_freed": config.last_bytes_freed,
            "pending_files": pending_files,
            "pending_bytes": pending_bytes,
            "policies": [
                {
                    "folder_type": p.folder_type,
                    "folder_path": p.folder_path,
                    "enabled": p.enabled,
                    "retention_days": p.retention_days
                }
                for p in policies
            ],
            "storage": storage_stats
        }

    async def get_storage_stats(self) -> Dict:
        """
        Calculate storage usage statistics for key folders.
        Also counts 'orphan' files (Prompt 15).
        """
        stats = {
            "categories": [
                {"id": "executions", "label": "Ejecuciones", "path": "data/executions", "size_bytes": 0},
                {"id": "automations", "label": "Automatizaciones", "path": "data/automations", "size_bytes": 0},
                {"id": "uploads", "label": "Cargas (Uploads)", "path": "data/uploads", "size_bytes": 0},
                {"id": "screenshots", "label": "Capturas (RPA)", "path": "data/screenshots", "size_bytes": 0}
            ],
            "orphan_count": 0,
            "total_bytes": 0
        }

        # 1. Calculate folder sizes
        for cat in stats["categories"]:
            path = Path(cat["path"])
            if path.exists():
                # Recursive size calculation
                size = 0
                for f in path.rglob('*'):
                    if f.is_file():
                        try:
                            size += f.stat().st_size
                        except: pass
                cat["size_bytes"] = size
                stats["total_bytes"] += size

        # 2. Count Orphans (Prompt 15 requirement)
        try:
            async with AsyncSession(client_engine) as session:
                # 2.1 Uploads Orphans
                path_uploads = Path("data/uploads")
                if path_uploads.exists():
                    from client_app.app.database.models import ExtractionLog
                    result = await session.exec(select(ExtractionLog.filename))
                    db_files = set(result.all())
                    for f in path_uploads.glob('*'):
                        if f.is_file() and f.name not in db_files:
                            stats["orphan_count"] += 1

                # 2.2 Automations Orphans
                from client_app.app.database.models import CustomScript
                result_scripts = await session.exec(select(CustomScript.script_path))
                result_docs = await session.exec(select(CustomScript.doc_path))
                db_paths = set(p for p in result_scripts.all() if p) | set(p for p in result_docs.all() if p)
                
                path_automations = Path("data/automations")
                if path_automations.exists():
                    for f in path_automations.rglob('*'):
                        if f.is_file() and not f.name.startswith('__'):
                            try:
                                # Try to match relative to data/
                                rel_p = str(f.relative_to(Path("data"))).replace("\\", "/")
                                if rel_p not in db_paths:
                                    # Try match relative to automations/
                                    rel_p_alt = str(f.relative_to(Path("data/automations"))).replace("\\", "/")
                                    # Some models might store paths relative to automations/ or just filename
                                    if rel_p_alt not in db_paths and f.name not in db_paths:
                                        stats["orphan_count"] += 1
                            except: pass
        except Exception as e:
            print(f"[Cleanup] Error calculating orphans: {e}")

        return stats

    async def get_cleanup_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent cleanup logs."""
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(CleanupLog)
                .order_by(CleanupLog.timestamp.desc())
                .limit(limit)
            )
            logs = result.all()

            return [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "folder_type": log.folder_type,
                    "files_deleted": log.files_deleted,
                    "bytes_freed": log.bytes_freed,
                    "message": log.message,
                    "errors": log.errors
                }
                for log in logs
            ]


# Global singleton instance
cleanup_service = CleanupService()
