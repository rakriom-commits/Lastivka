# -*- coding: utf-8 -*-
import hashlib, os, zipfile
from datetime import datetime
from typing import Dict, List, Optional

class BackupRunner:
    def _sha256(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, 'rb') as fh:
            for chunk in iter(lambda: fh.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def _zip_plain(self, files: List[str], target_path: str) -> None:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with zipfile.ZipFile(target_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                if os.path.exists(f):
                    zf.write(f, arcname=os.path.relpath(f, start=os.getcwd()))

    def _zip_encrypted_pyzipper(self, files: List[str], target_path: str, password: str) -> bool:
        try:
            import pyzipper
        except Exception:
            return False
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        keep = [f for f in files if os.path.exists(f)]
        with pyzipper.AESZipFile(target_path, 'w',
                                 compression=pyzipper.ZIP_DEFLATED,
                                 encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode('utf-8'))
            zf.setencryption(pyzipper.WZ_AES, nbits=256)
            for f in keep:
                zf.write(f, arcname=os.path.relpath(f, start=os.getcwd()))
        return True

    def run(self, manifest: Dict, target_path: str, encrypt: bool = False, password: Optional[str] = None) -> Dict:
        files: List[str] = manifest.get("files", [])
        enc_used = False
        method = "none"
        if encrypt and password:
            enc_used = self._zip_encrypted_pyzipper(files, target_path, password)
            method = "pyzipper-aes256" if enc_used else "none"
        if not enc_used:
            self._zip_plain(files, target_path)

        exists = os.path.exists(target_path)
        return {
            "status": "ok" if exists else "error",
            "time": datetime.utcnow().isoformat() + "Z",
            "size": os.path.getsize(target_path) if exists else 0,
            "hash": self._sha256(target_path) if exists else "",
            "location": target_path,
            "files_count": len([f for f in files if os.path.exists(f)]),
            "encrypted": enc_used,
            "method": method,
        }

BACKUP = BackupRunner()
