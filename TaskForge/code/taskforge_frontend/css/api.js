
// КОНФИГУРАЦИЯ

const API_BASE = window.API_BASE || 'http://localhost:8000';

// Таймаут для запросов (30 секунд)
const REQUEST_TIMEOUT = 30000;


// HELPER: Единый request wrapper с обработкой ошибок
async function request(url, options = {}) {
    // Создаём AbortController для таймаута
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        // Парсим JSON (может быть null, если ответ пустой)
        let data = null;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            try {
                data = await response.json();
            } catch (e) {
                console.warn('Ошибка парсинга JSON:', e);
            }
        }
        
        // Проверяем статус ответа
        if (!response.ok) {
            const errorMessage = data?.detail || data?.message || `HTTP ${response.status}: ${response.statusText}`;
            throw new Error(errorMessage);
        }
        
        return data;
        
    } catch (error) {
        clearTimeout(timeoutId);
        
        // Обработка таймаута
        if (error.name === 'AbortError') {
            throw new Error('Превышено время ожидания ответа от сервера');
        }
        
        // Обработка сетевых ошибок
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('Не удалось连接到 серверу. Проверьте, запущен ли backend на порту 8000');
        }
        
        throw error;
    }
}

// УПРАВЛЕНИЕ СЕССИЕЙ
function getSessionId() {
    let sessionId = localStorage.getItem('taskforge_session_id');
    if (!sessionId) {
        sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 11);
        localStorage.setItem('taskforge_session_id', sessionId);
    }
    return sessionId;
}

async function setSessionId(newId) {
    localStorage.setItem('taskforge_session_id', newId);
    // Небольшая задержка для гарантии записи в localStorage
    await new Promise(resolve => setTimeout(resolve, 50));
    location.reload();
}


// API МЕТОДЫ
const api = {
    /**
     * Основная генерация вариантов (multipart/form-data)
     */
    async uploadAndGenerate(formData) {
        return request(`${API_BASE}/upload-and-generate`, {
            method: 'POST',
            body: formData
        });
    },
    
    /**
     * Получение истории заданий пользователя
     */
    async getHistory(sessionId) {
        return request(`${API_BASE}/history/${sessionId}`);
    },
    
    /**
     * Получение всех вариантов конкретного задания
     */
    async getVariants(sessionId, taskId) {
        if (!taskId) {
            throw new Error('taskId не указан');
        }
        return request(`${API_BASE}/get-variants/${sessionId}/${taskId}`);
    },
    
    /**
     * Сохранение отредактированного варианта
     */
    async editVariant(sessionId, taskId, variantNumber, editedContent) {
        if (!taskId || !variantNumber) {
            throw new Error('taskId и variantNumber обязательны');
        }
        return request(`${API_BASE}/edit-variant`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                task_id: taskId,
                variant_number: variantNumber,
                edited_content: editedContent
            })
        });
    },
    
    /**
     * Перегенерация одного варианта
     */
    async regenerateVariant(sessionId, taskId, variantNumber) {
        if (!taskId || !variantNumber) {
            throw new Error('taskId и variantNumber обязательны');
        }
        return request(`${API_BASE}/regenerate-variant`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                task_id: taskId,
                variant_number: variantNumber
            })
        });
    },
    
    /**
     * Экспорт вариантов в PDF или DOCX
     */
    exportTask(sessionId, taskId, format) {
        if (!taskId) {
            console.warn('exportTask: taskId не указан');
            return;
        }
        if (!format || !['pdf', 'docx'].includes(format)) {
            console.warn('exportTask: неверный формат', format);
            return;
        }
        const url = `${API_BASE}/export?session_id=${sessionId}&task_id=${taskId}&format=${format}`;
        window.open(url, '_blank');
    },
    
    /**
     * Анализ сложности задания
     */
    async analyzeDifficulty(sessionId, taskId) {
        if (!taskId) {
            throw new Error('taskId не указан');
        }
        return request(`${API_BASE}/analyze-difficulty/${sessionId}/${taskId}`);
    },
    
    /**
     * Получение информации о лимите запросов
     */
    async getRateLimit(sessionId) {
        return request(`${API_BASE}/rate-limit/${sessionId}`);
    },
    
    /**
     * Очистка всех данных сессии
     */
    async clearSession(sessionId) {
        return request(`${API_BASE}/clear-session/${sessionId}`, {
            method: 'DELETE'
        });
    }
};