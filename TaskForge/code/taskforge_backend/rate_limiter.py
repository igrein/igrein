from collections import defaultdict
import time
from typing import Dict, List


class RateLimiter:
    """Ограничение количества запросов на пользователя (user_id)"""
    
    def __init__(self, max_requests_per_hour: int = 30):
        self.max_requests = max_requests_per_hour
        self.requests: Dict[int, List[float]] = defaultdict(list)  # user_id -> timestamps
    
    def _cleanup_old_requests(self, user_id: int) -> None:
        """Очищает записи о запросах старше часа"""
        now = time.time()
        hour_ago = now - 3600
        self.requests[user_id] = [
            t for t in self.requests[user_id] if t > hour_ago
        ]
    
    def can_request(self, user_id: int) -> bool:
        """Проверяет, может ли пользователь выполнить запрос"""
        self._cleanup_old_requests(user_id)
        
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        self.requests[user_id].append(time.time())
        return True
    
    def remaining_requests(self, user_id: int) -> int:
        """Возвращает количество оставшихся запросов для пользователя"""
        self._cleanup_old_requests(user_id)
        remaining = self.max_requests - len(self.requests[user_id])
        return max(0, remaining)
    
    def reset_user(self, user_id: int) -> None:
        """Сбрасывает счётчик запросов для пользователя"""
        if user_id in self.requests:
            del self.requests[user_id]


# Глобальный экземпляр для всего приложения
rate_limiter = RateLimiter()
