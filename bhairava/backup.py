import os
import shutil
import tarfile
import hashlib
import base64
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


class Backup:
    @staticmethod
    def generate_key_file(key_path):
        import base64
        import os
        key_dir = os.path.dirname(os.path.abspath(os.path.expanduser(key_path)))
        if key_dir:
            os.makedirs(key_dir, exist_ok=True)
        # Generate 16 bytes random key, base64 encoded
        random_key = os.urandom(16)
        encoded = base64.b64encode(random_key)
        with open(key_path, "wb") as f:
            f.write(encoded)

    def __init__(self,
                 backup_dir="logs/backup",
                 remote_dir="logs/remote_storage",
                 key_path=".secure_keys/vyom_backup.key",
                 retention_limit=5):

        self.backup_dir = backup_dir
        self.remote_dir = remote_dir
        self.key_path = os.path.abspath(os.path.expanduser(key_path))
        self.retention_limit = retention_limit

        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.remote_dir, exist_ok=True)

        if not os.path.exists(self.key_path):
            raise RuntimeError("Backup encryption key file missing.")

    def _load_key(self):
        with open(self.key_path, "rb") as f:
            return base64.b64decode(f.read().strip())

    def _encrypt_file(self, file_path, key):
        iv = os.urandom(16)

        with open(file_path, "rb") as f:
            data = f.read()

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()

        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )

        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        encrypted_path = file_path + ".enc"

        with open(encrypted_path, "wb") as f:
            f.write(iv + encrypted)

        return encrypted_path

    def _hash_file(self, file_path):
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _apply_retention_policy(self):
        backups = sorted(
            [f for f in os.listdir(self.backup_dir) if f.endswith(".enc")]
        )

        while len(backups) > self.retention_limit:
            oldest = backups.pop(0)
            os.remove(os.path.join(self.backup_dir, oldest))

    def create_backup(self, details=None):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        archive_name = f"snapshot_{timestamp}.tar.gz"
        archive_path = os.path.join(self.backup_dir, archive_name)

        with tarfile.open(archive_path, "w:gz") as tar:
            if os.path.exists("config"):
                tar.add("config")
            if os.path.exists("integrity_baseline.json"):
                tar.add("integrity_baseline.json")

        key = self._load_key()
        encrypted_path = self._encrypt_file(archive_path, key)
        os.remove(archive_path)

        file_hash = self._hash_file(encrypted_path)

        shutil.copy(encrypted_path, self.remote_dir)

        print(f"[BACKUP] Encrypted backup created: {encrypted_path}")
        print(f"[BACKUP] SHA256: {file_hash}")

        self._apply_retention_policy()