// ОТОБРАЖЕНИЕ ЗАГРУЗКИ
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


// ПЕРЕКЛЮЧЕНИЕ ШАГОВ 
function showStep(step) {
    // Скрываем все шаги
    const stepIds = ['step1', 'step2', 'stepAnalysis', 'step3', 'step4'];
    for (const id of stepIds) {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    }
    
    // Определяем целевой ID
    let targetId = null;
    
    if (step === 1 || step === 'step1') targetId = 'step1';
    else if (step === 2 || step === 'step2') targetId = 'step2';
    else if (step === 'analysis' || step === 'stepAnalysis') targetId = 'stepAnalysis';
    else if (step === 3 || step === 'step3') targetId = 'step3';
    else if (step === 4 || step === 'step4') targetId = 'step4';
    else targetId = step;
    
    const targetEl = document.getElementById(targetId);
    if (targetEl) targetEl.style.display = 'block';
}

// ОТОБРАЖЕНИЕ АНАЛИЗА СТРУКТУРЫ
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
}


// ОТОБРАЖЕНИЕ ВАЛИДАЦИИ И ОТВЕТОВ
function renderValidation(validation) {
    const section = document.getElementById('validationSection');
    const resultDiv = document.getElementById('validationResult');
    const answersSection = document.getElementById('answersSection');
    const answersContainer = document.getElementById('answersContainer');
    
    if (!section) return;
    
    if (!validation) {
        section.style.display = 'none';
        return;
    }
    
    section.style.display = 'block';
    
    const isValid = validation.valid;
    const difficultyMatch = validation.difficulty_match;
    const uniqueAnswers = validation.unique_answers;
    const sameStructure = validation.same_structure;
    const allSolvable = validation.all_solvable;
    const issues = validation.issues || [];
    
    if (resultDiv) {
        resultDiv.innerHTML = `
            <div class="validation-badge ${isValid ? 'valid' : 'invalid'}">
                ${isValid ? '✅ Все проверки пройдены' : '⚠️ Обнаружены проблемы'}
            </div>
            <div class="validation-badge ${difficultyMatch ? 'valid' : 'warning'}">
                ${difficultyMatch ? '✅ Сложность одинакова' : '⚠️ Сложность отличается'}
            </div>
            <div class="validation-badge ${uniqueAnswers ? 'valid' : 'warning'}">
                ${uniqueAnswers ? '✅ Ответы уникальны' : '⚠️ Есть совпадающие ответы'}
            </div>
            <div class="validation-badge ${sameStructure ? 'valid' : 'warning'}">
                ${sameStructure ? '✅ Структура сохранена' : '⚠️ Структура изменена'}
            </div>
            <div class="validation-badge ${allSolvable ? 'valid' : 'invalid'}">
                ${allSolvable ? '✅ Все варианты решаемы' : '❌ Есть нерешаемые варианты'}
            </div>
        `;
        
        if (issues.length > 0) {
            resultDiv.innerHTML += `
                <div class="issues-list">
                    <strong>Проблемы:</strong>
                    <ul>${issues.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>
                </div>
            `;
        }
    }
    
    // Ответы для учителя
    const answers = validation.answers;
    if (answersSection && answersContainer && answers && Object.keys(answers).length > 0) {
        answersSection.style.display = 'block';
        answersContainer.innerHTML = Object.entries(answers).map(([num, answer]) => `
            <div class="answer-card">
                <strong>Вариант ${num}</strong><br>
                ${escapeHtml(answer)}
            </div>
        `).join('');
    } else if (answersSection) {
        answersSection.style.display = 'none';
    }
}

// ОТОБРАЖЕНИЕ ВАРИАНТОВ
function renderVariants(variants, taskId, validation = null) {
    currentTaskId = taskId;
    currentVariants = variants;
    if (validation) currentValidation = validation;
    
    const container = document.getElementById('variantsContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    for (const [num, content] of Object.entries(variants)) {
        const card = document.createElement('div');
        card.className = 'variant-card';
        card.innerHTML = `
            <div class="variant-header">
                <span class="variant-title">📌 Вариант ${num}</span>
                <div class="variant-actions">
                    <button class="btn-small edit-variant" data-variant="${num}">✏️ Редактировать</button>
                    <button class="btn-small regenerate-variant" data-variant="${num}">🔄 Перегенерировать</button>
                </div>
            </div>
            <div class="variant-content">${escapeHtml(content)}</div>
        `;
        container.appendChild(card);
    }
    
    // Обработчики для кнопок
    document.querySelectorAll('.edit-variant').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const variantNum = btn.dataset.variant;
            openEditModal(variantNum, variants[variantNum]);
        });
    });
    
    document.querySelectorAll('.regenerate-variant').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const variantNum = parseInt(btn.dataset.variant);
            if (typeof handleRegenerateVariant === 'function') {
                await handleRegenerateVariant(variantNum);
            }
        });
    });
}

// РЕДАКТИРОВАНИЕ ВАРИАНТА
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
    
    const sessionId = getSessionId();
    showLoading(true, 'Сохранение...');
    try {
        await api.editVariant(sessionId, currentTaskId, currentEditVariantNum, newContent);
        if (currentVariants) {
            currentVariants[currentEditVariantNum] = newContent;
        }
        renderVariants(currentVariants, currentTaskId, currentValidation);
        closeEditModal();
        showToast('Вариант сохранён!', 'success');
    } catch (error) {
        console.error('Save error:', error);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ИСТОРИЯ
function renderHistory(tasks) {
    const container = document.getElementById('historyContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<p style="text-align:center;">Нет сохранённых заданий. Создайте первое!</p>';
        return;
    }
    
    for (const task of tasks) {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
            <strong>📋 Задание #${task.task_id}</strong>
            <div class="history-preview">${escapeHtml(task.preview)}...</div>
            <small>${new Date(task.created_at).toLocaleString()}</small>
            <div style="margin-top: 8px;">
                <span class="badge">${task.difficulty_override || 'same'}</span>
                ${task.target_grade ? `<span class="badge">${task.target_grade} класс</span>` : ''}
            </div>
        `;
        item.addEventListener('click', () => loadTask(task.task_id));
        container.appendChild(item);
    }
}

async function loadTask(taskId) {
    const sessionId = getSessionId();
    showLoading(true, 'Загрузка задания...');
    try {
        const data = await api.getVariants(sessionId, taskId);
        const analysis = await api.analyzeDifficulty(sessionId, taskId);
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


// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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