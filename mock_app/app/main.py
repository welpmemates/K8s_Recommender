from fastapi import FastAPI
import time
import random
import hashlib

app = FastAPI()

# GLOBAL memory holder
MEMORY_HOG = []

@app.get("/work")
def do_work(size: int = 1000, sleep: float = 0.01, retain: bool = False):
    data = []

    for _ in range(size):
        s = str(random.random()).encode()
        hashlib.sha256(s).hexdigest()
        data.append(s)

    if retain:
        # retain memory across requests
        MEMORY_HOG.append(data)

    time.sleep(sleep)

    return {
        "items": size,
        "retained_chunks": len(MEMORY_HOG),
        "sleep": sleep
    }
