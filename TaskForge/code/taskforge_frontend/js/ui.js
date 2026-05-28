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

// ========== ОТОБРАЖЕНИЕ ВАРИАНТОВ ==========
function renderVariants(variants, taskId, validation = null) {
    currentTaskId = taskId;
    currentVariants = variants;
    if (validation) currentValidation = validation;
    
    const container = document.getElementById('variantsContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    const variantStatus = validation?.variant_status || {};
    const answers = validation?.answers || {};
    
    for (const [num, content] of Object.entries(variants)) {
        const status = variantStatus[num];
        
        // 🔑 ГЛАВНАЯ ПРАВКА: читаем правильные поля из нового формата
        const isValid = status?.valid !== false;
        const hasCritical = status?.critical === true;
        const warnings = status?.warnings || [];
        const issues = status?.issues || [];
        
        // Определяем стиль карточки
        let cardClass = 'variant-card';
        let titleIcon = '✅';
        let titleText = `Вариант ${num}`;
        
        if (hasCritical) {
            cardClass += ' critical';
            titleIcon = '❌';
            titleText = `Вариант ${num} (критическая ошибка)`;
        } else if (warnings.length > 0 || (!isValid && !hasCritical)) {
            cardClass += ' warning';
            titleIcon = '⚠️';
            titleText = `Вариант ${num}`;
        } else {
            cardClass += ' ok';
            titleIcon = '✅';
            titleText = `Вариант ${num}`;
        }
        
        // 🔑 ПРАВКА: бейджи читаем из правильных полей
        const solvable = status?.solvable !== false;
        const difficultyMatch = status?.difficulty_match !== false;
        const sameStructure = status?.same_structure !== false;
        const uniqueAnswer = status?.unique_answer !== false;
        
        const validationBadgesHtml = `
            <div class="variant-validation-badges">
                <span class="variant-validation-badge ${solvable ? 'pass' : 'fail'}">${solvable ? '✅ Решаемо' : '❌ Нерешаемо'}</span>
                <span class="variant-validation-badge ${difficultyMatch ? 'pass' : 'fail'}">${difficultyMatch ? '📊 Сложность' : '⚠️ Сложность'}</span>
                <span class="variant-validation-badge ${sameStructure ? 'pass' : 'fail'}">${sameStructure ? '🏗️ Структура' : '⚠️ Структура'}</span>
                <span class="variant-validation-badge ${uniqueAnswer ? 'pass' : 'fail'}">${uniqueAnswer ? '🔄 Уникальность' : '⚠️ Не уникально'}</span>
            </div>
        `;
        
        // 🔑 ПРАВКА: ответ учителя
        let teacherAnswerHtml = '';
        const answer = answers[num];
        if (answer && answer !== 'null' && answer !== null && answer !== 'none') {
            let answerText = '';
            if (typeof answer === 'object' && answer !== null) {
                answerText = answer.answer || answer.text || answer.value || JSON.stringify(answer);
            } else {
                answerText = String(answer);
            }
            if (answerText && answerText.trim() && answerText !== 'null') {
                teacherAnswerHtml = `
                    <div class="variant-teacher-answer">
                        <div class="variant-teacher-answer-title">🔑 Ответ для учителя:</div>
                        <div class="variant-teacher-answer-content">${escapeHtml(answerText)}</div>
                    </div>
                `;
            }
        }
        
        // 🔑 ПРАВКА: проблемы и предупреждения
        let issuesHtml = '';
        const allIssues = [...issues, ...warnings];
        if (allIssues.length > 0) {
            const severityClass = hasCritical ? 'severity-critical' : 'severity-warning';
            const issueIcon = hasCritical ? '❌' : '⚠️';
            const issueTitle = hasCritical ? 'Критические проблемы:' : 'Предупреждения:';
            
            issuesHtml = `
                <div class="variant-issues ${severityClass}">
                    <div class="variant-issues-title">${issueIcon} ${issueTitle}</div>
                    <ul class="variant-issues-list">
                        ${allIssues.map(issue => `<li>${escapeHtml(issue)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        const card = document.createElement('div');
        card.className = cardClass;
        card.innerHTML = `
            <div class="variant-header">
                <span class="variant-title">${titleIcon} ${titleText}</span>
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

// ========== ОТОБРАЖЕНИЕ ЗАГРУЗКИ ==========
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

// ========== ПЕРЕКЛЮЧЕНИЕ ШАГОВ ==========
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
}

// ========== ОТОБРАЖЕНИЕ АНАЛИЗА СТРУКТУРЫ ==========
function renderStructureAnalysis(taskStructure) {
    const container = document.getElementById('structureAnalysisContainer');
    if (!container) return;
    // Маппинг типов на русский
    const typeMapping = {
        'calculation': 'Вычисление/Задача',
        'test': 'Тест',
        'multiple_choice': 'Тест с выбором',
        'matching': 'Сопоставление',
        'fill_blanks': 'Заполнение пропусков',
        'open_question': 'Открытый вопрос',
        'proof': 'Доказательство'
    };
    
    const intentMapping = {
        'calculation': 'Вычисление',
        'classification': 'Классификация',
        'matching': 'Сопоставление',
        'sequence': 'Упорядочивание',
        'fact_recall': 'Воспроизведение фактов',
        'application': 'Применение знаний'
    };
    
    const cognitiveMapping = {
        'recognition': 'Узнавание',
        'reproduction': 'Воспроизведение',
        'application': 'Применение',
        'analysis': 'Анализ',
        'synthesis': 'Синтез'
    };
    
    const invariantElements = (taskStructure.invariant_elements || []).map(el => {
        // Переводим ключевые фразы
        return el.replace('pedagogical_intent:', 'Педагогическая цель:')
                 .replace('cognitive_level:', 'Когнитивный уровень:')
                 .replace('structural_type:', 'Тип задания:')
                 .replace('topic_core:', 'Тема:');
    });
    
    const taskType = typeMapping[taskStructure.task_type] || taskStructure.task_type || '—';
    const pedagogicalIntent = intentMapping[taskStructure.pedagogical_intent] || taskStructure.pedagogical_intent || '—';
    const cognitiveLevel = cognitiveMapping[taskStructure.cognitive_level] || taskStructure.cognitive_level || '—';
    
    container.innerHTML = `
        <div class="structure-grid">
            <div class="structure-card">
                <h4>📚 Общая информация</h4>
                <p><strong>Предмет:</strong> ${escapeHtml(taskStructure.subject || '—')}</p>
                <p><strong>Тип задания:</strong> ${taskType}</p>
                <p><strong>Сложность:</strong> ${taskStructure.difficulty_score || '—'}/10</p>
                <p><strong>Рекомендуемый класс:</strong> ${escapeHtml(taskStructure.grade || '5-9')}</p>
                <p><strong>Количество операций:</strong> ${taskStructure.operations_count || '—'}</p>
                <p><strong>Педагогическая цель:</strong> ${pedagogicalIntent}</p>
                <p><strong>Когнитивный уровень:</strong> ${cognitiveLevel}</p>
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
                    ${(taskStructure.variable_elements || []).map(el => `<li>✨ ${escapeHtml(el)}</li>`).join('')}
                </ul>
                ${taskStructure.why_variable ? `<div class="explanation">💡 ${escapeHtml(taskStructure.why_variable)}</div>` : ''}
            </div>
        </div>
        ${taskStructure.why_difficulty ? `<div class="explanation" style="margin-top: 10px;">📊 Обоснование сложности: ${escapeHtml(taskStructure.why_difficulty)}</div>` : ''}
    `;
}

// ========== ОТОБРАЖЕНИЕ ВАЛИДАЦИИ И ОТВЕТОВ ==========
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
    
    const total = summary.total || Object.keys(variantStatus).length;
    const validCount = summary.valid_count || 0;
    const criticalCount = summary.critical_count || 0;
    const warningCount = summary.warning_count || 0;
    
    let statusIcon = '✅';
    let statusText = 'Все варианты валидны';
    let statusClass = 'valid';
    
    if (criticalCount > 0) {
        statusIcon = '❌';
        statusText = `Критические ошибки в ${criticalCount} вариантах`;
        statusClass = 'invalid';
    } else if (warningCount > 0) {
        statusIcon = '⚠️';
        statusText = `${warningCount} вариант(ов) с предупреждениями`;
        statusClass = 'warning';
    }
    
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
            statsHtml += `<span class="stat warning">⚠️ С предупреждениями: ${warningCount}</span>`;
        }
        if (criticalCount > 0) {
            statsHtml += `<span class="stat invalid">❌ Критических: ${criticalCount}</span>`;
        }
        
        statsHtml += `</div>`;
        
        if (remainingProblems && Object.keys(remainingProblems).length > 0) {
            statsHtml += `
                <div class="remaining-problems" style="margin-top: 12px; padding: 10px; background: #fee2e2; border-radius: 8px;">
                    <strong>⚠️ Остались проблемы:</strong>
                    <ul style="margin: 8px 0 0 20px;">
                        ${Object.entries(remainingProblems).map(([num, problems]) => 
                            `<li><strong>Вариант ${num}:</strong> ${Array.isArray(problems) ? problems.join('; ') : problems}</li>`
                        ).join('')}
                    </ul>
                </div>
            `;
        }
        
        resultDiv.innerHTML = statsHtml;
    }
    
    // Перерендериваем варианты с обновлёнными статусами
    if (currentVariants && currentTaskId) {
        renderVariants(currentVariants, currentTaskId, validation);
    }
}

// ========== РЕДАКТИРОВАНИЕ ВАРИАНТА ==========
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
        // ИСПРАВЛЕНО: убрали sessionId
        await api.editVariant(currentTaskId, currentEditVariantNum, newContent);
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

// ========== ИСТОРИЯ ==========
function renderHistory(tasks) {
    const container = document.getElementById('historyContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<p style="text-align:center;">Нет сохранённых заданий. Создайте первое!</p>';
        return;
    }

    console.log('Tasks data:', tasks);
    
    for (const task of tasks) {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
            <strong>📋 Задание #${task.task_number_for_user}</strong>
            <div class="history-preview">${escapeHtml(task.preview)}...</div>
            <small>${new Date(task.created_at).toLocaleString()}</small>
            <div style="margin-top: 8px;">
                <span class="badge">${task.difficulty_override || 'same'}</span>
                ${task.target_grade ? `<span class="badge">${task.target_grade} класс</span>` : ''}
            </div>
        `;
        // ИСПРАВЛЕНО: loadTask больше не нужен sessionId
        item.addEventListener('click', () => loadTask(task.task_id));
        container.appendChild(item);
    }
}

// ИСПРАВЛЕНА: функция loadTask без sessionId
async function loadTask(taskId) {
    showLoading(true, 'Загрузка задания...');
    try {
        // ИСПРАВЛЕНО: убрали sessionId
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

// ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
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

// ========== СТИЛИ ДЛЯ ВАРИАНТОВ (ЕДИНАЯ ВЕРСИЯ) ==========
function addVariantStyles() {
    if (!document.querySelector('#variant-styles')) {
        const style = document.createElement('style');
        style.id = 'variant-styles';
        style.textContent = `
            /* Сохраняем переносы строк в вариантах */
            .variant-content {
                white-space: pre-wrap;
                line-height: 1.6;
                font-family: 'Segoe UI', 'Times New Roman', serif;
            }
            
            /* Критическая ошибка - красный */
            .variant-card.critical {
                border-left: 4px solid #ef4444 !important;
                background: #fef2f2 !important;
            }
            
            .variant-card.critical .variant-title {
                color: #dc2626 !important;
            }
            
            /* Предупреждение - жёлтый/оранжевый */
            .variant-card.warning {
                border-left: 4px solid #f59e0b !important;
                background: #fffbeb !important;
            }
            
            .variant-card.warning .variant-title {
                color: #d97706 !important;
            }
            
            /* Всё хорошо - зелёный */
            .variant-card.ok {
                border-left: 4px solid #22c55e !important;
                background: #f0fdf4 !important;
            }
            
            .variant-card.ok .variant-title {
                color: #16a34a !important;
            }
            
            /* Блок с проблемами */
            .variant-issues {
                margin-top: 12px;
                padding: 12px;
                border-radius: 8px;
            }
            
            .variant-issues.severity-critical {
                background: #fee2e2;
                border-left: 3px solid #dc2626;
            }
            
            .variant-issues.severity-warning {
                background: #fef3c7;
                border-left: 3px solid #f59e0b;
            }
            
            .variant-issues-title {
                font-weight: 600;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 13px;
            }
            
            .severity-critical .variant-issues-title {
                color: #991b1b;
            }
            
            .severity-warning .variant-issues-title {
                color: #92400e;
            }
            
            .variant-issues-list {
                margin: 0;
                padding-left: 20px;
                font-size: 13px;
            }
            
            .severity-critical .variant-issues-list {
                color: #7f1d1d;
            }
            
            .severity-warning .variant-issues-list {
                color: #78350f;
            }
            
            .variant-hint {
                margin-top: 8px;
                padding-top: 8px;
                font-size: 12px;
                color: #6b7280;
                border-top: 1px solid #e5e7eb;
            }
            
            /* Бейджи проверок */
            .variant-validation-badges {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 12px;
                padding-top: 8px;
                border-top: 1px solid #e5e7eb;
            }
            
            .variant-validation-badge {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-size: 11px;
                padding: 2px 8px;
                border-radius: 12px;
                background: white;
            }
            
            .variant-validation-badge.fail {
                color: #dc2626;
                background: #fee2e2;
            }
            
            .variant-validation-badge.pass {
                color: #16a34a;
                background: #dcfce7;
            }
            
            /* Анимация */
            @keyframes warningPulse {
                0%, 100% { border-left-color: #f59e0b; }
                50% { border-left-color: #fcd34d; }
            }
            
            @keyframes criticalPulse {
                0%, 100% { border-left-color: #ef4444; }
                50% { border-left-color: #fca5a5; }
            }
            
            .variant-card.warning {
                animation: warningPulse 2s ease-in-out;
            }
            
            .variant-card.critical {
                animation: criticalPulse 2s ease-in-out;
            }
        `;
        document.head.appendChild(style);
        console.log('✅ Стили для вариантов добавлены');
    }
}

// Вызвать при загрузке
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addVariantStyles);
} else {
    addVariantStyles();
}

// ========== ФУНКЦИЯ ДЛЯ ФОРМАТИРОВАНИЯ СОДЕРЖИМОГО С ПЕРЕНОСАМИ ==========
function formatVariantContent(content) {
    if (!content) return '';
    // Сначала экранируем HTML
    const div = document.createElement('div');
    div.textContent = content;
    let safe = div.innerHTML;
    // Затем заменяем переносы строк на <br> для отображения в HTML
    safe = safe.replace(/\n/g, '<br>');
    // Восстанавливаем LaTeX команды
    safe = safe.replace(/\\\(/g, '\\(')
               .replace(/\\\)/g, '\\)')
               .replace(/\\\[/g, '\\[')
               .replace(/\\\]/g, '\\]');
    return safe;
}


if (!document.querySelector('#variant-problem-styles')) {
    const style = document.createElement('style');
    style.id = 'variant-problem-styles';
    style.textContent = `
        /* Проблемный вариант */
        .variant-card.problem {
            border-left: 4px solid #ef4444;
            background: #fef2f2;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
        }
        
        .variant-card.problem .variant-title {
            color: #dc2626;
        }
        
        .variant-issues {
            margin-top: 12px;
            padding: 10px;
            background: #fee2e2;
            border-radius: 8px;
            border-left: 3px solid #dc2626;
        }
        
        .variant-issues-title {
            font-weight: 600;
            color: #991b1b;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .variant-issues-list {
            margin: 0;
            padding-left: 20px;
            color: #7f1d1d;
            font-size: 13px;
        }
        
        .variant-issues-list li {
            margin: 4px 0;
        }
        
        .variant-validation-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #fecaca;
        }
        
        .variant-validation-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 12px;
            background: white;
        }
        
        .variant-validation-badge.fail {
            color: #dc2626;
            background: #fee2e2;
        }
        
        .variant-validation-badge.pass {
            color: #16a34a;
            background: #dcfce7;
        }
    `;
    document.head.appendChild(style);
}



// В ui.js - добавьте или обновите эти стили
function addProblemVariantStyles() {
    if (!document.querySelector('#variant-styles')) {
        const style = document.createElement('style');
        style.id = 'variant-styles';
        style.textContent = `
            /* Критическая ошибка - красный */
            .variant-card.critical {
                border-left: 4px solid #ef4444 !important;
                background: #fef2f2 !important;
            }
            
            .variant-card.critical .variant-title {
                color: #dc2626 !important;
            }
            
            /* Предупреждение - жёлтый/оранжевый */
            .variant-card.warning {
                border-left: 4px solid #f59e0b !important;
                background: #fffbeb !important;
            }
            
            .variant-card.warning .variant-title {
                color: #d97706 !important;
            }
            
            /* Всё хорошо - зелёный */
            .variant-card.ok {
                border-left: 4px solid #22c55e !important;
                background: #f0fdf4 !important;
            }
            
            .variant-card.ok .variant-title {
                color: #16a34a !important;
            }
            
            /* Блок с проблемами */
            .variant-issues {
                margin-top: 12px;
                padding: 12px;
                border-radius: 8px;
            }
            
            .variant-issues.severity-critical {
                background: #fee2e2;
                border-left: 3px solid #dc2626;
            }
            
            .variant-issues.severity-warning {
                background: #fef3c7;
                border-left: 3px solid #f59e0b;
            }
            
            .variant-issues-title {
                font-weight: 600;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 13px;
            }
            
            .severity-critical .variant-issues-title {
                color: #991b1b;
            }
            
            .severity-warning .variant-issues-title {
                color: #92400e;
            }
            
            .variant-issues-list {
                margin: 0;
                padding-left: 20px;
                font-size: 13px;
            }
            
            .severity-critical .variant-issues-list {
                color: #7f1d1d;
            }
            
            .severity-warning .variant-issues-list {
                color: #78350f;
            }
            
            .variant-hint {
                margin-top: 8px;
                padding-top: 8px;
                font-size: 12px;
                color: #6b7280;
                border-top: 1px solid #e5e7eb;
            }
            
            /* Бейджи проверок */
            .variant-validation-badges {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 12px;
                padding-top: 8px;
                border-top: 1px solid #e5e7eb;
            }
            
            .variant-validation-badge {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-size: 11px;
                padding: 2px 8px;
                border-radius: 12px;
                background: white;
            }
            
            .variant-validation-badge.fail {
                color: #dc2626;
                background: #fee2e2;
            }
            
            .variant-validation-badge.pass {
                color: #16a34a;
                background: #dcfce7;
            }
            
            /* Анимация */
            @keyframes warningPulse {
                0%, 100% { border-left-color: #f59e0b; }
                50% { border-left-color: #fcd34d; }
            }
            
            @keyframes criticalPulse {
                0%, 100% { border-left-color: #ef4444; }
                50% { border-left-color: #fca5a5; }
            }
            
            .variant-card.warning {
                animation: warningPulse 2s ease-in-out;
            }
            
            .variant-card.critical {
                animation: criticalPulse 2s ease-in-out;
            }
        `;
        document.head.appendChild(style);
        console.log('✅ Стили для вариантов добавлены');
    }
}

// Вызвать при загрузке
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addProblemVariantStyles);
} else {
    addProblemVariantStyles();
}


document.addEventListener('click', async (e) => {
    // Редактирование
    if (e.target.classList.contains('edit-variant')) {
        const variantNum = e.target.dataset.variant;
        const content = currentVariants?.[variantNum];
        if (content) {
            openEditModal(variantNum, content);
        }
    }
    
    // Перегенерация
    if (e.target.classList.contains('regenerate-variant')) {
        const variantNum = e.target.dataset.variant;
        if (confirm(`Перегенерировать вариант ${variantNum}?`)) {
            await handleRegenerateVariant(parseInt(variantNum));
        }
    }
});
