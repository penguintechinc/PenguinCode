# Security Guidelines

PenguinCode is designed to generate secure code by default. The Executor agent follows OWASP Top 10 guidelines and language-specific security best practices.

## Table of Contents

- [OWASP Top 10 Compliance](#owasp-top-10-compliance)
- [Language-Specific Security](#language-specific-security)
- [Infrastructure as Code Security](#infrastructure-as-code-security)
- [Security Configuration](#security-configuration)
- [Reporting Vulnerabilities](#reporting-vulnerabilities)

---

## OWASP Top 10 Compliance

The Executor agent is instructed to follow OWASP Top 10 (2021) guidelines when generating code:

### A01: Broken Access Control

**What we do:**
- Generate proper authorization checks before sensitive operations
- Implement deny-by-default access patterns
- Use indirect object references (UUIDs) instead of sequential IDs
- Server-side permission validation

**Example - FastAPI:**
```python
from fastapi import Depends, HTTPException, status
from uuid import UUID

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    user = await verify_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

@app.get("/users/{user_id}")
async def get_user(
    user_id: UUID,  # UUID, not int
    current_user: User = Depends(get_current_user)
):
    if not current_user.can_view_user(user_id):
        raise HTTPException(status_code=403)
    return await get_user_by_id(user_id)
```

### A02: Cryptographic Failures

**What we do:**
- Never hardcode secrets in generated code
- Use environment variables or secret managers
- Modern encryption algorithms (AES-256, bcrypt/argon2)
- Proper password hashing with salts

**Example - Password hashing:**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

### A03: Injection

**What we do:**
- Parameterized queries for all database operations
- Input validation and sanitization
- Context-aware output escaping
- No shell command construction with user input

**Example - SQL (SQLAlchemy):**
```python
# GOOD: Parameterized query
user = session.execute(
    select(User).where(User.email == email)
).scalar_one_or_none()

# BAD: String concatenation (never generated)
# query = f"SELECT * FROM users WHERE email = '{email}'"
```

### A04: Insecure Design

**What we do:**
- Rate limiting on authentication endpoints
- CSRF protection for state-changing operations
- Secure session management
- Principle of least privilege

### A05: Security Misconfiguration

**What we do:**
- No debug info in production responses
- Secure HTTP headers by default
- Minimal service exposure

**Example - FastAPI security headers:**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.example.com"])
app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET"])

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

### A06: Vulnerable Components

**What we do:**
- Recommend well-maintained libraries
- Suggest version pinning
- Warn about known vulnerabilities

### A07: Authentication Failures

**What we do:**
- Strong password policies
- Account lockout mechanisms
- Secure session tokens
- Proper token expiration

### A08: Data Integrity Failures

**What we do:**
- Validate all external data
- Suggest integrity checks

### A09: Logging & Monitoring

**What we do:**
- Log security events
- Never log sensitive data
- Structured logging with context

**Example:**
```python
import structlog

logger = structlog.get_logger()

async def login(email: str, password: str):
    user = await get_user(email)
    if not user or not verify_password(password, user.password_hash):
        logger.warning("login_failed", email=email)  # Log email, not password
        raise HTTPException(status_code=401)

    logger.info("login_success", user_id=str(user.id))
    return create_token(user)
```

### A10: SSRF

**What we do:**
- URL validation before requests
- Domain allowlists
- Block internal IP ranges

---

## Language-Specific Security

### Python

| Risk | Mitigation |
|------|------------|
| Insecure random | Use `secrets` module, not `random` |
| Command injection | Use `subprocess` with `shell=False` and list args |
| Code injection | Avoid `eval()`, `exec()`, `pickle.loads()` |
| XSS | Use `html.escape()` for HTML output |

### JavaScript/TypeScript

| Risk | Mitigation |
|------|------------|
| XSS | Use `textContent` instead of `innerHTML` |
| Input validation | Use Zod, Yup, or similar |
| URL injection | Use `encodeURIComponent()` |
| Cookie theft | Set `httpOnly` and `secure` flags |

### Go

| Risk | Mitigation |
|------|------------|
| SQL injection | Use `database/sql` with `?` placeholders |
| Command injection | Use `exec.Command()` with separate args |
| Path traversal | Use `filepath.Clean()` and validate paths |

### Rust

| Risk | Mitigation |
|------|------------|
| Memory safety | Leverage ownership system (automatic) |
| SQL injection | Use `sqlx` or `diesel` with parameters |
| Untrusted input | Use `serde` with validation |

---

## Infrastructure as Code Security

### OpenTofu/Terraform

**Secrets Management:**
```hcl
# GOOD: Use variables with sensitive flag
variable "db_password" {
  type      = string
  sensitive = true
}

resource "aws_db_instance" "main" {
  password = var.db_password
}

# BAD: Hardcoded (never generated)
# password = "supersecret123"
```

**State Security:**
```hcl
# Use encrypted backend
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

**Resource Security:**
```hcl
# Enable encryption by default
resource "aws_s3_bucket" "data" {
  bucket = "my-secure-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Use private subnets
resource "aws_instance" "app" {
  subnet_id                   = aws_subnet.private.id
  associate_public_ip_address = false
}
```

### Ansible

**Vault Usage:**
```yaml
# Create encrypted variables
# ansible-vault create secrets.yml

# Reference in playbook
- name: Deploy application
  hosts: webservers
  vars_files:
    - secrets.yml
  tasks:
    - name: Configure database
      template:
        src: db.conf.j2
        dest: /etc/app/db.conf
      no_log: true  # Don't log secrets
```

**Privilege Escalation:**
```yaml
# Use become only when necessary
- name: Install packages
  become: true
  ansible.builtin.apt:
    name: nginx
    state: present

- name: Copy config (no root needed)
  become: false
  ansible.builtin.copy:
    src: nginx.conf
    dest: /etc/nginx/nginx.conf
```

---

## Security Configuration

### Enable Security Scanning

```yaml
# config.yaml
security:
  enabled: true
  scan_on_write: true      # Scan generated code
  block_insecure: false    # Warn but don't block

  rules:
    - no_hardcoded_secrets
    - no_sql_injection
    - no_command_injection
    - use_parameterized_queries
    - use_secure_random
```

### Custom Rules

```yaml
security:
  custom_rules:
    - pattern: "password\\s*=\\s*['\"][^'\"]+['\"]"
      message: "Hardcoded password detected"
      severity: high

    - pattern: "eval\\(.*\\$"
      message: "Eval with variable input"
      severity: critical
```

---

## Reporting Vulnerabilities

If you discover a security vulnerability in PenguinCode:

1. **Do not** open a public issue
2. Email security@penguintech.io
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you on responsible disclosure.

---

**Last Updated**: 2025-12-28
**See Also**: [AGENTS.md](AGENTS.md), [USAGE.md](USAGE.md)
