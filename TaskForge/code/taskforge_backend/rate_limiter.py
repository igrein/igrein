from collections import defaultdict
import time
from typing import Dict, List


class RateLimiter:
    """  Ограничение количества запросов на пользователя (session_id) """
    
    def __init__(self, max_requests_per_hour: int = 30):
        self.max_requests = max_requests_per_hour
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    def _cleanup_old_requests(self, session_id: str) -> None:
        """Очищает записи о запросах старше часа"""
        now = time.time()
        hour_ago = now - 3600
        self.requests[session_id] = [
            t for t in self.requests[session_id] if t > hour_ago
        ]
    
    def can_request(self, session_id: str) -> bool:
        """ Проверяет, может ли пользователь выполнить запрос """
        self._cleanup_old_requests(session_id)
        
        if len(self.requests[session_id]) >= self.max_requests:
            return False
        
        self.requests[session_id].append(time.time())
        return True
    
    def remaining_requests(self, session_id: str) -> int:
        """ Возвращает количество оставшихся запросов для пользователя """
        self._cleanup_old_requests(session_id)
        remaining = self.max_requests - len(self.requests[session_id])
        return max(0, remaining)
    
    def reset_session(self, session_id: str) -> None:
        """ Сбрасывает счётчик запросов для сессии """
        if session_id in self.requests:
            del self.requests[session_id]


# Глобальный экземпляр для всего приложения
rate_limiter = RateLimiter()