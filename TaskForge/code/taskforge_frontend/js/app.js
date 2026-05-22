// ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
let currentTaskId = null;
let currentVariants = null;
let currentTaskStructure = null;
let currentValidation = null;
let currentEditVariantNum = null;
let selectedFile = null;
let isGenerating = false;

// ИНИЦИАЛИЗАЦИЯ
document.addEventListener('DOMContentLoaded', () => {
    updateSessionDisplay();
    loadRateLimit();
    setupPresets();
    setupFileUpload();
    
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
    
    const backToSettingsFromAnalysisBtn = document.getElementById('backToSettingsFromAnalysisBtn');
    if (backToSettingsFromAnalysisBtn) backToSettingsFromAnalysisBtn.addEventListener('click', () => showStep(2));
    
    const proceedToGenerateBtn = document.getElementById('proceedToGenerateBtn');
    if (proceedToGenerateBtn) proceedToGenerateBtn.addEventListener('click', generateVariants);
    
    const backToAnalysisBtn = document.getElementById('backToAnalysisBtn');
    if (backToAnalysisBtn) backToAnalysisBtn.addEventListener('click', () => showStep('analysis'));
    
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) generateBtn.addEventListener('click', analyzeAndShowStructure);
    
    // Экспорт
    const exportPdfBtn = document.getElementById('exportPdfBtn');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', () => {
            if (currentTaskId) {
                api.exportTask(getSessionId(), currentTaskId, 'pdf');
            } else {
                showToast('Нет активного задания', 'error');
            }
        });
    }
    
    const exportDocxBtn = document.getElementById('exportDocxBtn');
    if (exportDocxBtn) {
        exportDocxBtn.addEventListener('click', () => {
            if (currentTaskId) {
                api.exportTask(getSessionId(), currentTaskId, 'docx');
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
    
    // Новая сессия
    const newSessionBtn = document.getElementById('newSessionBtn');
    if (newSessionBtn) {
        newSessionBtn.addEventListener('click', async () => {
            if (confirm('Создать новую сессию? Все несохранённые данные будут потеряны.')) {
                try {
                    await api.clearSession(getSessionId());
                } catch (e) {
                    console.warn('Ошибка при очистке сессии:', e);
                }
                setSessionId('session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 11));
                updateSessionDisplay();
                await loadRateLimit();
                showToast('Сессия обновлена', 'success');
                selectedFile = null;
                currentTaskId = null;
                currentVariants = null;
                const manualText = document.getElementById('manualText');
                if (manualText) manualText.value = '';
                showStep(1);
            }
        });
    }
    
    // Модальное окно
    const closeModal = document.querySelector('.close');
    if (closeModal) closeModal.addEventListener('click', closeEditModal);
    
    const saveEditBtn = document.getElementById('saveEditBtn');
    if (saveEditBtn) saveEditBtn.addEventListener('click', saveEdit);
    
    const regenerateVariantBtn = document.getElementById('regenerateVariantBtn');
    if (regenerateVariantBtn) {
        regenerateVariantBtn.addEventListener('click', async () => {
            if (currentEditVariantNum) {
                await handleRegenerateVariant(currentEditVariantNum);
                closeEditModal();
            }
        });
    }
    
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    if (cancelEditBtn) cancelEditBtn.addEventListener('click', closeEditModal);
});


// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ UI
function updateSessionDisplay() {
    const sessionIdDisplay = document.getElementById('sessionIdDisplay');
    if (sessionIdDisplay) {
        sessionIdDisplay.textContent = getSessionId().slice(-8);
    }
}


// ЛИМИТЫ ЗАПРОСОВ
async function loadRateLimit() {
    const sessionId = getSessionId();
    try {
        const data = await api.getRateLimit(sessionId);
        const rateLimitDisplay = document.getElementById('rateLimitDisplay');
        if (rateLimitDisplay) {
            rateLimitDisplay.textContent = `${data.remaining}/${data.max_per_hour}`;
        }
    } catch (error) {
        console.error('Ошибка загрузки лимита:', error);
    }
}


// ПРЕСЕТЫ
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


// ЗАГРУЗКА ФАЙЛА
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
    const validTypes = ['.txt', '.pdf', '.docx', '.png', '.jpg', '.jpeg'];
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


// АНАЛИЗ СТРУКТУРЫ
async function analyzeAndShowStructure() {
    const manualText = document.getElementById('manualText')?.value || '';
    if (!selectedFile && !manualText.trim()) {
        showToast('Загрузите файл или введите текст задания', 'error');
        return;
    }
    
    showStep('analysis');
    
    const container = document.getElementById('structureAnalysisContainer');
    if (container) {
        container.innerHTML = `
            <div class="structure-grid">
                <div class="structure-card">
                    <h4>📚 Анализ структуры</h4>
                    <p>Структура задания будет определена автоматически после генерации.</p>
                    <p style="color: #667eea;">Нажмите "Продолжить генерацию" для создания вариантов.</p>
                </div>
            </div>
        `;
    }
}


// ГЕНЕРАЦИЯ ВАРИАНТОВ
async function generateVariants() {
    if (isGenerating) {
        showToast('Генерация уже выполняется, подождите...', 'warning');
        return;
    }
    
    const sessionId = getSessionId();
    const numVariants = parseInt(document.getElementById('numVariants')?.value || '4');
    
    if (numVariants < 2 || numVariants > 10) {
        showToast('Количество вариантов должно быть от 2 до 10', 'error');
        return;
    }
    
    const variationTypes = Array.from(document.querySelectorAll('.checkbox-group input:checked'))
        .map(cb => cb.value);
    
    if (variationTypes.length === 0) {
        showToast('Выберите хотя бы один тип вариации', 'error');
        return;
    }
    
    const forbiddenParts = document.getElementById('forbiddenParts')?.value || '';
    const difficultyOverride = document.querySelector('input[name="difficulty"]:checked')?.value || 'same';
    const targetGrade = document.getElementById('targetGrade')?.value || '';
    
    const manualText = document.getElementById('manualText')?.value || '';
    if (!selectedFile && !manualText.trim()) {
        showToast('Загрузите файл или введите текст задания', 'error');
        return;
    }
    
    isGenerating = true;
    
    const proceedBtn = document.getElementById('proceedToGenerateBtn');
    if (proceedBtn) proceedBtn.disabled = true;
    
    showLoading(true, 'Генерация вариантов...');
    
    try {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('num_variants', numVariants);
        formData.append('variation_types', variationTypes.join(','));
        if (forbiddenParts) formData.append('forbidden_parts', forbiddenParts);
        formData.append('difficulty_override', difficultyOverride);
        if (targetGrade) formData.append('target_grade', targetGrade);
        
        if (selectedFile) {
            formData.append('file', selectedFile);
        } else {
            const blob = new Blob([manualText], { type: 'text/plain' });
            formData.append('file', blob, 'manual.txt');
        }
        
        const result = await api.uploadAndGenerate(formData);
        
        currentTaskId = result.task_id;
        currentTaskStructure = result.task_structure;
        currentValidation = result.validation;
        
        // 🔥 Защита от null/undefined variants
        const variantsCount = result?.variants ? Object.keys(result.variants).length : 0;
        
        if (typeof renderStructureAnalysis === 'function') {
            renderStructureAnalysis(result.task_structure);
        }
        
        if (typeof renderValidation === 'function') {
            renderValidation(result.validation);
        }
        
        if (typeof renderVariants === 'function') {
            renderVariants(result.variants || {}, result.task_id, result.validation);
        }
        
        showStep(3);
        showToast(`Сгенерировано ${variantsCount} вариантов!`, 'success');
        loadRateLimit();
        
    } catch (error) {
        console.error('Generation error:', error);
        showToast(error.message || 'Ошибка генерации', 'error');
    } finally {
        isGenerating = false;
        if (proceedBtn) proceedBtn.disabled = false;
        showLoading(false);
    }
}


// ЗАГРУЗКА ИСТОРИИ
async function loadHistory() {
    const sessionId = getSessionId();
    showLoading(true, 'Загрузка истории...');
    try {
        const history = await api.getHistory(sessionId);
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


// ПЕРЕГЕНЕРАЦИЯ ВАРИАНТА
async function handleRegenerateVariant(variantNumber) {
    if (!currentTaskId) {
        showToast('Нет активного задания', 'error');
        return;
    }
    
    const sessionId = getSessionId();
    showLoading(true, 'Перегенерация варианта...');
    try {
        const result = await api.regenerateVariant(sessionId, currentTaskId, variantNumber);
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