---
name: auth-patterns
description: "Provides authentication and authorization patterns for JWT handling and RBAC; use when implementing login, token management, OAuth integration, or RBAC, or when reviewing auth code."
---

# Skill: Authentication & Authorization Patterns

## When to load

When implementing login, token management, OAuth integration, RBAC, or reviewing auth code.

## JWT Best Practices

```python
def create_access_token(user_id: str) -> str:
    return jwt.encode(
        payload={
            "sub": user_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=15),  # Short expiry
            "jti": str(uuid.uuid4()),  # Unique ID for revocation
            "type": "access",          # Prevent refresh token as access token
        },
        key=settings.JWT_PRIVATE_KEY,
        algorithm="RS256",  # Asymmetric. Never HS256 in distributed systems.
    )
```

**Anti-patterns**: No `exp` claim; storing JWT in `localStorage`; using `alg: none`; sensitive data in payload.

## RBAC Pattern

```python
PERMISSIONS = {
    "invoices:read":   ["viewer", "editor", "admin"],
    "invoices:create": ["editor", "admin"],
    "invoices:delete": ["admin"],
}

def require_permission(permission: str):
    def dependency(current_user: User = Depends(get_current_user)):
        allowed_roles = PERMISSIONS.get(permission, [])
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403)
        return current_user
    return dependency
```
