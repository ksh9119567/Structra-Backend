import fnmatch
import time


class FakeRedis:
    """
    In-memory stand-in for the slice of `redis.StrictRedis` this project uses
    (OTP codes, refresh/access token registry, invite and reset tokens, rate
    limit counters). It lets the test-suite run with no Redis server and, more
    importantly, can never touch a real Redis database.

    Values are stored as `str`, matching the project's `decode_responses=True`
    client. Expiry is honoured, and `advance()` fast-forwards the clock so a
    test can prove an OTP / token really does expire without sleeping.
    """

    def __init__(self):
        self._data = {}      # key -> str value
        self._expires = {}   # key -> absolute (fake) timestamp
        self._offset = 0.0

    # ----- clock -----
    def _now(self):
        return time.time() + self._offset

    def advance(self, seconds):
        """Test helper: move the fake clock forward."""
        self._offset += seconds

    def _purge(self, key):
        exp = self._expires.get(key)
        if exp is not None and exp <= self._now():
            self._data.pop(key, None)
            self._expires.pop(key, None)

    # ----- commands used by the project -----
    def setex(self, name, time_, value):
        self._data[name] = str(value)
        self._expires[name] = self._now() + int(time_)
        return True

    def set(self, name, value, ex=None):
        self._data[name] = str(value)
        if ex is not None:
            self._expires[name] = self._now() + int(ex)
        else:
            self._expires.pop(name, None)
        return True

    def get(self, name):
        self._purge(name)
        return self._data.get(name)

    def exists(self, *names):
        count = 0
        for name in names:
            self._purge(name)
            if name in self._data:
                count += 1
        return count

    def delete(self, *names):
        removed = 0
        for name in names:
            self._purge(name)
            if name in self._data:
                removed += 1
            self._data.pop(name, None)
            self._expires.pop(name, None)
        return removed

    def incr(self, name, amount=1):
        self._purge(name)
        value = int(self._data.get(name, 0)) + amount
        self._data[name] = str(value)  # expiry (if any) is preserved, like real Redis
        return value

    def expire(self, name, seconds):
        self._purge(name)
        if name not in self._data:
            return False
        self._expires[name] = self._now() + int(seconds)
        return True

    def ttl(self, name):
        self._purge(name)
        if name not in self._data:
            return -2
        exp = self._expires.get(name)
        if exp is None:
            return -1
        return max(int(round(exp - self._now())), 0)

    def keys(self, pattern="*"):
        for key in list(self._data):
            self._purge(key)
        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]

    def flushall(self):
        self._data.clear()
        self._expires.clear()
        self._offset = 0.0
        return True

    flushdb = flushall
