import secrets
import string
import bcrypt

def generate_api_key_raw(length=40) -> str:
    """Genera una clave alfanumérica segura."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_api_key(raw_key: str) -> str:
    """Devuelve el hash bcrypt de la clave."""
    # bcrypt.hashpw espera bytes, por eso codificamos
    return bcrypt.hashpw(raw_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """Verifica una clave plana contra un hash bcrypt."""
    return bcrypt.checkpw(raw_key.encode('utf-8'), hashed_key.encode('utf-8'))