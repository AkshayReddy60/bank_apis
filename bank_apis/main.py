import rsa
import psycopg2
import jwt
import datetime
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os

# *JWT Secret Key*
JWT_SECRET = "Akshay"
JWT_ALGORITHM = "HS256"

# *Load or Generate RSA Keys*
KEY_DIR = "keys"
PUBLIC_KEY_FILE = os.path.join(KEY_DIR, "public.pem")
PRIVATE_KEY_FILE = os.path.join(KEY_DIR, "private.pem")

if not os.path.exists(KEY_DIR):
    os.makedirs(KEY_DIR)

if os.path.exists(PUBLIC_KEY_FILE) and os.path.exists(PRIVATE_KEY_FILE):
    with open(PUBLIC_KEY_FILE, "rb") as pub_file, open(PRIVATE_KEY_FILE, "rb") as priv_file:
        public_key = rsa.PublicKey.load_pkcs1(pub_file.read())
        private_key = rsa.PrivateKey.load_pkcs1(priv_file.read())
else:
    public_key, private_key = rsa.newkeys(512)
    with open(PUBLIC_KEY_FILE, "wb") as pub_file, open(PRIVATE_KEY_FILE, "wb") as priv_file:
        pub_file.write(public_key.save_pkcs1())
        priv_file.write(private_key.save_pkcs1())

# *FastAPI app*
app = FastAPI()

# *Database Configuration*
DB_CONFIG = {
    "dbname": "Bankenq",
    "user": "postgres",
    "password": "Akshay@2003",
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# *Ensure tables exist*
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            account_id INT UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_accounts (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id) ON DELETE CASCADE,
            balance FLOAT DEFAULT 0.0
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

create_tables()

# *Pydantic Models*
class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Transaction(BaseModel):
    amount: float

# *Encryption and Decryption*
def encrypt_password(password: str) -> str:
    return rsa.encrypt(password.encode("utf-8"), public_key).hex()

def decrypt_password(encrypted_password: str) -> str:
    try:
        encrypted_bytes = bytes.fromhex(encrypted_password)
        return rsa.decrypt(encrypted_bytes, private_key).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid password or decryption failed")

# *JWT Token Generation and Verification*
def create_jwt_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: Optional[str] = Header(None)):
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# *Register User*
@app.post("/register")
def register_user(user: UserRegister):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
    if cursor.fetchone():
        return {"message": "Account already exists, please sign in"}
    encrypted_password = encrypt_password(user.password)
    cursor.execute("INSERT INTO bank_accounts (balance) VALUES (0.0) RETURNING id")
    account_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO users (username, password, account_id) VALUES (%s, %s, %s)",
                   (user.username, encrypted_password, account_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Account created successfully"}

# *Sign In*
@app.post("/signin")
def sign_in(user: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = %s", (user.username,))
    user_record = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user_record or decrypt_password(user_record[0]) != user.password:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    token = create_jwt_token(user.username)
    return {"message": "Sign-in successful", "token": token}

# *Deposit Money*
@app.post("/deposit")
def deposit_money(transaction: Transaction, username: str = Depends(verify_jwt_token)):
    if transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Deposit amount must be positive")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_id FROM users WHERE username = %s", (username,))
    account_id = cursor.fetchone()[0]
    cursor.execute("UPDATE bank_accounts SET balance = balance + %s WHERE id = %s", (transaction.amount, account_id))
    conn.commit()
    cursor.execute("SELECT balance FROM bank_accounts WHERE id = %s", (account_id,))
    new_balance = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return {"message": "Deposit successful", "balance": new_balance}

# *Get Account Balance*
@app.get("/balance")
def get_balance(username: str = Depends(verify_jwt_token)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_id FROM users WHERE username = %s", (username,))
    account_id = cursor.fetchone()[0]
    cursor.execute("SELECT balance FROM bank_accounts WHERE id = %s", (account_id,))
    balance = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return {"message": "Your current balance", "balance": balance}

