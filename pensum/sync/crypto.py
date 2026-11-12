"""Decompress and decrypt sync payloads (`C` and `E` in the envelope), as
Super Productivity 20.0.0 writes them (packages/sync-core/src:
compression.ts, encryption.ts, encryption/argon2.ts, encryption/legacy.ts,
encryption/web-crypto.ts):

- compressed: base64 of gzip of the UTF-8 text;
- encrypted: base64 of `[salt 16][iv 12][AES-256-GCM ciphertext + tag 16]`,
  key = Argon2id(password, salt, 3 passes, 64 MiB, 1 lane, 32 bytes);
  older files `[iv 12][ciphertext + tag]` with key =
  PBKDF2-SHA256(password, salt = password, 1000 rounds); Super
  Productivity tries the older layout when the newer one fails;
- compression is applied before encryption, so decryption comes first.

Argon2id comes from argon2-cffi-bindings (bundled), AES-GCM from the
runtime's OpenSSL (libcrypto) through ctypes; PBKDF2 from hashlib."""
import base64
import binascii
import ctypes
import ctypes.util
import gzip
import hashlib
import re
from functools import lru_cache

from pensum.sync import SyncError

SALT_LENGTH = 16
IV_LENGTH = 12
TAG_LENGTH = 16
KEY_LENGTH = 32
ARGON2_PASSES = 3
ARGON2_MEMORY_KIB = 65536
ARGON2_LANES = 1
LEGACY_ROUNDS = 1000


class WrongPassword(SyncError):
    """The data can't be decrypted with this password."""


def b64decode(text):
    """Base64 as Super Productivity reads it: stray characters dropped,
    padding repaired (sanitizeBase64)."""
    cleaned = re.sub(r"[^A-Za-z0-9+/=]", "", text)
    remainder = len(cleaned) % 4
    if remainder == 1:
        cleaned = cleaned[:-1]
    elif remainder:
        cleaned += "=" * (4 - remainder)
    try:
        return base64.b64decode(cleaned)
    except binascii.Error as error:
        raise SyncError("A sync file is damaged (base64).") from error


def decompress(text):
    try:
        return gzip.decompress(b64decode(text)).decode("utf-8")
    except (OSError, EOFError, UnicodeDecodeError) as error:
        raise SyncError("A sync file is damaged (gzip).") from error


def decrypt(text, password, cache=None):
    """The plain text of an encrypted payload. `cache` (a dict) keeps
    derived keys by salt between files of one read."""
    data = b64decode(text)
    if len(data) >= SALT_LENGTH + IV_LENGTH + TAG_LENGTH:
        salt = data[:SALT_LENGTH]
        key = None if cache is None else cache.get(salt)
        if key is None:
            key = argon2id(password.encode("utf-8"), salt)
            if cache is not None:
                cache[salt] = key
        plain = aes_gcm_decrypt(key, data[SALT_LENGTH:SALT_LENGTH + IV_LENGTH],
                                data[SALT_LENGTH + IV_LENGTH:])
        if plain is not None:
            return _text(plain)
    if len(data) >= IV_LENGTH + TAG_LENGTH:
        secret = password.encode("utf-8")
        key = hashlib.pbkdf2_hmac("sha256", secret, secret, LEGACY_ROUNDS, KEY_LENGTH)
        plain = aes_gcm_decrypt(key, data[:IV_LENGTH], data[IV_LENGTH:])
        if plain is not None:
            return _text(plain)
        raise WrongPassword("The encryption password is wrong.")
    raise SyncError("A sync file is damaged (too short to be encrypted).")


def _text(plain):
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SyncError("A sync file is damaged (not text).") from error


# --- Argon2id ---------------------------------------------------------------

def argon2id(secret, salt):
    try:
        from _argon2_cffi_bindings import ffi, lib
    except ImportError as error:
        raise SyncError("Encrypted sync files need the Argon2 module, which "
                        "is missing.") from error
    out = ffi.new("uint8_t[]", KEY_LENGTH)
    result = lib.argon2_hash(ARGON2_PASSES, ARGON2_MEMORY_KIB, ARGON2_LANES,
                             secret, len(secret), salt, len(salt), out, KEY_LENGTH,
                             ffi.NULL, 0, lib.Argon2_id, lib.ARGON2_VERSION_13)
    if result != lib.ARGON2_OK:
        raise SyncError("The encryption key can't be derived "
                        f"(Argon2 error {result}).")
    return bytes(ffi.buffer(out, KEY_LENGTH))


# --- AES-256-GCM through OpenSSL ------------------------------------------

EVP_CTRL_GCM_SET_IVLEN = 0x9
EVP_CTRL_GCM_SET_TAG = 0x11


@lru_cache(maxsize=1)
def _libcrypto():
    for name in ("libcrypto.so.3", ctypes.util.find_library("crypto")):
        if not name:
            continue
        try:
            lib = ctypes.CDLL(name)
        except OSError:
            continue
        lib.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
        lib.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]
        lib.EVP_aes_256_gcm.restype = ctypes.c_void_p
        lib.EVP_DecryptInit_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                           ctypes.c_char_p, ctypes.c_char_p]
        lib.EVP_CIPHER_CTX_ctrl.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                            ctypes.c_void_p]
        lib.EVP_DecryptUpdate.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                          ctypes.POINTER(ctypes.c_int), ctypes.c_char_p,
                                          ctypes.c_int]
        lib.EVP_DecryptFinal_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                            ctypes.POINTER(ctypes.c_int)]
        return lib
    raise SyncError("Encrypted sync files need OpenSSL, which is missing.")


def aes_gcm_decrypt(key, iv, sealed):
    """The plain bytes, or None when the tag does not match (wrong key)."""
    if len(sealed) < TAG_LENGTH:
        return None
    lib = _libcrypto()
    body, tag = sealed[:-TAG_LENGTH], sealed[-TAG_LENGTH:]
    ctx = lib.EVP_CIPHER_CTX_new()
    if not ctx:
        raise SyncError("OpenSSL failed.")
    try:
        out = ctypes.create_string_buffer(len(body) + 16)
        length = ctypes.c_int(0)
        tag_buffer = ctypes.create_string_buffer(tag, TAG_LENGTH)
        ok = (lib.EVP_DecryptInit_ex(ctx, lib.EVP_aes_256_gcm(), None, None, None) == 1
              and lib.EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, len(iv), None) == 1
              and lib.EVP_DecryptInit_ex(ctx, None, None, key, iv) == 1
              and lib.EVP_DecryptUpdate(ctx, out, ctypes.byref(length), body, len(body)) == 1)
        if not ok:
            raise SyncError("OpenSSL failed.")
        written = length.value
        if lib.EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, TAG_LENGTH, tag_buffer) != 1:
            raise SyncError("OpenSSL failed.")
        rest = ctypes.c_int(0)
        if lib.EVP_DecryptFinal_ex(ctx, ctypes.addressof(out) + written,
                                   ctypes.byref(rest)) != 1:
            return None
        return out.raw[:written + rest.value]
    finally:
        lib.EVP_CIPHER_CTX_free(ctx)
