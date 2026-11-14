import threading
import time


class TokenBucket:
    """Spaces calls to respect an RPM limit. burst=1 means no bursting (safest on free tiers)."""

    def __init__(self, rpm: float, burst: int = 1, clock=time.monotonic, sleep=time.sleep):
        self.rate = rpm / 60.0
        self.capacity = max(1, burst)
        self.tokens = float(self.capacity)
        self.clock, self.sleep = clock, sleep
        self.updated = clock()
        self.lock = threading.Lock()

    def acquire(self) -> float:
        waited = 0.0
        while True:
            with self.lock:
                now = self.clock()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return waited
                need = (1 - self.tokens) / self.rate
            self.sleep(need)
            waited += need
