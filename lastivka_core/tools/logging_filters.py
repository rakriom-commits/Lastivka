"""Легкий rate-limit фільтр для logging.
 - Ліміт рядків за хвилину (default 500)
 - Ліміт обсягу (символів) за годину (default ~5 МБ)
Без зовнішніх залежностей.
"""
from __future__ import annotations
import logging, time, threading

class RateLimitFilter(logging.Filter):
    def __init__(self, name: str = "", lines_per_minute: int = 500, bytes_per_hour: int = 5 * 1024 * 1024) -> None:
        super().__init__(name)
        self.lpm = max(1, int(lines_per_minute))
        self.bph = max(1024, int(bytes_per_hour))
        self._lock = threading.Lock()
        now = time.time()
        self._min_window_start = now
        self._hour_window_start = now
        self._lines_in_min = 0
        self._bytes_in_hour = 0
        self._suppressed_min = 0
        self._suppressed_hour = 0

    def _reset_windows_if_needed(self, now: float) -> None:
        if now - self._min_window_start >= 60.0:
            self._min_window_start = now
            self._lines_in_min = 0
            self._suppressed_min = 0
        if now - self._hour_window_start >= 3600.0:
            self._hour_window_start = now
            self._bytes_in_hour = 0
            self._suppressed_hour = 0

    def filter(self, record: logging.LogRecord) -> bool:
        # Дозволити службові повідомлення про тротлінг навіть під лімітом
        if getattr(record, "_bypass_rate_limit", False):
            return True

        try:
            msg_len = len(record.getMessage())
        except Exception:
            msg_len = 0
        now = time.time()
        with self._lock:
            self._reset_windows_if_needed(now)
            allow_line = self._lines_in_min < self.lpm
            allow_bytes = (self._bytes_in_hour + msg_len) <= self.bph
            if allow_line and allow_bytes:
                self._lines_in_min += 1
                self._bytes_in_hour += msg_len
                return True
            if not allow_line:
                self._suppressed_min += 1
            if not allow_bytes:
                self._suppressed_hour += 1
            # раз при першому придушенні в хвилині/годині — тихий сигнал
            if self._suppressed_min == 1 or self._suppressed_hour == 1:
                try:
                    logging.getLogger(record.name).log(
                        max(logging.WARNING, record.levelno),
                        "Log throttled: minute=%s (limit=%s), hour_bytes=%s/%s",
                        self._lines_in_min, self.lpm, self._bytes_in_hour, self.bph,
                        extra={"_bypass_rate_limit": True},  # <— байпас для цього повідомлення
                    )
                except Exception:
                    pass
            return False

def attach_rate_limit(logger: logging.Logger, lines_per_minute: int = 500, bytes_per_hour: int = 5 * 1024 * 1024) -> None:
    # уникаємо дублювання фільтра
    for f in logger.filters:
        if isinstance(f, RateLimitFilter):
            return
    logger.addFilter(RateLimitFilter(lines_per_minute=lines_per_minute, bytes_per_hour=bytes_per_hour))
