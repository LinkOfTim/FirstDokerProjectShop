import os
import socket
import sys
import time
from urllib.parse import urlparse


def wait_for_db(timeout: int = 60):
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@catalog-db:5432/catalog")
    parsed = urlparse(url)
    host = parsed.hostname or "catalog-db"
    port = parsed.port or 5432

    start = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"DB reachable at {host}:{port}")
                return True
        except OSError:
            if (time.time() - start) > timeout:
                print(f"Timed out waiting for DB at {host}:{port}", file=sys.stderr)
                return False
            print("Waiting for DB...", flush=True)
            time.sleep(1)


if __name__ == "__main__":
    ok = wait_for_db()
    sys.exit(0 if ok else 1)

