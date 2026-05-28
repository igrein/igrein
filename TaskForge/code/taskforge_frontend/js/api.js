// ==================== api.js ====================
// КОНФИГУРАЦИЯ
const API_BASE = window.API_BASE || 'http://localhost:8000';
const REQUEST_TIMEOUT = 30000;

// ===== ТОКЕНЫ И ПОЛЬЗОВАТЕЛИ =====
function getAuthToken() {
    return localStorage.getItem('taskforge_auth_token');
}

function setAuthToken(token) {
    if (token) {
        localStorage.setItem('taskforge_auth_token', token);
    } else {
        localStorage.removeItem('taskforge_auth_token');
    }
}

function getCurrentUser() {
    const userStr = localStorage.getItem('taskforge_user');
    return userStr ? JSON.parse(userStr) : null;
}

function setCurrentUser(user) {
    if (user) {
        localStorage.setItem('taskforge_user', JSON.stringify(user));
    } else {
        localStorage.removeItem('taskforge_user');
    }
}

function isAuthenticated() {
    return !!getAuthToken();
}

function logout() {
    setAuthToken(null);
    setCurrentUser(null);
}

// ===== REQUEST WRAPPER =====
async function request(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    
    const headers = options.headers || {};
    const token = getAuthToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
        const response = await fetch(url, {
            ...options,
            headers: headers,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.status === 401) {
            logout();
            throw new Error('Сессия истекла. Войдите снова.');
        }
        
        let data = null;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            try {
                data = await response.json();
            } catch (e) {
                console.warn('Ошибка парсинга JSON:', e);
            }
        }
        
        if (!response.ok) {
            const errorMessage = data?.detail || data?.message || `HTTP ${response.status}: ${response.statusText}`;
            throw new Error(errorMessage);
        }
        
        return data;
        
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Превышено время ожидания ответа от сервера');
        }
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('Не удалось подключиться к серверу. Проверьте, запущен ли backend на порту 8000');
        }
        throw error;
    }
}

// ===== API МЕТОДЫ =====
const api = {
    // Авторизация
    async register(username, password) {
        return request(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
    },
    
    async login(username, password) {
        return request(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
    },
    
    async logout() {
        try {
            await request(`${API_BASE}/logout`, { method: 'POST' });
        } catch(e) {
            console.warn('Logout error:', e);
        }
        logout();
    },
    
    async getMe() {
        return request(`${API_BASE}/me`);
    },
    
    // Анализ без генерации
    async analyzeOnly(formData) {
        formData.append('preview_only', 'true');
        return request(`${API_BASE}/upload-and-generate`, {
            method: 'POST',
            body: formData
        });
    },
    
    // Генерация из существующего задания
    async generateFromTask(taskId, params, userComment = null) {
        const formData = new FormData();
        formData.append('task_id', taskId);
        formData.append('num_variants', params.numVariants);
        formData.append('variation_types', params.variationTypes.join(','));
        if (params.forbiddenParts) formData.append('forbidden_parts', params.forbiddenParts);
        formData.append('difficulty_override', params.difficultyOverride);
        if (params.targetGrade) formData.append('target_grade', params.targetGrade);
        if (params.taskType) formData.append('task_type', params.taskType);
        if (userComment && userComment.trim()) {
            formData.append('user_comment', userComment.trim());
        }
        return request(`${API_BASE}/generate-from-task`, {
            method: 'POST',
            body: formData
        });
    },
    
    // Полная генерация (анализ + варианты)
    async uploadAndGenerate(formData) {
        return request(`${API_BASE}/upload-and-generate`, {
            method: 'POST',
            body: formData
        });
    },
    
    async getHistory() {
        return request(`${API_BASE}/history`);
    },
    
    async getVariants(taskId) {
        if (!taskId) throw new Error('taskId не указан');
        return request(`${API_BASE}/get-variants/${taskId}`);
    },
    
    async editVariant(taskId, variantNumber, editedContent) {
        if (!taskId || !variantNumber) throw new Error('taskId и variantNumber обязательны');
        return request(`${API_BASE}/edit-variant`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: taskId,
                variant_number: variantNumber,
                edited_content: editedContent
            })
        });
    },
    
    async regenerateVariant(taskId, variantNumber) {
        if (!taskId || !variantNumber) throw new Error('taskId и variantNumber обязательны');
        return request(`${API_BASE}/regenerate-variant`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: taskId,
                variant_number: variantNumber
            })
        });
    },
    
    exportTask(taskId, format, includeAnswers = false) {
        if (!taskId) return;
        const token = getAuthToken();
        const url = `${API_BASE}/export?task_id=${taskId}&format=${format}&include_answers=${includeAnswers}`;
        fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(response => {
            if (!response.ok) throw new Error('Ошибка экспорта');
            return response.blob();
        })
        .then(blob => {
            const blobUrl = URL.createObjectURL(blob);
            window.open(blobUrl, '_blank');
            URL.revokeObjectURL(blobUrl);
        })
        .catch(err => console.error('Export error:', err));
    },
    
    async analyzeDifficulty(taskId) {
        if (!taskId) throw new Error('taskId не указан');
        return request(`${API_BASE}/analyze-difficulty/${taskId}`);
    },
    
    async getRateLimit() {
        return request(`${API_BASE}/rate-limit`);
    },
    
    async clearUserData() {
        return request(`${API_BASE}/clear-data`, { method: 'DELETE' });
    },
    
    async generateAnswers(taskId) {
        if (!taskId) throw new Error('taskId не указан');
        return request(`${API_BASE}/generate-answers/${taskId}`, { method: 'POST' });
    }
};
