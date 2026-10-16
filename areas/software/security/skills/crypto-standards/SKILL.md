---
name: crypto-standards
description: "Defines approved cryptographic algorithms, Argon2id password storage, and envelope encryption; use when implementing password storage, data encryption, token signing, or key management."
---

# Skill: Cryptography Standards

## When to load

When implementing password storage, data encryption, token signing, or key management.

## Approved Algorithms

| Use Case | Approved | Forbidden |
|:---|:---|:---|
| Password hashing | Argon2id, bcrypt (cost≥12) | MD5, SHA-1, unsalted SHA-256 |
| Data encryption | AES-256-GCM, ChaCha20-Poly1305 | DES, 3DES, AES-ECB |
| Token signing | RS256, ES256 | HS256 in distributed systems |
| TLS | TLS 1.2+, prefer TLS 1.3 | SSLv3, TLS 1.0, TLS 1.1 |

## Password Storage (Argon2id)

```python
from argon2 import PasswordHasher

ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
hashed = ph.hash(plain_password)

try:
    ph.verify(stored_hash, provided_password)
    if ph.check_needs_rehash(stored_hash):
        new_hash = ph.hash(provided_password)
        db.update_password_hash(user_id, new_hash)
except VerifyMismatchError:
    raise InvalidCredentials()
```

## Envelope Encryption

```
Never encrypt data directly with a master key.

1. Generate unique Data Encryption Key (DEK) per record
2. Encrypt data with DEK (AES-256-GCM)
3. Encrypt DEK with Key Encryption Key (KEK) in KMS
4. Store: encrypted_data + encrypted_DEK + IV
```
