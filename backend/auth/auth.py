import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
import jwt

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 30  # 30 days

# Supabase Configuration (optional - for cloud sync)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Local file fallback for user data (if no Supabase)
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserPreferences(BaseModel):
    subscriptions: list[int] = []
    recent_searches: list[dict] = []
    last_platform: Optional[int] = None
    theme: str = "dark"

def hash_password(password: str) -> str:
    """Hash password with salt."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{pwd_hash.hex()}"

def verify_password(password: str, stored: str) -> bool:
    """Verify password against stored hash."""
    try:
        salt, pwd_hash = stored.split(":")
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return new_hash.hex() == pwd_hash
    except:
        return False

def create_token(user_id: str, email: str) -> str:
    """Create JWT token."""
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# User storage (local JSON fallback)
def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users: dict):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def get_user_by_email(email: str) -> Optional[dict]:
    users = load_users()
    return users.get(email.lower())

def create_user(email: str, password: str, name: str = None) -> dict:
    users = load_users()
    email = email.lower()
    
    if email in users:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = secrets.token_urlsafe(16)
    user = {
        "id": user_id,
        "email": email,
        "name": name or email.split("@")[0],
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow().isoformat(),
        "preferences": UserPreferences().dict()
    }
    users[email] = user
    save_users(users)
    return user

def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = get_user_by_email(email)
    if user and verify_password(password, user["password_hash"]):
        return user
    return None

def update_user_preferences(email: str, preferences: dict) -> dict:
    users = load_users()
    email = email.lower()
    if email in users:
        users[email]["preferences"] = {**users[email].get("preferences", {}), **preferences}
        users[email]["updated_at"] = datetime.utcnow().isoformat()
        save_users(users)
        return users[email]["preferences"]
    raise HTTPException(status_code=404, detail="User not found")

def get_user_preferences(email: str) -> dict:
    user = get_user_by_email(email)
    if user:
        return user.get("preferences", UserPreferences().dict())
    return UserPreferences().dict()

# Dependency for protected routes
async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    user = get_user_by_email(payload["email"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Optional: Supabase sync functions (if configured)
async def sync_to_supabase(user: dict):
    """Sync user preferences to Supabase."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return False
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{user['id']}",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "preferences": user.get("preferences", {}),
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
        return True
    except:
        return False

async def load_from_supabase(user_id: str) -> Optional[dict]:
    """Load user preferences from Supabase."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}&select=preferences",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0].get("preferences")
    except:
        pass
    return None