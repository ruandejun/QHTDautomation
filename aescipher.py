"""
aescipher.py - AES-256 CBC Encryption/Decryption utility
Used throughout the antidetect-automatic project for encrypting SSH credentials
and other sensitive data stored in SQLite databases.
"""
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto import Random


class AESCipher:
    """
    AES-256 CBC encryption/decryption with PKCS7 padding.
    
    Usage:
        cipher = AESCipher('your-secret-key')
        encrypted = cipher.encrypt('hello world')
        decrypted = cipher.decrypt(encrypted)
    """

    def __init__(self, key: str):
        self.bs = AES.block_size  # 16 bytes
        # SHA-256 hash of key to get exactly 32 bytes
        self.key = hashlib.sha256(key.encode('utf-8')).digest()

    def encrypt(self, raw: str) -> str:
        """Encrypt a plaintext string, return base64-encoded ciphertext."""
        if not raw:
            return ''
        raw = self._pad(raw)
        iv = Random.new().read(self.bs)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(raw.encode('utf-8'))
        return base64.b64encode(iv + encrypted).decode('utf-8')

    def decrypt(self, enc: str) -> str:
        """Decrypt a base64-encoded ciphertext, return plaintext string."""
        if not enc:
            return ''
        try:
            enc_bytes = base64.b64decode(enc)
            iv = enc_bytes[:self.bs]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(enc_bytes[self.bs:])
            return self._unpad(decrypted).decode('utf-8')
        except Exception as e:
            # Return the raw value if decryption fails (might be plaintext already)
            try:
                return enc.strip()
            except Exception:
                return ''

    def _pad(self, s: str) -> str:
        """PKCS7 padding."""
        pad_len = self.bs - len(s.encode('utf-8')) % self.bs
        return s + chr(pad_len) * pad_len

    @staticmethod
    def _unpad(s: bytes) -> bytes:
        """Remove PKCS7 padding."""
        pad_len = s[-1]
        if pad_len > AES.block_size:
            return s
        return s[:-pad_len]


if __name__ == '__main__':
    # Quick self-test
    cipher = AESCipher('stay123!@#')
    plaintext = 'test_password_123'
    enc = cipher.encrypt(plaintext)
    dec = cipher.decrypt(enc)
    assert dec == plaintext, f"Decrypt failed: got '{dec}', expected '{plaintext}'"
    print(f'[OK] AESCipher self-test passed')
    print(f'  plaintext : {plaintext}')
    print(f'  encrypted : {enc}')
    print(f'  decrypted : {dec}')
