# -*- coding: utf-8 -*-
import logging, os
from datetime import datetime
from typing import Dict
from core.event_bus import BUS
from security.backup_runner import BACKUP

class BackupOrchestrator:
    def schedule_tick(self) -> None:
        pass

    def run_daily(self) -> None:
        BUS.publish("core.backup.run", {"scope": "daily", "mode": "incremental"})

    def run_weekly(self) -> None:
        BUS.publish("core.backup.run", {"scope": "weekly", "mode": "full"})

    def on_backup_run(self, payload: Dict) -> None:
        manifest = {
            "files": [
                os.path.join("lastivka_core", "config", "trusts.yaml"),
                os.path.join("lastivka_core", "logs", "lastivka.log"),
                os.path.join("lastivka_core", "logs", "memory_store.json"),
                os.path.join("lastivka_core", "logs", "security_events.json"),
                os.path.join("lastivka_core", "memory", "manager.py"),
            ]
        }
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = os.path.join("lastivka_core", "logs", "backups")
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, f"backup_{ts}.zip")

        password = os.getenv("LASTIVKA_BACKUP_PWD")
        report = BACKUP.run(
            manifest=manifest,
            target_path=target_file,
            encrypt=bool(password),
            password=password
        )
        logging.info("BACKUP report: %s", report)
        BUS.publish("core.backup.report", report)

    def verify_sandbox(self, report: Dict) -> None:
        pass

ORCH = BackupOrchestrator()
