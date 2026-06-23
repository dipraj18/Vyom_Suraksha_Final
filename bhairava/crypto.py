from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64


class CryptoEngine:
    def __init__(self):
        self.key = get_random_bytes(16)  # 128-bit AES key

    def encrypt(self, plaintext):
        cipher = AES.new(self.key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode())
        return base64.b64encode(cipher.nonce + tag + ciphertext).decode()

    def decrypt(self, encrypted_data):
        raw = base64.b64decode(encrypted_data.encode())
        nonce = raw[:16]
        tag = raw[16:32]
        ciphertext = raw[32:]
        cipher = AES.new(self.key, AES.MODE_EAX, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode()