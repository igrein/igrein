// ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
let currentTaskId = null;
let currentVariants = null;
let currentTaskStructure = null;
let currentValidation = null;
let currentEditVariantNum = null;
let selectedFile = null;
let isGenerating = false;
let variantsRendered = false;
let currentGenerationParams = {
    numVariants: 4,
    variationTypes: ['numbers', 'order'],
    forbiddenParts: '',
    difficultyOverride: 'same',
    targetGrade: '',
    taskType: '',
    userComment: ''  // ✅ Может быть пустым
};

// ИНИЦИАЛИЗАЦИЯ
document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    setupPresets();
    setupFileUpload();
    setupAuthHandlers();
    
    // Кнопки навигации
    const continueBtn = document.getElementById('continueToSettingsBtn');
    if (continueBtn) {
        continueBtn.addEventListener('click', () => {
            const manualText = document.getElementById('manualText')?.value.trim() || '';
            if (!selectedFile && !manualText) {
                showToast('Введите текст задания или загрузите файл', 'error');
                return;
            }
            showStep(2);
        });
    }
    
    const backToUploadBtn = document.getElementById('backToUploadBtn');
    if (backToUploadBtn) backToUploadBtn.addEventListener('click', () => showStep(1));
    
    // ✅ ИЗМЕНЕНО: Обработчик для кнопки "Назад" на шаге анализа
    const backToSettingsFromAnalysisBtn = document.getElementById('backToSettingsFromAnalysisBtn');
    if (backToSettingsFromAnalysisBtn) {
        backToSettingsFromAnalysisBtn.addEventListener('click', () => showStep(2));
    }
    
    // ✅ ИЗМЕНЕНО: Кнопка генерации на шаге анализа теперь вызывает generateVariantsFromAnalysis
    const proceedToGenerateBtn = document.getElementById('proceedToGenerateBtn');
    if (proceedToGenerateBtn) {
        proceedToGenerateBtn.textContent = '✅ Всё верно, сгенерировать варианты';
        proceedToGenerateBtn.addEventListener('click', generateVariantsFromAnalysis);
    }
    
    const backToAnalysisBtn = document.getElementById('backToAnalysisBtn');
    if (backToAnalysisBtn) backToAnalysisBtn.addEventListener('click', () => showStep('analysis'));
    
    // ✅ ИЗМЕНЕНО: Кнопка на шаге 2 теперь вызывает analyzeAndShowStructure (анализ, а не генерацию)
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        generateBtn.textContent = '🔍 Анализировать задание';
        generateBtn.addEventListener('click', analyzeAndShowStructure);
    }
    
    // Экспорт
    const exportPdfBtn = document.getElementById('exportPdfBtn');
        if (exportPdfBtn) {
            exportPdfBtn.addEventListener('click', () => {
                if (currentTaskId) {
                    const includeAnswers = document.getElementById('includeAnswersCheckbox')?.checked || false;
                    api.exportTask(currentTaskId, 'pdf', includeAnswers);
                } else {
                    showToast('Нет активного задания', 'error');
                }
            });
        }

        const exportDocxBtn = document.getElementById('exportDocxBtn');
        if (exportDocxBtn) {
            exportDocxBtn.addEventListener('click', () => {
                if (currentTaskId) {
                    const includeAnswers = document.getElementById('includeAnswersCheckbox')?.checked || false;
                    api.exportTask(currentTaskId, 'docx', includeAnswers);
                } else {
                    showToast('Нет активного задания', 'error');
                }
            });
        }
            
    // Новая задача
    const newTaskBtn = document.getElementById('newTaskBtn');
    if (newTaskBtn) {
        newTaskBtn.addEventListener('click', () => {
            showStep(1);
            const manualText = document.getElementById('manualText');
            if (manualText) manualText.value = '';
            const fileInput = document.getElementById('fileInput');
            if (fileInput) fileInput.value = '';
            selectedFile = null;
            currentTaskId = null;
            currentVariants = null;
            currentTaskStructure = null;
            currentValidation = null;
            currentGenerationParams = null; // ✅ ОЧИЩАЕМ ПАРАМЕТРЫ
        });
    }
    
    const backToGeneratorBtn = document.getElementById('backToGeneratorBtn');
    if (backToGeneratorBtn) backToGeneratorBtn.addEventListener('click', () => showStep(1));
    
    // Навигационные кнопки в футере
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const step = btn.dataset.step;
            if (step === '4') {
                await loadHistory();
                return;
            }
            showStep(parseInt(step));
        });
    });
    
    // Очистка данных пользователя
    const clearDataBtn = document.getElementById('clearDataBtn');
    if (clearDataBtn) {
        clearDataBtn.addEventListener('click', async () => {
            if (confirm('Удалить все ваши задания? Это действие необратимо.')) {
                try {
                    await api.clearUserData();
                    showToast('Все данные удалены', 'success');
                    selectedFile = null;
                    currentTaskId = null;
                    currentVariants = null;
                    const manualText = document.getElementById('manualText');
                    if (manualText) manualText.value = '';
                    showStep(1);
                    await loadRateLimit();
                } catch (e) {
                    console.warn('Ошибка при очистке данных:', e);
                    showToast('Ошибка очистки данных', 'error');
                }
            }
        });
    }
    
    // Модальное окно редактирования
    const closeModal = document.querySelector('#editModal .close');
    if (closeModal) closeModal.addEventListener('click', closeEditModal);
    
    const saveEditBtn = document.getElementById('saveEditBtn');
    if (saveEditBtn) saveEditBtn.addEventListener('click', saveEdit);
    
    // const regenerateVariantBtn = document.getElementById('regenerateVariantBtn');
    // if (regenerateVariantBtn) {
    //     regenerateVariantBtn.addEventListener('click', async () => {
    //         if (currentEditVariantNum) {
    //             await handleRegenerateVariant(currentEditVariantNum);
    //             closeEditModal();
    //         }
    //     });
    // }
    
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    if (cancelEditBtn) cancelEditBtn.addEventListener('click', closeEditModal);
    
    // Кнопка генерации ответов
    addAnswersButton();
    
    // ✅ НОВОЕ: Обработчик для комментария (счётчик символов)
    const commentTextarea = document.getElementById('generationComment');
    if (commentTextarea) {
        commentTextarea.addEventListener('input', updateCommentCounter);
        // Инициализируем счётчик
        updateCommentCounter();
    }
});


// ========== АВТОРИЗАЦИЯ (ИСПРАВЛЕНА) ==========
async function initAuth() {
    if (isAuthenticated()) {
        try {
            const user = await api.getMe();
            setCurrentUser(user);
            showUserPanel(user.username);
            await loadRateLimit();
            return true;
        } catch (error) {
            console.warn('Token invalid, logging out');
            performLogout();
            showUnauthButtons();
            return false;
        }
    } else {
        showUnauthButtons();
        return false;
    }
}

// Показываем кнопки неавторизованного пользователя
function showUnauthButtons() {
    const authButtons = document.getElementById('authButtons');
    const userPanel = document.getElementById('userPanel');
    
    if (authButtons) authButtons.style.display = 'flex';
    if (userPanel) userPanel.style.display = 'none';
    
    const rateLimitDisplay = document.getElementById('rateLimitDisplay');
    if (rateLimitDisplay) rateLimitDisplay.textContent = '0';
}

function showUserPanel(username) {
    const authButtons = document.getElementById('authButtons');
    const userPanel = document.getElementById('userPanel');
    const usernameDisplay = document.getElementById('usernameDisplay');
    
    if (authButtons) authButtons.style.display = 'none';
    if (userPanel) userPanel.style.display = 'flex';
    if (usernameDisplay) usernameDisplay.textContent = username;
}

// Функция выхода
function performLogout() {
    setAuthToken(null);
    setCurrentUser(null);
    currentTaskId = null;
    currentVariants = null;
    currentTaskStructure = null;
    currentValidation = null;
    selectedFile = null;
    
    const manualText = document.getElementById('manualText');
    if (manualText) manualText.value = '';
    
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    
    if (typeof showStep === 'function') showStep(1);
}

function showAuthModal() {
    const modal = document.getElementById('authModal');
    if (!modal) return;
    
    // Сбрасываем форму
    const usernameInput = document.getElementById('authUsername');
    const passwordInput = document.getElementById('authPassword');
    const errorDiv = document.getElementById('authError');
    
    if (usernameInput) usernameInput.value = '';
    if (passwordInput) passwordInput.value = '';
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
    
    // Сбрасываем на режим входа
    currentAuthMode = true;
    updateAuthModeUI();
    
    modal.style.display = 'flex';
}

// Переменная для хранения текущего режима авторизации
let currentAuthMode = true;

function updateAuthModeUI() {
    const authModalTitle = document.getElementById('authModalTitle');
    const authSubtitle = document.getElementById('authSubtitle');
    const authIcon = document.getElementById('authIcon');
    const authSubmitBtn = document.getElementById('authSubmitBtn');
    const authToggleBtn = document.getElementById('authToggleBtn');
    
    if (currentAuthMode) {
        if (authModalTitle) authModalTitle.textContent = 'Вход';
        if (authSubtitle) authSubtitle.textContent = 'Войдите в свой аккаунт';
        if (authIcon) authIcon.textContent = '🔐';
        if (authSubmitBtn) authSubmitBtn.textContent = 'Войти';
        if (authToggleBtn) authToggleBtn.textContent = 'Нет аккаунта? Зарегистрироваться';
    } else {
        if (authModalTitle) authModalTitle.textContent = 'Регистрация';
        if (authSubtitle) authSubtitle.textContent = 'Создайте новый аккаунт';
        if (authIcon) authIcon.textContent = '📝';
        if (authSubmitBtn) authSubmitBtn.textContent = 'Зарегистрироваться';
        if (authToggleBtn) authToggleBtn.textContent = 'Уже есть аккаунт? Войти';
    }
}

function setupAuthHandlers() {
    // Кнопка входа
    const loginBtn = document.getElementById('loginBtn');
    if (loginBtn) {
        // Удаляем старые обработчики
        const newLoginBtn = loginBtn.cloneNode(true);
        loginBtn.parentNode.replaceChild(newLoginBtn, loginBtn);
        
        newLoginBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showAuthModal();
        });
    }
    
    // Кнопка выхода
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        const newLogoutBtn = logoutBtn.cloneNode(true);
        logoutBtn.parentNode.replaceChild(newLogoutBtn, logoutBtn);
        
        newLogoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                try { await api.logout(); } catch(e) {}
            } catch(e) {}
            
            performLogout();
            showUnauthButtons();
            showToast('Вы вышли из системы', 'success');
        });
    }
    
    // Закрытие модалки
    const authModal = document.getElementById('authModal');
    const closeAuthModal = document.querySelector('#authModal .close');
    
    if (closeAuthModal) {
        const newCloseBtn = closeAuthModal.cloneNode(true);
        closeAuthModal.parentNode.replaceChild(newCloseBtn, closeAuthModal);
        
        newCloseBtn.addEventListener('click', () => {
            if (authModal) authModal.style.display = 'none';
        });
    }
    
    if (authModal) {
        authModal.addEventListener('click', (e) => {
            if (e.target === authModal) {
                authModal.style.display = 'none';
            }
        });
    }
    
    // Кнопка переключения режима
    const authToggleBtn = document.getElementById('authToggleBtn');
    if (authToggleBtn) {
        const newToggleBtn = authToggleBtn.cloneNode(true);
        authToggleBtn.parentNode.replaceChild(newToggleBtn, authToggleBtn);
        
        newToggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            currentAuthMode = !currentAuthMode;
            updateAuthModeUI();
            
            // Очищаем поля и ошибки
            const usernameInput = document.getElementById('authUsername');
            const passwordInput = document.getElementById('authPassword');
            const errorDiv = document.getElementById('authError');
            
            if (usernameInput) usernameInput.value = '';
            if (passwordInput) passwordInput.value = '';
            if (errorDiv) {
                errorDiv.style.display = 'none';
                errorDiv.textContent = '';
            }
        });
    }
    
    // Кнопка отправки формы
    const authSubmitBtn = document.getElementById('authSubmitBtn');
    if (authSubmitBtn) {
        const newSubmitBtn = authSubmitBtn.cloneNode(true);
        authSubmitBtn.parentNode.replaceChild(newSubmitBtn, authSubmitBtn);
        
        newSubmitBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('authUsername')?.value.trim();
            const password = document.getElementById('authPassword')?.value;
            const errorDiv = document.getElementById('authError');
            
            // Валидация
            if (!username || !password) {
                if (errorDiv) {
                    errorDiv.textContent = '❌ Заполните все поля';
                    errorDiv.style.display = 'block';
                }
                return;
            }
            
            if (username.length < 3) {
                if (errorDiv) {
                    errorDiv.textContent = '❌ Имя пользователя должно быть не менее 3 символов';
                    errorDiv.style.display = 'block';
                }
                return;
            }
            
            if (password.length < 6) {
                if (errorDiv) {
                    errorDiv.textContent = '❌ Пароль должен быть не менее 6 символов';
                    errorDiv.style.display = 'block';
                }
                return;
            }
            
            try {
                let response;
                if (currentAuthMode) {
                    response = await api.login(username, password);
                } else {
                    response = await api.register(username, password);
                }
                
                setAuthToken(response.access_token);
                setCurrentUser(response.user);
                
                if (authModal) authModal.style.display = 'none';
                showUserPanel(response.user.username);
                await loadRateLimit();
                
                if (currentAuthMode) {
                    showToast(`✨ Добро пожаловать, ${response.user.username}!`, 'success');
                } else {
                    showToast('✅ Регистрация успешна!', 'success');
                    // После регистрации переключаем на вход
                    currentAuthMode = true;
                    updateAuthModeUI();
                    if (usernameInput) usernameInput.value = '';
                    if (passwordInput) passwordInput.value = '';
                }
                
            } catch (error) {
                if (errorDiv) {
                    let errorMsg = error.message;
                    if (errorMsg.includes('already exists')) {
                        errorMsg = '❌ Пользователь с таким именем уже существует';
                    } else if (errorMsg.includes('Invalid credentials')) {
                        errorMsg = '❌ Неверное имя пользователя или пароль';
                    }
                    errorDiv.textContent = errorMsg;
                    errorDiv.style.display = 'block';
                }
            }
        });
    }
}

// ========== ЛИМИТЫ ЗАПРОСОВ ==========
async function loadRateLimit() {
    if (!isAuthenticated()) return;
    try {
        const data = await api.getRateLimit();
        const rateLimitDisplay = document.getElementById('rateLimitDisplay');
        if (rateLimitDisplay) {
            rateLimitDisplay.textContent = `${data.remaining}/${data.max_per_hour}`;
        }
    } catch (error) {
        console.error('Ошибка загрузки лимита:', error);
    }
}

// ========== ПРЕСЕТЫ ==========
function setupPresets() {
    const presets = {
        'minimal': { variationTypes: ['numbers'] },
        'standard': { variationTypes: ['numbers', 'order'] },
        'full': { variationTypes: ['numbers', 'order', 'synonyms', 'context'] }
    };
    
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const preset = btn.dataset.preset;
            const config = presets[preset];
            if (config) {
                document.querySelectorAll('.checkbox-group input').forEach(cb => {
                    cb.checked = config.variationTypes.includes(cb.value);
                });
                showToast(`Пресет "${btn.textContent}" применён`, 'success');
            }
        });
    });
}

// ========== ЗАГРУЗКА ФАЙЛА ==========
function setupFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');
    
    if (selectFileBtn) {
        selectFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput?.click();
        });
    }
    
    if (uploadArea) {
        uploadArea.addEventListener('click', () => fileInput?.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#667eea';
            uploadArea.style.background = '#f8f9ff';
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '#ccc';
            uploadArea.style.background = 'transparent';
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
            uploadArea.style.borderColor = '#ccc';
            uploadArea.style.background = 'transparent';
        });
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files[0]) handleFile(e.target.files[0]);
        });
    }
}

function handleFile(file) {
    const validTypes = ['.txt', '.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg'];
    const extension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validTypes.includes(extension)) {
        showToast('Неподдерживаемый формат файла', 'error');
        return;
    }
    
    selectedFile = file;
    const manualText = document.getElementById('manualText');
    if (manualText) manualText.value = '';
    showToast(`Выбран файл: ${file.name}`, 'success');
}

// ========== АНАЛИЗ СТРУКТУРЫ ==========
async function analyzeAndShowStructure() {
    const manualText = document.getElementById('manualText')?.value || '';
    if (!selectedFile && !manualText.trim()) {
        showToast('Загрузите файл или введите текст задания', 'error');
        return;
    }
    
    // ✅ СОХРАНЯЕМ ПАРАМЕТРЫ ШАГА 2
    currentGenerationParams = {
        numVariants: parseInt(document.getElementById('numVariants')?.value || '4'),
        variationTypes: Array.from(document.querySelectorAll('.checkbox-group input:checked')).map(cb => cb.value),
        forbiddenParts: document.getElementById('forbiddenParts')?.value || '',
        difficultyOverride: document.querySelector('input[name="difficulty"]:checked')?.value || 'same',
        targetGrade: document.getElementById('targetGrade')?.value || '',
        taskType: document.getElementById('taskType')?.value || ''
    };
    
    // ✅ ВАЛИДАЦИЯ ПАРАМЕТРОВ
    if (currentGenerationParams.numVariants < 2 || currentGenerationParams.numVariants > 10) {
        showToast('Количество вариантов должно быть от 2 до 10', 'error');
        return;
    }
    
    if (currentGenerationParams.variationTypes.length === 0) {
        showToast('Выберите хотя бы один тип вариации', 'error');
        return;
    }
    
    // Показываем загрузку
    showLoading(true, 'Анализ структуры задания...');
    
    try {
        const formData = new FormData();
        formData.append('num_variants', currentGenerationParams.numVariants);
        formData.append('variation_types', currentGenerationParams.variationTypes.join(','));
        if (currentGenerationParams.forbiddenParts) formData.append('forbidden_parts', currentGenerationParams.forbiddenParts);
        formData.append('difficulty_override', currentGenerationParams.difficultyOverride);
        if (currentGenerationParams.targetGrade) formData.append('target_grade', currentGenerationParams.targetGrade);
        if (currentGenerationParams.taskType) formData.append('task_type', currentGenerationParams.taskType);
        
        if (selectedFile) {
            formData.append('file', selectedFile);
            console.log('📁 Отправка файла для анализа:', selectedFile.name);
        } else {
            const blob = new Blob([manualText], { type: 'text/plain' });
            formData.append('file', blob, 'manual.txt');
            console.log('📝 Отправка ручного текста для анализа, длина:', manualText.length);
        }
        
        // ✅ ВЫЗЫВАЕМ analyzeOnly ВМЕСТО uploadAndGenerate
        const result = await api.analyzeOnly(formData);
        
        currentTaskId = result.task_id;
        currentTaskStructure = result.task_structure;
        
        // Отображаем анализ
        if (typeof renderStructureAnalysis === 'function') {
            renderStructureAnalysis(result.task_structure);
        }
        
        // Переходим на шаг анализа
        showStep('analysis');
        showToast('Структура задания проанализирована', 'success');
        
        selectedFile = null;
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';
        
    } catch (error) {
        console.error('Analysis error:', error);
        showToast(error.message || 'Ошибка анализа структуры', 'error');
    } finally {
        showLoading(false);
    }
}

// ========== ГЕНЕРАЦИЯ ВАРИАНТОВ ==========
async function generateVariantsFromAnalysis() {
    if (isGenerating) {
        showToast('Генерация уже выполняется, подождите...', 'warning');
        return;
    }
    
    if (!currentTaskId) {
        showToast('Нет проанализированного задания', 'error');
        return;
    }
    
    // ✅ ПРОВЕРЯЕМ НАЛИЧИЕ ПАРАМЕТРОВ
    if (!currentGenerationParams) {
        console.warn('currentGenerationParams is null, пытаемся восстановить из формы');
        // Пытаемся восстановить параметры из текущих значений формы
        currentGenerationParams = {
            numVariants: parseInt(document.getElementById('numVariants')?.value || '4'),
            variationTypes: Array.from(document.querySelectorAll('.checkbox-group input:checked')).map(cb => cb.value),
            forbiddenParts: document.getElementById('forbiddenParts')?.value || '',
            difficultyOverride: document.querySelector('input[name="difficulty"]:checked')?.value || 'same',
            targetGrade: document.getElementById('targetGrade')?.value || '',
            taskType: document.getElementById('taskType')?.value || ''
        };
    }
    
    // ✅ ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА
    if (!currentGenerationParams || !currentGenerationParams.numVariants) {
        showToast('Ошибка: не найдены параметры генерации. Вернитесь к настройкам.', 'error');
        return;
    }
    
    // ✅ Получаем комментарий (может быть пустым)
    const commentInput = document.getElementById('generationComment');
    const userComment = commentInput ? commentInput.value : '';
    
    // ✅ Валидируем длину ТОЛЬКО если комментарий не пустой
    if (userComment && userComment.length > 200) {
        showToast('Комментарий не может превышать 200 символов', 'error');
        return;
    }
    
    isGenerating = true;
    
    const generateBtn = document.getElementById('proceedToGenerateBtn');
    if (generateBtn) generateBtn.disabled = true;
    
    showLoading(true, 'Генерация вариантов...');
    
    try {
        console.log('Параметры генерации:', currentGenerationParams);
        console.log('Комментарий:', userComment || '(пусто)');
        
        // Используем сохранённые параметры
        const result = await api.generateFromTask(
            currentTaskId,
            currentGenerationParams,
            userComment || null  // ✅ Если пусто - передаём null
        );
        
        currentVariants = result.variants;
        currentValidation = result.validation;
        
        // Обновляем структуру (может быть улучшена)
        if (result.task_structure) {
            currentTaskStructure = result.task_structure;
        }
        
        const variantsCount = Object.keys(result.variants).length;
        
        if (typeof renderVariants === 'function') {
            renderVariants(result.variants, result.task_id, result.validation);
        }
        
        if (typeof renderValidation === 'function') {
            renderValidation(result.validation);
        }
        
        // ✅ ОЧИЩАЕМ КОММЕНТАРИЙ ПОСЛЕ ГЕНЕРАЦИИ
        if (commentInput) {
            commentInput.value = '';
            updateCommentCounter(); // Обновляем счётчик
        }
        
        // ✅ ОЧИЩАЕМ СОХРАНЁННЫЙ КОММЕНТАРИЙ В ПАРАМЕТРАХ
        if (currentGenerationParams) {
            currentGenerationParams.userComment = '';
        }
        
        showStep(3);
        showToast(`Сгенерировано ${variantsCount} вариантов!`, 'success');
        loadRateLimit();
        
    } catch (error) {
        console.error('Generation error:', error);
        showToast(error.message || 'Ошибка генерации', 'error');
    } finally {
        isGenerating = false;
        if (generateBtn) generateBtn.disabled = false;
        showLoading(false);
    }
}


// ========== ЗАГРУЗКА ИСТОРИИ ==========
async function loadHistory() {
    if (!isAuthenticated()) {
        showToast('Войдите в аккаунт для просмотра истории', 'warning');
        showAuthModal();
        return;
    }
    
    showLoading(true, 'Загрузка истории...');
    try {
        const history = await api.getHistory();
        if (typeof renderHistory === 'function') {
            renderHistory(history.tasks);
        }
        showStep(4);
    } catch (error) {
        console.error('History error:', error);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ========== ПЕРЕГЕНЕРАЦИЯ ВАРИАНТА ==========
async function handleRegenerateVariant(variantNumber) {
    if (!currentTaskId) {
        showToast('Нет активного задания', 'error');
        return;
    }
    
    showLoading(true, 'Перегенерация варианта...');
    try {
        const result = await api.regenerateVariant(currentTaskId, variantNumber);
        if (currentVariants) {
            currentVariants[variantNumber] = result.content;
        }
        if (typeof renderVariants === 'function') {
            renderVariants(currentVariants, currentTaskId, currentValidation);
        }
        showToast(`Вариант ${variantNumber} перегенерирован!`, 'success');
    } catch (error) {
        console.error('Regenerate error:', error);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ========== ГЕНЕРАЦИЯ ОТВЕТОВ ==========
async function generateAnswersOnly() {
    if (!currentTaskId) {
        showToast('Нет активного задания', 'error');
        return;
    }
    
    showLoading(true, 'Генерация ответов...');
    try {
        const result = await api.generateAnswers(currentTaskId);
        if (result.answers) {
            // Обновляем текущую валидацию
            if (currentValidation) {
                currentValidation.answers = result.answers;
            } else {
                currentValidation = { answers: result.answers, valid: true, variant_status: {} };
                for (const num of Object.keys(currentVariants)) {
                    currentValidation.variant_status[num] = { valid: true };
                }
            }
            // Перерендериваем
            renderVariants(currentVariants, currentTaskId, currentValidation);
            renderValidation(currentValidation);
            showToast('Ответы сгенерированы!', 'success');
        }
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ========== КНОПКА ГЕНЕРАЦИИ ОТВЕТОВ ==========
function addAnswersButton() {
    const toolbar = document.querySelector('.variants-toolbar');
    if (toolbar && !document.getElementById('generateAnswersBtn')) {
        const btn = document.createElement('button');
        btn.id = 'generateAnswersBtn';
        btn.className = 'btn-small';
        btn.innerHTML = '🔑 Сгенерировать ответы';
        btn.style.marginLeft = '10px';
        btn.addEventListener('click', generateAnswersOnly);
        toolbar.appendChild(btn);
    }
}

// ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
function sanitizeLatexContent(content) {
    if (!content) return '';
    const div = document.createElement('div');
    div.textContent = content;
    let safe = div.innerHTML;
    safe = safe.replace(/\\\(/g, '\\(')
               .replace(/\\\)/g, '\\)')
               .replace(/\\\[/g, '\\[')
               .replace(/\\\]/g, '\\]');
    return safe;
}

function renderVariants(variants, taskId, validation = null) {
    currentTaskId = taskId;
    currentVariants = variants;
    if (validation) currentValidation = validation;
    
    const container = document.getElementById('variantsContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Получаем статусы вариантов из валидации
    const variantStatus = validation?.variant_status || {};
    const answers = validation?.answers || {};
    const summary = validation?.summary || {};
    const remainingProblems = validation?.problems_remaining || {};
    
    for (const [num, content] of Object.entries(variants)) {
        const status = variantStatus[num];
        const severity = status?.severity || 'info';
        const isValid = status?.valid !== false;
        const issues = status?.issues || [];
        
        // Определяем стиль карточки
        let cardClass = 'variant-card';
        let titleIcon = '✅';
        let titleText = `Вариант ${num}`;
        
        if (severity === 'critical' || (!isValid && severity !== 'warning')) {
            cardClass += ' critical';
            titleIcon = '❌';
            titleText = `Вариант ${num} (критическая ошибка)`;
        } else if (severity === 'warning') {
            cardClass += ' warning';
            titleIcon = '⚠️';
            titleText = `Вариант ${num} (требует внимания)`;
        } else {
            cardClass += ' ok';
            titleIcon = '✅';
            titleText = `Вариант ${num}`;
        }
        
        // Бейджи проверки (всегда показываем под вариантом)
        let validationBadgesHtml = '';
        if (status) {
            const checks = [
                { key: 'solvable', label: '✅ Решаемо', failLabel: '❌ Нерешаемо', pass: status.solvable },
                { key: 'difficulty_match', label: '📊 Сложность', failLabel: '⚠️ Сложность', pass: status.difficulty_match },
                { key: 'same_structure', label: '🏗️ Структура', failLabel: '⚠️ Структура', pass: status.same_structure },
                { key: 'unique_answer', label: '🔄 Уникальность', failLabel: '⚠️ Не уникально', pass: status.unique_answer }
            ];
            
            validationBadgesHtml = '<div class="variant-validation-badges">';
            for (const check of checks) {
                const badgeClass = check.pass ? 'pass' : 'fail';
                const label = check.pass ? check.label : check.failLabel;
                validationBadgesHtml += `<span class="variant-validation-badge ${badgeClass}">${label}</span>`;
            }
            validationBadgesHtml += '</div>';
        }
        
        // Ответ учителя (зелёный блок, как проблемы, но зелёного цвета)
        let teacherAnswerHtml = '';
        const answer = answers[num];
        if (answer && answer !== 'null' && answer !== null) {
            let answerText = '';
            if (typeof answer === 'object' && answer !== null) {
                if (answer.text) answerText = answer.text;
                else if (answer.answer) answerText = answer.answer;
                else if (answer.value) answerText = answer.value;
                else answerText = JSON.stringify(answer);
            } else {
                answerText = String(answer);
            }
            
            if (answerText && answerText.trim() && answerText !== 'null') {
                teacherAnswerHtml = `
                    <div class="variant-teacher-answer">
                        <div class="variant-teacher-answer-title">
                            🔑 Ответ для учителя:
                        </div>
                        <div class="variant-teacher-answer-content">${escapeHtml(answerText)}</div>
                    </div>
                `;
            }
        }
        
        // Список проблем (только если есть проблемы)
        let issuesHtml = '';
        if (issues.length > 0) {
            const issueIcon = severity === 'critical' ? '❌' : '⚠️';
            const issueTitle = severity === 'critical' ? 'Критические проблемы:' : 'Проблемы:';
            
            issuesHtml = `
                <div class="variant-issues severity-${severity}">
                    <div class="variant-issues-title">
                        ${issueIcon} ${issueTitle}
                    </div>
                    <ul class="variant-issues-list">
                        ${issues.map(issue => `<li>${escapeHtml(issue)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        const card = document.createElement('div');
        card.className = cardClass;
        
        card.innerHTML = `
            <div class="variant-header">
                <span class="variant-title">
                    ${titleIcon} ${titleText}
                </span>
                <div class="variant-actions">
                    <button class="btn-small edit-variant" data-variant="${num}">✏️ Редактировать</button>
                    <button class="btn-small regenerate-variant" data-variant="${num}">🔄 Перегенерировать</button>
                </div>
            </div>
            <div class="variant-content math">${formatVariantContent(content)}</div>
            ${validationBadgesHtml}
            ${teacherAnswerHtml}
            ${issuesHtml}
        `;
        container.appendChild(card);
    }
    
    renderMathInContainer(container);
}


function renderMathInContainer(container) {
    if (!window.MathJax || !window.MathJax.typesetPromise) {
        console.warn('MathJax не загружен');
        return Promise.resolve();
    }
    
    if (window.MathJax.typesetClear) {
        window.MathJax.typesetClear([container]);
    }
    
    return new Promise(resolve => {
        setTimeout(() => {
            MathJax.typesetPromise([container])
                .catch(err => console.warn('MathJax error:', err))
                .finally(resolve);
        }, 50);
    });
}

function showLoading(show, message = 'Генерация вариантов...') {
    const overlay = document.getElementById('loadingOverlay');
    const msgElement = document.getElementById('loadingMessage');
    if (show) {
        if (msgElement) msgElement.textContent = message;
        if (overlay) overlay.style.display = 'flex';
    } else {
        if (overlay) overlay.style.display = 'none';
    }
}

function showStep(step) {
    const stepIds = ['step1', 'step2', 'stepAnalysis', 'step3', 'step4'];
    for (const id of stepIds) {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    }
    
    let targetId = null;
    
    if (step === 1 || step === 'step1') targetId = 'step1';
    else if (step === 2 || step === 'step2') targetId = 'step2';
    else if (step === 'analysis' || step === 'stepAnalysis') targetId = 'stepAnalysis';
    else if (step === 3 || step === 'step3') targetId = 'step3';
    else if (step === 4 || step === 'step4') targetId = 'step4';
    else targetId = step;
    
    const targetEl = document.getElementById(targetId);
    if (targetEl) targetEl.style.display = 'block';
    
    // ✅ При переходе на шаг анализа, показываем комментарий (если был сохранён)
    if (targetId === 'stepAnalysis') {
        const commentTextarea = document.getElementById('generationComment');
        if (commentTextarea && currentGenerationParams) {
            // Не очищаем, оставляем что ввели (если вернулись назад)
            if (!commentTextarea.value && currentGenerationParams.userComment) {
                commentTextarea.value = currentGenerationParams.userComment;
            }
        }
        updateCommentCounter();
    }
    
    // ✅ При переходе на шаг 2, восстанавливаем параметры
    if (targetId === 'step2' && currentGenerationParams) {
        // Восстанавливаем настройки
        const numVariantsInput = document.getElementById('numVariants');
        if (numVariantsInput) numVariantsInput.value = currentGenerationParams.numVariants;
        
        // Восстанавливаем чекбоксы
        document.querySelectorAll('.checkbox-group input').forEach(cb => {
            cb.checked = currentGenerationParams.variationTypes.includes(cb.value);
        });
        
        const forbiddenInput = document.getElementById('forbiddenParts');
        if (forbiddenInput) forbiddenInput.value = currentGenerationParams.forbiddenParts || '';
        
        const difficultyRadios = document.querySelectorAll('input[name="difficulty"]');
        difficultyRadios.forEach(radio => {
            if (radio.value === currentGenerationParams.difficultyOverride) {
                radio.checked = true;
            }
        });
        
        const gradeSelect = document.getElementById('targetGrade');
        if (gradeSelect) gradeSelect.value = currentGenerationParams.targetGrade || '';
        
        const taskTypeSelect = document.getElementById('taskType');
        if (taskTypeSelect) taskTypeSelect.value = currentGenerationParams.taskType || '';
    }
}

function updateCommentCounter() {
    const commentTextarea = document.getElementById('generationComment');
    const counterSpan = document.getElementById('commentCounter');
    
    if (commentTextarea && counterSpan) {
        const length = commentTextarea.value.length;
        counterSpan.textContent = `${length}/200`;
        
        // Визуальное предупреждение при приближении к лимиту
        if (length > 180) {
            counterSpan.style.color = '#f59e0b';
        } else if (length > 190) {
            counterSpan.style.color = '#ef4444';
        } else {
            counterSpan.style.color = '#666';
        }
    }
}


function renderStructureAnalysis(taskStructure) {
    const container = document.getElementById('structureAnalysisContainer');
    if (!container) return;
    
    if (!taskStructure) {
        container.innerHTML = '<p>Не удалось проанализировать структуру задания</p>';
        return;
    }
    
    const invariantElements = taskStructure.invariant_elements || [];
    const variableElements = taskStructure.variable_elements || [];
    
    container.innerHTML = `
        <div class="structure-grid">
            <div class="structure-card">
                <h4>📚 Общая информация</h4>
                <p><strong>Предмет:</strong> ${escapeHtml(taskStructure.subject || '—')}</p>
                <p><strong>Тип задания:</strong> ${escapeHtml(taskStructure.task_type || '—')}</p>
                <p><strong>Сложность:</strong> ${taskStructure.difficulty_score || '—'}/10</p>
                <p><strong>Рекомендуемый класс:</strong> ${escapeHtml(taskStructure.grade || '—')}</p>
                <p><strong>Количество операций:</strong> ${taskStructure.operations_count || '—'}</p>
            </div>
            <div class="structure-card">
                <h4>🔒 Инвариантные элементы (НЕ меняются)</h4>
                <ul class="invariant-list">
                    ${invariantElements.map(el => `<li>🔒 ${escapeHtml(el)}</li>`).join('')}
                </ul>
                ${taskStructure.why_invariant ? `<div class="explanation">💡 ${escapeHtml(taskStructure.why_invariant)}</div>` : ''}
            </div>
            <div class="structure-card">
                <h4>✨ Вариативные элементы (МЕНЯЮТСЯ)</h4>
                <ul class="variable-list">
                    ${variableElements.map(el => `<li>✨ ${escapeHtml(el)}</li>`).join('')}
                </ul>
                ${taskStructure.why_variable ? `<div class="explanation">💡 ${escapeHtml(taskStructure.why_variable)}</div>` : ''}
            </div>
        </div>
        ${taskStructure.why_difficulty ? `<div class="explanation" style="margin-top: 10px;">📊 Обоснование сложности: ${escapeHtml(taskStructure.why_difficulty)}</div>` : ''}
    `;
    
    setTimeout(() => {
        if (window.MathJax && window.MathJax.typesetPromise) {
            MathJax.typesetPromise([container]);
        }
    }, 50);
}

function renderValidation(validation) {
    const section = document.getElementById('validationSection');
    const resultDiv = document.getElementById('validationResult');
    
    if (!section) return;
    
    if (!validation) {
        section.style.display = 'none';
        return;
    }
    
    section.style.display = 'block';
    
    const summary = validation.summary || {};
    const variantStatus = validation.variant_status || {};
    const remainingProblems = validation.problems_remaining;
    const regenerationHistory = validation.regeneration_history || [];
    
    const total = summary.total || Object.keys(variantStatus).length;
    const validCount = summary.valid_count || 0;
    const invalidCount = summary.invalid_count || 0;
    const warningCount = summary.warning_count || 0;
    
    // Подсчитываем проблемы по типам
    let issuesByType = summary.issues_by_type || { solvable: 0, difficulty: 0, structure: 0, uniqueness: 0 };
    
    if (!summary.issues_by_type && Object.keys(variantStatus).length > 0) {
        issuesByType = { solvable: 0, difficulty: 0, structure: 0, uniqueness: 0 };
        for (const status of Object.values(variantStatus)) {
            if (!status.solvable) issuesByType.solvable++;
            if (!status.difficulty_match) issuesByType.difficulty++;
            if (!status.same_structure) issuesByType.structure++;
            if (!status.unique_answer) issuesByType.uniqueness++;
        }
    }
    
    // Определяем общий статус
    let statusIcon = '✅';
    let statusText = 'Все проверки пройдены';
    let statusClass = 'valid';
    
    if (invalidCount > 0) {
        statusIcon = '❌';
        statusText = `Критические ошибки в ${invalidCount} вариантах`;
        statusClass = 'invalid';
    } else if (warningCount > 0) {
        statusIcon = '⚠️';
        statusText = `Требуют внимания: ${warningCount} вариант(ов) с замечаниями`;
        statusClass = 'warning';
    }
    
    // Формируем HTML для общей статистики (без дублирования проверок)
    if (resultDiv) {
        let statsHtml = `
            <div class="validation-summary ${statusClass}" style="margin-bottom: 12px;">
                <span class="summary-icon">${statusIcon}</span>
                <span class="summary-text">${statusText}</span>
            </div>
            <div class="validation-stats" style="display: flex; flex-wrap: wrap; gap: 12px;">
                <span class="stat">📊 Всего: ${total}</span>
                <span class="stat valid">✅ Валидных: ${validCount}</span>
        `;
        
        if (warningCount > 0) {
            statsHtml += `<span class="stat warning">⚠️ С замечаниями: ${warningCount}</span>`;
        }
        
        if (invalidCount > 0) {
            statsHtml += `<span class="stat invalid">❌ Критических: ${invalidCount}</span>`;
        }
        
        statsHtml += `</div>`;
        
        // Добавляем информацию о проблемах, оставшихся после итераций
        if (remainingProblems && Object.keys(remainingProblems).length > 0) {
            statsHtml += `
                <div class="remaining-problems" style="margin-top: 12px; padding: 10px; background: #fee2e2; border-radius: 8px;">
                    <strong>⚠️ После 2 итераций остались проблемы:</strong>
                    <ul style="margin: 8px 0 0 20px;">
                        ${Object.entries(remainingProblems).map(([num, issues]) => 
                            `<li><strong>Вариант ${num}:</strong> ${Array.isArray(issues) ? issues.join('; ') : issues}</li>`
                        ).join('')}
                    </ul>
                </div>
            `;
        }
        
        // Добавляем историю перегенераций
        if (regenerationHistory && regenerationHistory.length > 0) {
            let historyHtml = `
                <div class="regeneration-history" style="margin-top: 12px; padding: 10px; background: #f0fdf4; border-radius: 8px;">
                    <strong>🔄 История перегенераций:</strong>
                    <ul style="margin: 8px 0 0 20px; font-size: 12px;">
            `;
            for (const hist of regenerationHistory) {
                historyHtml += `<li>Итерация ${hist.iteration}: перегенерированы варианты ${hist.problem_variants.join(', ')}</li>`;
            }
            historyHtml += `</ul></div>`;
            statsHtml += historyHtml;
        }
        
        resultDiv.innerHTML = statsHtml;
    }
    
    // Обновляем отображение вариантов с учётом статусов и ответов
    if (currentVariants && currentTaskId) {
        renderVariants(currentVariants, currentTaskId, validation);
    }
}

function openEditModal(variantNum, content) {
    currentEditVariantNum = variantNum;
    const modal = document.getElementById('editModal');
    const textarea = document.getElementById('editTextarea');
    if (modal) modal.style.display = 'flex';
    if (textarea) textarea.value = content;
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    if (modal) modal.style.display = 'none';
    currentEditVariantNum = null;
}

async function saveEdit() {
    const newContent = document.getElementById('editTextarea')?.value;
    if (!newContent || !currentTaskId || !currentEditVariantNum) {
        showToast('Ошибка сохранения', 'error');
        return;
    }
    
    showLoading(true, 'Сохранение...');
    try {
        // ✅ ИСПРАВЛЕНО: оборачиваем в Number()
        await api.editVariant(
            Number(currentTaskId), 
            Number(currentEditVariantNum), 
            newContent
        );
        if (currentVariants) {
            currentVariants[currentEditVariantNum] = newContent;
        }
        
        const container = document.getElementById('variantsContainer');
        if (container) {
            const variantCards = container.querySelectorAll('.variant-card');
            if (variantCards[currentEditVariantNum - 1]) {
                const contentDiv = variantCards[currentEditVariantNum - 1].querySelector('.variant-content');
                if (contentDiv) {
                    contentDiv.innerHTML = sanitizeLatexContent(newContent);
                    
                    if (window.MathJax && window.MathJax.typesetClear) {
                        MathJax.typesetClear([contentDiv]);
                    }
                    setTimeout(() => {
                        if (window.MathJax && window.MathJax.typesetPromise) {
                            MathJax.typesetPromise([contentDiv]);
                        }
                    }, 50);
                }
            }
        }
        
        closeEditModal();
        showToast('Вариант сохранён!', 'success');
    } catch (error) {
        console.error('Save error:', error);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// function renderHistory(tasks) {
//     const container = document.getElementById('historyContainer');
//     if (!container) return;
    
//     container.innerHTML = '';
    
//     if (!tasks || tasks.length === 0) {
//         container.innerHTML = '<p style="text-align:center;">Нет сохранённых заданий. Создайте первое!</p>';
//         return;
//     }
    
//     for (const task of tasks) {
//         const item = document.createElement('div');
//         item.className = 'history-item';
//         item.innerHTML = `
//             <strong>📋 Задание #${task.task_id}</strong>
//             <div class="history-preview">${escapeHtml(task.preview)}...</div>
//             <small>${new Date(task.created_at).toLocaleString()}</small>
//             <div style="margin-top: 8px;">
//                 <span class="badge">${task.difficulty_override || 'same'}</span>
//                 ${task.target_grade ? `<span class="badge">${task.target_grade} класс</span>` : ''}
//             </div>
//         `;
//         item.addEventListener('click', () => loadTask(task.task_id));
//         container.appendChild(item);
//     }
// }

async function loadTask(taskId) {
    showLoading(true, 'Загрузка задания...');
    try {
        const data = await api.getVariants(taskId);
        const analysis = await api.analyzeDifficulty(taskId);
        currentTaskStructure = analysis.task_structure;
        renderVariants(data.variants, taskId);
        if (currentTaskStructure && typeof renderStructureAnalysis === 'function') {
            renderStructureAnalysis(currentTaskStructure);
        }
        showStep(3);
    } catch (error) {
        console.error('Load task error:', error);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4caf50' : type === 'warning' ? '#f59e0b' : '#f44336'};
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        z-index: 3000;
        animation: fadeInOut 3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Добавляем стили для тостов (если ещё нет)
if (!document.querySelector('#toast-styles')) {
    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
        @keyframes fadeInOut {
            0% { opacity: 0; transform: translateX(100%); }
            10% { opacity: 1; transform: translateX(0); }
            90% { opacity: 1; transform: translateX(0); }
            100% { opacity: 0; transform: translateX(100%); }
        }
        .badge {
            display: inline-block;
            background: #e0e0e0;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            margin-right: 5px;
        }
        .validation-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
        }
        .validation-badge.valid {
            background: #22c55e20;
            color: #166534;
        }
        .validation-badge.invalid {
            background: #ef444420;
            color: #991b1b;
        }
        .validation-badge.warning {
            background: #f59e0b20;
            color: #92400e;
        }
        .issues-list {
            margin-top: 10px;
            padding-left: 20px;
            color: #dc2626;
        }
        .answer-card {
            background: white;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #ddd;
        }
        .structure-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .structure-card {
            background: white;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .invariant-list li, .variable-list li {
            padding: 4px 0;
        }
        .invariant-list li { color: #e74c3c; }
        .variable-list li { color: #27ae60; }
        .explanation {
            font-size: 13px;
            color: #666;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }
    `;
    document.head.appendChild(style);
}
