"""
Simple SMTP connectivity checker.
Run this to verify DNS resolution and TCP connectivity to the configured SMTP server.
"""
import os
import socket
from dotenv import load_dotenv

load_dotenv()

MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
TIMEOUT = int(os.getenv('MAIL_TIMEOUT', 10))

print(f"Checking SMTP server {MAIL_SERVER}:{MAIL_PORT} (timeout={TIMEOUT}s)")

try:
    ip = socket.gethostbyname(MAIL_SERVER)
    print(f"DNS resolution OK: {MAIL_SERVER} -> {ip}")
except Exception as e:
    print(f"DNS resolution failed for {MAIL_SERVER}: {e}")
    raise SystemExit(1)

try:
    with socket.create_connection((MAIL_SERVER, MAIL_PORT), timeout=TIMEOUT) as s:
        print(f"TCP connect OK to {MAIL_SERVER}:{MAIL_PORT}")
except Exception as e:
    print(f"TCP connect failed to {MAIL_SERVER}:{MAIL_PORT}: {e}")
    raise SystemExit(2)

print("SMTP connectivity check passed.")
