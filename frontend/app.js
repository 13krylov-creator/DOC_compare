// СравнениеДок Платформа - Фронтенд
const API_BASE = '/api/v1';

let state = {
    documents: [],
    selectedMode: 'line-by-line',
    selectedStrategy: 'MOST_RECENT',
    selectedMergeDocs: [],
    currentMergeId: null,
    currentView: 'compare',
    lastMergedDocumentId: null,
    currentUser: null
};

// Load current user from oauth2-proxy (via /api/v1/auth/me)
async function loadCurrentUser() {
    console.log('[AUTH] Loading current user from /api/v1/auth/me...');
    try {
        const response = await fetch(`${API_BASE}/auth/me`);
        console.log('[AUTH] /auth/me response status:', response.status);
        if (response.ok) {
            state.currentUser = await response.json();
            console.log('[AUTH] User loaded successfully:', JSON.stringify(state.currentUser));
            updateUserInfo();
        } else {
            const errorText = await response.text();
            console.warn('[AUTH] Failed to load user. Status:', response.status, 'Body:', errorText);
            state.currentUser = null;
            updateUserInfo();
        }
    } catch (error) {
        console.error('[AUTH] Error loading user:', error);
        state.currentUser = null;
        updateUserInfo();
    }
}

// Update user info display in navbar
function updateUserInfo() {
    const userNameEl = document.getElementById('userName');

    console.log('[AUTH] updateUserInfo called, currentUser:', state.currentUser ? state.currentUser.email : 'null');

    if (state.currentUser) {
        const name = state.currentUser.full_name ||
            state.currentUser.username ||
            state.currentUser.email ||
            'Пользователь';
        console.log('[AUTH] Displaying user name:', name);
        userNameEl.textContent = name;
    } else {
        console.log('[AUTH] No user data, showing fallback');
        userNameEl.textContent = 'Пользователь';
    }
}

// Logout - redirect to oauth2-proxy logout endpoint
function logout() {
    console.log('[AUTH] Logging out via /oauth2/sign_out');
    window.location.href = '/oauth2/sign_out?rd=' + encodeURIComponent(window.location.origin);
}

// Инициализация - oauth2-proxy handles auth via cookies, no Bearer tokens needed
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    loadDocuments();
    setupEventListeners();
    showView('compare');
});

function setupEventListeners() {
    // Навигация между вкладками
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = e.target.dataset.view;
            if (view) showView(view);
        });
    });

    // Кнопки режима сравнения
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.selectedMode = btn.dataset.mode;

            const aiPromptSection = document.getElementById('aiPromptSection');
            if (aiPromptSection) {
                aiPromptSection.classList.toggle('hidden', state.selectedMode !== 'semantic');
            }
        });
    });

    // Кнопки стратегии слияния
    document.querySelectorAll('.strategy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.strategy-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.selectedStrategy = btn.dataset.strategy;
        });
    });

    // Зона загрузки для сравнения
    setupUploadZone('uploadZone', 'fileInput');
    // Зона загрузки для слияния
    setupUploadZone('uploadZoneMerge', 'fileInputMerge');
}

function setupUploadZone(zoneId, inputId) {
    const uploadZone = document.getElementById(zoneId);
    const fileInput = document.getElementById(inputId);
    if (!uploadZone || !fileInput) return;

    uploadZone.addEventListener('click', (e) => {
        if (e.target.tagName !== 'BUTTON') fileInput.click();
    });
    uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        uploadFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', (e) => uploadFiles(e.target.files));
}

function showView(viewId) {
    state.currentView = viewId;

    // Скрыть все секции
    document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
    // Показать выбранную
    document.getElementById(viewId)?.classList.remove('hidden');

    // Обновить навигацию
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelector(`[data-view="${viewId}"]`)?.classList.add('active');
}

// ===================== INLINE PROGRESS & LOGS =====================
function showInlineProgress(containerId, title) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.classList.remove('hidden');
    container.querySelector('.progress-title-inline').textContent = title;
    container.querySelector('.progress-percent-inline').textContent = '0%';
    container.querySelector('.progress-fill-inline').style.width = '0%';
    container.querySelector('.inline-log').innerHTML = '';

    // Collapse log section by default
    const logSection = container.querySelector('.log-section');
    if (logSection) {
        logSection.classList.remove('expanded');
    }

    addInlineLog(containerId, `🚀 Начало: ${title}`);
}

function updateInlineProgress(containerId, percent, message) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.querySelector('.progress-percent-inline').textContent = `${percent}%`;
    container.querySelector('.progress-fill-inline').style.width = `${percent}%`;

    if (message) {
        container.querySelector('.progress-title-inline').textContent = message;
    }
}

function addInlineLog(containerId, message, type = 'info') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const logContainer = container.querySelector('.inline-log');
    const time = new Date().toLocaleTimeString('ru-RU');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;

    let icon = 'ℹ️';
    if (type === 'error') icon = '❌';
    else if (type === 'success') icon = '✅';
    else if (type === 'warning') icon = '⚠️';
    else if (type === 'ai') icon = '🧠';
    else if (type === 'ocr') icon = '📷';

    entry.innerHTML = `<span class="log-time">[${time}]</span> ${icon} ${message}`;
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;

    // Update log count
    const logCount = container.querySelector('.log-count');
    if (logCount) {
        const count = logContainer.querySelectorAll('.log-entry').length;
        logCount.textContent = `${count} записей`;
    }
}

function toggleLogSection(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const logSection = container.querySelector('.log-section');
    if (logSection) {
        logSection.classList.toggle('expanded');
    }
}

function clearInlineProgress(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.querySelector('.progress-title-inline').textContent = 'Обработка...';
    container.querySelector('.progress-percent-inline').textContent = '0%';
    container.querySelector('.progress-fill-inline').style.width = '0%';
    container.querySelector('.inline-log').innerHTML = '';

    const logCount = container.querySelector('.log-count');
    if (logCount) {
        logCount.textContent = '0 записей';
    }
}

function completeInlineProgress(containerId, message) {
    updateInlineProgress(containerId, 100, message);
    addInlineLog(containerId, message, 'success');
    // Do NOT hide the progress - keep it visible
}

// ===================== ДОКУМЕНТЫ =====================
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents/`);
        if (response.ok) {
            const data = await response.json();
            state.documents = data.documents || [];
        } else {
            state.documents = [];
        }
        renderDocumentsCompact();
        populateSelects();
        renderMergeDocsList();
    } catch (error) {
        console.log('Загрузка документов...');
        state.documents = [];
        renderDocumentsCompact();
    }
}

function renderDocumentsCompact() {
    const container = document.getElementById('docsItems');
    const count = document.getElementById('docCount');

    if (!container) return;

    count.textContent = `${state.documents.length} файлов`;

    if (state.documents.length === 0) {
        container.innerHTML = '<div class="empty-docs">Нет загруженных файлов</div>';
        return;
    }

    container.innerHTML = state.documents.map(doc => `
        <div class="doc-item-compact" data-id="${doc.id}">
            <span class="doc-icon-small">${getFileIcon(doc.file_type)}</span>
            <span class="doc-name-compact">${escapeHtml(doc.name)}</span>
            <span class="doc-size-compact">${formatSize(doc.file_size)}</span>
            <button class="doc-download-btn" onclick="downloadDocument('${doc.id}', '${escapeHtml(doc.name).replace(/'/g, "\\'")}');" title="Скачать">📥</button>
            <button class="doc-delete-btn" onclick="deleteDocument('${doc.id}')" title="Удалить">🗑</button>
        </div>
    `).join('');
}

function getFileIcon(type) {
    const icons = { 'pdf': '📄', 'docx': '📝', 'txt': '📃' };
    return icons[type?.toLowerCase()] || '📄';
}

async function uploadFiles(files) {
    const progressId = state.currentView === 'merge' ? 'mergeProgress' : 'compareProgress';

    for (const file of files) {
        showInlineProgress(progressId, `Загрузка: ${file.name}`);

        try {
            // Проверка файла
            addInlineLog(progressId, `Проверка файла: ${file.name}`);
            updateInlineProgress(progressId, 10, 'Проверка формата...');

            const allowedTypes = ['.pdf', '.docx', '.txt'];
            const ext = '.' + file.name.split('.').pop().toLowerCase();
            if (!allowedTypes.includes(ext)) {
                addInlineLog(progressId, `Неподдерживаемый формат: ${ext}`, 'error');
                continue;
            }

            if (file.size > 50 * 1024 * 1024) {
                addInlineLog(progressId, `Файл слишком большой: ${formatSize(file.size)}`, 'error');
                continue;
            }

            addInlineLog(progressId, `Формат OK: ${ext}, размер: ${formatSize(file.size)}`, 'success');
            updateInlineProgress(progressId, 20, 'Загрузка на сервер...');

            // Загрузка
            addInlineLog(progressId, 'Отправка файла на сервер...');

            const formData = new FormData();
            formData.append('file', file);
            formData.append('name', file.name);

            const response = await fetch(`${API_BASE}/documents/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errorMsg = `HTTP ${response.status}`;
                if (response.status === 413) {
                    errorMsg = 'Файл слишком большой для сервера (nginx client_max_body_size). Увеличьте лимит в nginx.';
                } else if (response.status === 401) {
                    errorMsg = 'Не авторизован. Перезайдите в систему.';
                } else {
                    try {
                        const err = await response.json();
                        errorMsg = err.detail || response.statusText;
                    } catch (e) {
                        const text = await response.text().catch(() => '');
                        errorMsg = text || response.statusText;
                    }
                }
                addInlineLog(progressId, `Ошибка загрузки: ${errorMsg}`, 'error');
                console.error(`[UPLOAD] Error uploading ${file.name}: status=${response.status}`, errorMsg);
                continue;
            }

            const result = await response.json();
            addInlineLog(progressId, `Файл загружен, ID: ${result.id}`, 'success');

            // OCR обработка (если PDF)
            if (ext === '.pdf') {
                updateInlineProgress(progressId, 50, 'OCR распознавание...');
                addInlineLog(progressId, 'Запуск OCR для распознавания текста...', 'ocr');
                addInlineLog(progressId, 'Отправка запроса к Chandra Vision API...', 'ocr');

                // Симуляция OCR (реальная обработка на сервере)
                await new Promise(r => setTimeout(r, 500));

                if (result.extracted_text) {
                    addInlineLog(progressId, `OCR завершён, извлечено ${result.extracted_text.length} символов`, 'success');
                } else {
                    addInlineLog(progressId, 'OCR: текст не найден или документ пустой', 'warning');
                }
            }

            // Индексация
            updateInlineProgress(progressId, 80, 'Индексация...');
            addInlineLog(progressId, 'Сохранение в базу данных...');
            await new Promise(r => setTimeout(r, 300));
            addInlineLog(progressId, 'Создание поисковых индексов...', 'success');

            completeInlineProgress(progressId, `✅ ${file.name} успешно загружен`);
            showToast(`✓ ${file.name} загружен`, 'success');

        } catch (error) {
            addInlineLog(progressId, `Критическая ошибка: ${error.message}`, 'error');
            showToast(`Ошибка загрузки ${file.name}`, 'error');
        }
    }

    // Progress logs remain visible - user can collapse them
    loadDocuments();
}

async function deleteDocument(id) {
    if (!confirm('Удалить этот документ?')) return;
    try {
        await fetch(`${API_BASE}/documents/${id}`, {
            method: 'DELETE'
        });
        showToast('Документ удалён', 'success');
        loadDocuments();
    } catch (error) {
        showToast('Ошибка удаления', 'error');
    }
}

// ===================== СРАВНЕНИЕ =====================
function populateSelects() {
    const options = state.documents.map(d => `<option value="${d.id}">${escapeHtml(d.name)}</option>`).join('');
    const defaultOpt = '<option value="">Выберите документ</option>';

    const doc1 = document.getElementById('doc1Select');
    const doc2 = document.getElementById('doc2Select');

    if (doc1) doc1.innerHTML = defaultOpt + options;
    if (doc2) doc2.innerHTML = defaultOpt + options;
}

async function runComparison() {
    const doc1 = document.getElementById('doc1Select').value;
    const doc2 = document.getElementById('doc2Select').value;

    if (!doc1 || !doc2) { showToast('Выберите оба документа', 'warning'); return; }
    if (doc1 === doc2) { showToast('Выберите разные документы', 'warning'); return; }

    const progressId = 'compareProgress';
    const modeLabel = state.selectedMode === 'semantic' ? 'Семантический + AI' : 'Построчный';

    // Clear previous logs before starting
    clearInlineProgress(progressId);
    showInlineProgress(progressId, `Сравнение (${modeLabel})`);

    try {
        // Загрузка документов
        addInlineLog(progressId, 'Загрузка содержимого документов...');
        updateInlineProgress(progressId, 10, 'Загрузка документов...');

        const doc1Name = state.documents.find(d => d.id === doc1)?.name || 'Документ 1';
        const doc2Name = state.documents.find(d => d.id === doc2)?.name || 'Документ 2';

        addInlineLog(progressId, `Документ 1: ${doc1Name}`);
        addInlineLog(progressId, `Документ 2: ${doc2Name}`);

        // Токенизация
        updateInlineProgress(progressId, 25, 'Токенизация текста...');
        addInlineLog(progressId, 'Разбивка текста на токены для анализа...');

        // AI анализ (для семантического режима)
        if (state.selectedMode === 'semantic') {
            updateInlineProgress(progressId, 40, 'AI анализ...');
            addInlineLog(progressId, '🧠 Запуск семантического анализа...', 'ai');
            addInlineLog(progressId, 'Подключение к GPT API...', 'ai');

            const customPrompt = document.getElementById('customPrompt')?.value || '';
            if (customPrompt) {
                addInlineLog(progressId, `Пользовательский промпт: "${customPrompt.substring(0, 50)}..."`, 'ai');
            }
        }

        // Выполнение сравнения
        updateInlineProgress(progressId, 50, 'Выполнение сравнения...');
        addInlineLog(progressId, 'Отправка запроса на сервер...');

        const showFullDoc = document.getElementById('showFullDocument')?.checked ?? false;
        const customPrompt = document.getElementById('customPrompt')?.value || '';

        let url = `${API_BASE}/compare/${doc1}/vs/${doc2}?mode=${state.selectedMode}&show_full=${showFullDoc}`;

        const requestOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (state.selectedMode === 'semantic' && customPrompt.trim()) {
            requestOptions.body = JSON.stringify({ custom_prompt: customPrompt.trim() });
        }

        const response = await fetch(url, requestOptions);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            addInlineLog(progressId, `Ошибка сервера: ${response.status} ${response.statusText}`, 'error');
            if (errorData.detail) {
                addInlineLog(progressId, `Детали: ${errorData.detail}`, 'error');
            }
            throw new Error(errorData.detail || 'Ошибка сравнения');
        }

        const result = await response.json();

        addInlineLog(progressId, `Получен ответ от сервера`, 'success');

        // Логирование результатов AI
        if (state.selectedMode === 'semantic') {
            if (result.ai_enhanced) {
                addInlineLog(progressId, '✅ AI анализ выполнен успешно (GPT)', 'ai');
            } else {
                addInlineLog(progressId, '⚠️ AI недоступен, использован автоматический анализ', 'warning');
            }

            if (result.ai_summary) {
                addInlineLog(progressId, `AI резюме: ${result.ai_summary.substring(0, 100)}...`, 'ai');
            }
        }

        // Классификация изменений
        updateInlineProgress(progressId, 80, 'Классификация изменений...');
        addInlineLog(progressId, `Найдено изменений: ${result.summary?.total_changes || 0}`);
        addInlineLog(progressId, `🔴 Критичных: ${result.summary?.critical_changes || 0}`);
        addInlineLog(progressId, `🟡 Важных: ${result.summary?.major_changes || 0}`);
        addInlineLog(progressId, `🟢 Мелких: ${result.summary?.minor_changes || 0}`);

        // Формирование отчёта
        updateInlineProgress(progressId, 95, 'Формирование отчёта...');
        addInlineLog(progressId, 'Построение визуализации различий...');

        completeInlineProgress(progressId, '✅ Сравнение завершено');

        renderResults(result);

    } catch (error) {
        addInlineLog(progressId, `❌ Критическая ошибка: ${error.message}`, 'error');
        showToast('Ошибка сравнения', 'error');
    }
    // Progress logs remain visible - user can collapse them
}

function renderResults(result) {
    document.getElementById('resultsPanel').classList.remove('hidden');

    document.getElementById('totalChanges').textContent = result.summary?.total_changes || 0;
    document.getElementById('criticalChanges').textContent = result.summary?.critical_changes || 0;
    document.getElementById('majorChanges').textContent = result.summary?.major_changes || 0;
    document.getElementById('minorChanges').textContent = result.summary?.minor_changes || 0;
    document.getElementById('similarity').textContent = Math.round((result.summary?.similarity_score || 0) * 100) + '%';

    const doc1Name = state.documents.find(d => d.id === document.getElementById('doc1Select').value)?.name || 'Документ 1';
    const doc2Name = state.documents.find(d => d.id === document.getElementById('doc2Select').value)?.name || 'Документ 2';

    document.getElementById('diffFilename1').textContent = doc1Name;
    document.getElementById('diffFilename2').textContent = doc2Name;

    // AI Summary
    const aiSummarySection = document.getElementById('aiSummarySection');
    const aiSummaryContent = document.getElementById('aiSummaryContent');
    const aiBadge = document.getElementById('aiBadge');

    if (aiSummarySection && result.ai_summary) {
        let formattedSummary = result.ai_summary
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.+?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');

        aiSummaryContent.innerHTML = formattedSummary;

        if (result.ai_enhanced) {
            aiBadge.textContent = 'GPT';
            aiBadge.classList.remove('fallback');
        } else {
            aiBadge.textContent = 'Авто';
            aiBadge.classList.add('fallback');
        }

        aiSummarySection.classList.remove('hidden');
    } else {
        aiSummarySection?.classList.add('hidden');
    }

    renderSideBySideDiff(result);

    // Прокрутка к результатам
    document.getElementById('resultsPanel').scrollIntoView({ behavior: 'smooth' });
}

function renderSideBySideDiff(result) {
    const diffBody = document.getElementById('diffBody');

    // Fallback to old panes if table not found
    const leftPane = document.getElementById('diffLeft');
    const rightPane = document.getElementById('diffRight');

    if (result.diff_lines) {
        const leftLines = result.diff_lines.left;
        const rightLines = result.diff_lines.right;

        // Use table for synchronized row heights
        if (diffBody) {
            let html = '';
            for (let i = 0; i < leftLines.length; i++) {
                const left = leftLines[i];
                const right = rightLines[i];
                html += `
                    <tr>
                        <td>
                            <div class="diff-line ${left.type}">
                                <span class="diff-line-num">${left.num || ''}</span>
                                <span class="diff-line-content">${left.type === 'empty' ? '&nbsp;' : (left.html || escapeHtml(left.text) || '&nbsp;')}</span>
                            </div>
                        </td>
                        <td>
                            <div class="diff-line ${right.type}">
                                <span class="diff-line-num">${right.num || ''}</span>
                                <span class="diff-line-content">${right.type === 'empty' ? '&nbsp;' : (right.html || escapeHtml(right.text) || '&nbsp;')}</span>
                            </div>
                        </td>
                    </tr>
                `;
            }
            diffBody.innerHTML = html;
            return;
        }

        // Fallback to old method
        if (leftPane && rightPane) {
            leftPane.innerHTML = leftLines.map(line => `
                <div class="diff-line ${line.type}">
                    <span class="diff-line-num">${line.num || ''}</span>
                    <span class="diff-line-content">${line.type === 'empty' ? '&nbsp;' : (line.html || escapeHtml(line.text) || '&nbsp;')}</span>
                </div>
            `).join('');

            rightPane.innerHTML = rightLines.map(line => `
                <div class="diff-line ${line.type}">
                    <span class="diff-line-num">${line.num || ''}</span>
                    <span class="diff-line-content">${line.type === 'empty' ? '&nbsp;' : (line.html || escapeHtml(line.text) || '&nbsp;')}</span>
                </div>
            `).join('');

            syncDiffScroll();
        }
        return;
    }

    if (!result.changes?.length) {
        if (diffBody) {
            diffBody.innerHTML = '<tr><td colspan="2" class="empty-diff"><p>Документы идентичны</p></td></tr>';
        } else if (leftPane && rightPane) {
            leftPane.innerHTML = '<div class="empty-diff"><p>Документы идентичны</p></div>';
            rightPane.innerHTML = '<div class="empty-diff"><p>Различий нет</p></div>';
        }
        return;
    }

    const diffLines = buildDiffLines(result.changes);

    if (diffBody) {
        let html = '';
        for (let i = 0; i < diffLines.left.length; i++) {
            const left = diffLines.left[i];
            const right = diffLines.right[i];
            html += `
                <tr>
                    <td>
                        <div class="diff-line ${left.type}">
                            <span class="diff-line-num">${left.num || ''}</span>
                            <span class="diff-line-content">${left.type === 'empty' ? '&nbsp;' : left.html}</span>
                        </div>
                    </td>
                    <td>
                        <div class="diff-line ${right.type}">
                            <span class="diff-line-num">${right.num || ''}</span>
                            <span class="diff-line-content">${right.type === 'empty' ? '&nbsp;' : right.html}</span>
                        </div>
                    </td>
                </tr>
            `;
        }
        diffBody.innerHTML = html;
    } else if (leftPane && rightPane) {
        leftPane.innerHTML = diffLines.left.map(line => `
            <div class="diff-line ${line.type}">
                <span class="diff-line-num">${line.num || ''}</span>
                <span class="diff-line-content">${line.type === 'empty' ? '&nbsp;' : line.html}</span>
            </div>
        `).join('');

        rightPane.innerHTML = diffLines.right.map(line => `
            <div class="diff-line ${line.type}">
                <span class="diff-line-num">${line.num || ''}</span>
                <span class="diff-line-content">${line.type === 'empty' ? '&nbsp;' : line.html}</span>
            </div>
        `).join('');

        syncDiffScroll();
    }
}

function buildDiffLines(changes) {
    const left = [];
    const right = [];
    let leftNum = 1;
    let rightNum = 1;

    changes.forEach(change => {
        const type = change.type?.toUpperCase();
        const originalLines = (change.original_text || '').split('\n').filter(l => l.trim());
        const newLines = (change.new_text || '').split('\n').filter(l => l.trim());

        if (type === 'DELETED') {
            // Deleted lines - show on left with empty placeholders on right
            originalLines.forEach(line => {
                left.push({ num: leftNum++, type: 'deleted', html: highlightText(line, 'deleted') });
                right.push({ num: '', type: 'empty', html: '' });
            });
        } else if (type === 'ADDED') {
            // Added lines - empty placeholders on left, content on right
            newLines.forEach(line => {
                left.push({ num: '', type: 'empty', html: '' });
                right.push({ num: rightNum++, type: 'added', html: highlightText(line, 'added') });
            });
        } else if (type === 'MODIFIED' || type === 'REWORDED') {
            const maxLen = Math.max(originalLines.length, newLines.length);
            for (let i = 0; i < maxLen; i++) {
                const origLine = originalLines[i] || '';
                const newLine = newLines[i] || '';

                if (origLine && newLine) {
                    const { leftHtml, rightHtml } = computeInlineDiff(origLine, newLine);
                    left.push({ num: leftNum++, type: 'modified', html: leftHtml });
                    right.push({ num: rightNum++, type: 'modified', html: rightHtml });
                } else if (origLine) {
                    // Line deleted within modification
                    left.push({ num: leftNum++, type: 'deleted', html: highlightText(origLine, 'deleted') });
                    right.push({ num: '', type: 'empty', html: '' });
                } else if (newLine) {
                    // Line added within modification
                    left.push({ num: '', type: 'empty', html: '' });
                    right.push({ num: rightNum++, type: 'added', html: highlightText(newLine, 'added') });
                }
            }
        } else {
            originalLines.forEach(line => {
                left.push({ num: leftNum++, type: 'unchanged', html: escapeHtml(line) });
                right.push({ num: rightNum++, type: 'unchanged', html: escapeHtml(line) });
            });
        }
    });

    return { left, right };
}

function computeInlineDiff(origText, newText) {
    const origWords = origText.split(/(\s+)/);
    const newWords = newText.split(/(\s+)/);

    let leftHtml = '';
    let rightHtml = '';

    const maxLen = Math.max(origWords.length, newWords.length);

    for (let i = 0; i < maxLen; i++) {
        const origWord = origWords[i] || '';
        const newWord = newWords[i] || '';

        if (origWord === newWord) {
            leftHtml += escapeHtml(origWord);
            rightHtml += escapeHtml(newWord);
        } else {
            if (origWord) leftHtml += `<span class="diff-highlight-deleted">${escapeHtml(origWord)}</span>`;
            if (newWord) rightHtml += `<span class="diff-highlight-added">${escapeHtml(newWord)}</span>`;
        }
    }

    return { leftHtml, rightHtml };
}

function highlightText(text, type) {
    const escaped = escapeHtml(text);
    if (type === 'deleted') return `<span class="diff-highlight-deleted">${escaped}</span>`;
    if (type === 'added') return `<span class="diff-highlight-added">${escaped}</span>`;
    return escaped;
}

function syncDiffScroll() {
    const leftPane = document.getElementById('diffLeft');
    const rightPane = document.getElementById('diffRight');

    leftPane.addEventListener('scroll', () => { rightPane.scrollTop = leftPane.scrollTop; });
    rightPane.addEventListener('scroll', () => { leftPane.scrollTop = rightPane.scrollTop; });
}

// ===================== СЛИЯНИЕ =====================
function renderMergeDocsList() {
    const container = document.getElementById('mergeDocsList');
    if (!container) return;

    container.innerHTML = state.documents.map(doc => `
        <label class="merge-doc-item ${state.selectedMergeDocs.includes(doc.id) ? 'selected' : ''}">
            <input type="checkbox" value="${doc.id}" ${state.selectedMergeDocs.includes(doc.id) ? 'checked' : ''} onchange="toggleMergeDoc('${doc.id}')">
            <span class="merge-doc-icon">${getFileIcon(doc.file_type)}</span>
            <span class="merge-doc-name">${escapeHtml(doc.name)}</span>
        </label>
    `).join('') || '<div class="empty-docs">Нет загруженных файлов</div>';
}

function toggleMergeDoc(docId) {
    const idx = state.selectedMergeDocs.indexOf(docId);
    if (idx > -1) {
        state.selectedMergeDocs.splice(idx, 1);
    } else if (state.selectedMergeDocs.length < 10) {
        state.selectedMergeDocs.push(docId);
    } else {
        showToast('Максимум 10 документов для слияния', 'warning');
        return;
    }
    renderMergeDocsList();
}

async function startMerge() {
    if (state.selectedMergeDocs.length < 2) {
        showToast('Выберите минимум 2 документа для слияния', 'warning');
        return;
    }

    const progressId = 'mergeProgress';
    const strategyLabel = {
        'MOST_RECENT': 'Последняя версия',
        'MANUAL': 'Вручную'
    }[state.selectedStrategy] || state.selectedStrategy;

    // Clear previous logs before starting
    clearInlineProgress(progressId);
    showInlineProgress(progressId, `Слияние (${strategyLabel})`);

    try {
        // Загрузка документов
        addInlineLog(progressId, `Выбрано документов: ${state.selectedMergeDocs.length}`);
        updateInlineProgress(progressId, 10, 'Загрузка документов...');

        state.selectedMergeDocs.forEach((id, i) => {
            const doc = state.documents.find(d => d.id === id);
            addInlineLog(progressId, `${i + 1}. ${doc?.name || id}`);
        });

        // Сравнение
        updateInlineProgress(progressId, 30, 'Сравнение документов...');
        addInlineLog(progressId, 'Анализ различий между документами...');

        // Выполнение слияния
        updateInlineProgress(progressId, 50, 'Выполнение слияния...');
        addInlineLog(progressId, `Стратегия: ${strategyLabel}`);
        addInlineLog(progressId, 'Отправка запроса на сервер...');

        const response = await fetch(`${API_BASE}/merge/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            },
            body: JSON.stringify({
                document_ids: state.selectedMergeDocs,
                merge_strategy: state.selectedStrategy
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            addInlineLog(progressId, `Ошибка сервера: ${response.status}`, 'error');
            if (errorData.detail) {
                addInlineLog(progressId, `Детали: ${errorData.detail}`, 'error');
            }
            throw new Error(errorData.detail || 'Ошибка слияния');
        }

        const result = await response.json();

        addInlineLog(progressId, `Слияние выполнено, ID: ${result.id}`, 'success');

        // Обнаружение конфликтов
        updateInlineProgress(progressId, 80, 'Анализ конфликтов...');
        addInlineLog(progressId, `Найдено конфликтов: ${result.conflicts_count || 0}`);

        // In MANUAL mode, auto_resolved is always 0 - user decides everything
        if (state.selectedStrategy === 'MOST_RECENT') {
            addInlineLog(progressId, `Авто-разрешено: ${result.auto_resolved || 0}`);
        }

        // Count unresolved conflicts
        const unresolvedCount = result.conflicts.filter(c => c.consensus_variant === null || c.consensus_variant === undefined).length;

        if (state.selectedStrategy === 'MANUAL') {
            if (result.conflicts_count > 0) {
                addInlineLog(progressId, `✋ Режим "Вручную": ${result.conflicts_count} изменений требуют вашего выбора`, 'warning');
            } else {
                addInlineLog(progressId, '✅ Документы идентичны, слияние готово', 'success');
            }
        } else if (unresolvedCount > 0) {
            addInlineLog(progressId, `⚠️ ${unresolvedCount} конфликтов требуют ручного разрешения`, 'warning');
        } else if (result.conflicts_count > 0) {
            addInlineLog(progressId, '✅ Все конфликты разрешены автоматически', 'success');
        } else {
            addInlineLog(progressId, '✅ Конфликтов нет, слияние готово', 'success');
        }

        if (result.recommendation) {
            addInlineLog(progressId, `💡 Рекомендация: ${result.recommendation}`);
        }

        completeInlineProgress(progressId, '✅ Слияние завершено');

        state.currentMergeId = result.id;
        renderMergeResults(result);

    } catch (error) {
        addInlineLog(progressId, `❌ Критическая ошибка: ${error.message}`, 'error');
        showToast('Ошибка слияния', 'error');
    }
    // Progress logs remain visible - user can collapse them
}

function renderMergeResults(result) {
    document.getElementById('mergeResults').classList.remove('hidden');
    document.getElementById('mergeConflicts').textContent = result.conflicts_count;

    // In MANUAL mode, auto_resolved is always 0 - show only in MOST_RECENT mode
    const autoResolvedEl = document.getElementById('mergeAutoResolved');
    const autoResolvedStat = autoResolvedEl.closest('.merge-stat');
    if (state.selectedStrategy === 'MANUAL') {
        autoResolvedStat.style.display = 'none';
    } else {
        autoResolvedStat.style.display = '';
        autoResolvedEl.textContent = result.auto_resolved || 0;
    }

    const conflictsList = document.getElementById('conflictsList');

    // Check if we have unresolved conflicts (no consensus_variant set)
    const unresolvedConflicts = result.conflicts.filter(c => c.consensus_variant === null || c.consensus_variant === undefined);

    if (result.conflicts.length === 0) {
        conflictsList.innerHTML = '<div class="no-conflicts"><span class="success-icon">✅</span> Конфликтов нет! Готово к завершению.</div>';
        document.getElementById('finalizeMergeBtn').disabled = false;
        return;
    }

    // If MANUAL strategy - show ALL conflicts for user to choose (no auto-resolve)
    // If MOST_RECENT strategy - show only unresolved conflicts
    if (state.selectedStrategy === 'MANUAL') {
        // In MANUAL mode, all conflicts require user selection - ignore consensus_variant
        conflictsList.innerHTML = result.conflicts.map((conflict, idx) => `
            <div class="conflict-item" id="conflict-${conflict.index}">
                <div class="conflict-header">
                    <span class="conflict-number">Изменение #${conflict.index + 1}</span>
                    <span class="conflict-location">${conflict.location || 'Неизвестно'}</span>
                    <span class="conflict-type">${getConflictTypeLabel(conflict.type)}</span>
                </div>
                <div class="conflict-variants">
                    ${conflict.variants.map((variant, vIdx) => `
                        <div class="variant-option" onclick="selectVariant(${conflict.index}, ${vIdx})">
                            <input type="radio" name="conflict-${conflict.index}" value="${vIdx}">
                            <div class="variant-content">
                                <div class="variant-source">${escapeHtml(variant.source)}</div>
                                <div class="variant-text">${escapeHtml(variant.content || '(пусто)')}</div>
                                ${variant.votes ? `<div class="variant-votes">👍 ${variant.votes} голосов</div>` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    } else if (unresolvedConflicts.length > 0) {
        // MOST_RECENT mode with some unresolved conflicts
        conflictsList.innerHTML = result.conflicts.map((conflict, idx) => {
            const isAutoResolved = conflict.consensus_variant !== null && conflict.consensus_variant !== undefined;
            return `
            <div class="conflict-item ${isAutoResolved ? 'auto-resolved' : ''}" id="conflict-${conflict.index}">
                <div class="conflict-header">
                    <span class="conflict-number">Конфликт #${conflict.index + 1}</span>
                    <span class="conflict-location">${conflict.location || 'Неизвестно'}</span>
                    <span class="conflict-type">${getConflictTypeLabel(conflict.type)}</span>
                    ${isAutoResolved ? '<span class="auto-resolved-badge">Авто</span>' : ''}
                </div>
                <div class="conflict-variants">
                    ${conflict.variants.map((variant, vIdx) => `
                        <div class="variant-option ${conflict.consensus_variant === vIdx ? 'recommended' : ''}" onclick="selectVariant(${conflict.index}, ${vIdx})">
                            <input type="radio" name="conflict-${conflict.index}" value="${vIdx}" ${conflict.consensus_variant === vIdx ? 'checked' : ''}>
                            <div class="variant-content">
                                <div class="variant-source">${escapeHtml(variant.source)}</div>
                                <div class="variant-text">${escapeHtml(variant.content || '(пусто)')}</div>
                                ${variant.votes ? `<div class="variant-votes">👍 ${variant.votes} голосов</div>` : ''}
                            </div>
                            ${conflict.consensus_variant === vIdx ? '<span class="recommended-badge">Рекомендуется</span>' : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `}).join('');
    } else {
        // All conflicts auto-resolved (MOST_RECENT mode)
        conflictsList.innerHTML = `
            <div class="no-conflicts">
                <span class="success-icon">✅</span> 
                Все ${result.conflicts_count} конфликтов разрешены автоматически! Готово к завершению.
            </div>
        `;
        document.getElementById('finalizeMergeBtn').disabled = false;
        document.getElementById('mergeResults').scrollIntoView({ behavior: 'smooth' });
        return;
    }

    updateFinalizeBtnState();

    // Прокрутка к результатам
    document.getElementById('mergeResults').scrollIntoView({ behavior: 'smooth' });
}

function getConflictTypeLabel(type) {
    const labels = {
        'REPLACE': 'Замена',
        'DELETE': 'Удаление',
        'INSERT': 'Вставка',
        'CONSENSUS': 'Голосование',
        'THREE_WAY': 'Три версии',
        'MANUAL': 'Ручной'
    };
    return labels[type] || type;
}

function selectVariant(conflictIndex, variantIndex) {
    const radios = document.querySelectorAll(`input[name="conflict-${conflictIndex}"]`);
    radios.forEach((r, i) => {
        r.checked = i === variantIndex;
        r.closest('.variant-option').classList.toggle('selected', i === variantIndex);
    });
    updateFinalizeBtnState();
}

function updateFinalizeBtnState() {
    const allConflicts = document.querySelectorAll('.conflict-item');
    let allResolved = true;

    allConflicts.forEach(conflict => {
        const radios = conflict.querySelectorAll('input[type="radio"]');
        const anyChecked = Array.from(radios).some(r => r.checked);
        if (!anyChecked) allResolved = false;
    });

    document.getElementById('finalizeMergeBtn').disabled = !allResolved;
}

async function finalizeMerge() {
    if (!state.currentMergeId) return;

    const progressId = 'mergeProgress';
    addInlineLog(progressId, 'Завершение слияния...');

    const resolutions = [];
    document.querySelectorAll('.conflict-item').forEach(conflict => {
        const conflictIndex = parseInt(conflict.id.replace('conflict-', ''));
        const selectedRadio = conflict.querySelector('input[type="radio"]:checked');
        if (selectedRadio) {
            resolutions.push({
                conflict_index: conflictIndex,
                chosen_variant_index: parseInt(selectedRadio.value)
            });
        }
    });

    try {
        // First resolve any conflicts
        if (resolutions.length > 0) {
            addInlineLog(progressId, `Применение ${resolutions.length} разрешений конфликтов...`);
            const resolveResponse = await fetch(`${API_BASE}/merge/${state.currentMergeId}/resolve-bulk`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader()
                },
                body: JSON.stringify({ resolutions })
            });

            if (!resolveResponse.ok) {
                const err = await resolveResponse.json().catch(() => ({}));
                throw new Error(err.detail || 'Ошибка разрешения конфликтов');
            }

            addInlineLog(progressId, 'Конфликты разрешены', 'success');
        }

        // Now finalize - include time with seconds in name
        addInlineLog(progressId, 'Создание объединённого документа...');
        const now = new Date();
        const dateStr = now.toLocaleDateString('ru-RU');
        const timeStr = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const docName = `Объединённый документ ${dateStr} ${timeStr}`;

        const response = await fetch(`${API_BASE}/merge/${state.currentMergeId}/finalize?name=${encodeURIComponent(docName)}`, {
            method: 'POST',
            headers: { ...getAuthHeader() }
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка финализации');
        }

        const result = await response.json();

        addInlineLog(progressId, `Документ "${result.document_name}" создан успешно!`, 'success');

        // Store the new document ID for download
        state.lastMergedDocumentId = result.new_document_id;

        // Show success with download option
        showMergeSuccess(result);

        state.selectedMergeDocs = [];
        state.currentMergeId = null;
        renderMergeDocsList();
        loadDocuments();

    } catch (error) {
        addInlineLog(progressId, `Ошибка: ${error.message}`, 'error');
        showToast('Ошибка завершения слияния: ' + error.message, 'error');
    }
}

function showMergeSuccess(result) {
    const conflictsList = document.getElementById('conflictsList');
    conflictsList.innerHTML = `
        <div class="merge-success">
            <div class="success-header">
                <span class="success-icon-large">✅</span>
                <h3>Слияние завершено!</h3>
            </div>
            <div class="success-details">
                <p>Создан документ: <strong>${escapeHtml(result.document_name)}</strong></p>
                <p>Размер: ${formatSize(result.content_size)}</p>
            </div>
            <div class="success-actions">
                <button class="btn btn-primary btn-download" onclick="downloadMergedDocument('${result.new_document_id}', '${escapeHtml(result.document_name)}')">
                    📥 Скачать документ
                </button>
                <button class="btn btn-outline" onclick="closeMergeResults()">Закрыть</button>
            </div>
        </div>
    `;

    // Hide the finalize button since merge is complete
    document.getElementById('finalizeMergeBtn').style.display = 'none';
    document.querySelector('.merge-actions button[onclick="cancelMerge()"]').style.display = 'none';
}

async function downloadMergedDocument(docId, docName) {
    return downloadDocument(docId, docName);
}

async function downloadDocument(docId, docName) {
    try {
        const response = await fetch(`${API_BASE}/documents/${docId}/download`, {
            headers: { ...getAuthHeader() }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Ошибка загрузки документа');
        }

        const blob = await response.blob();

        // Get filename from Content-Disposition header if available
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = docName;

        if (contentDisposition) {
            // Try to extract filename from UTF-8 encoded header
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) {
                filename = decodeURIComponent(utf8Match[1]);
            } else {
                // Fallback to regular filename
                const regularMatch = contentDisposition.match(/filename="?([^";\n]+)"?/i);
                if (regularMatch) {
                    filename = regularMatch[1];
                }
            }
        }

        // Ensure proper extension
        if (!filename.endsWith('.docx') && !filename.endsWith('.txt')) {
            filename = `${filename}.docx`;
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        showToast('Документ скачан!', 'success');
    } catch (error) {
        showToast('Ошибка скачивания: ' + error.message, 'error');
    }
}

function closeMergeResults() {
    document.getElementById('mergeResults').classList.add('hidden');
    // Reset buttons visibility
    document.getElementById('finalizeMergeBtn').style.display = '';
    document.querySelector('.merge-actions button[onclick="cancelMerge()"]').style.display = '';
}

function cancelMerge() {
    if (state.currentMergeId) {
        fetch(`${API_BASE}/merge/${state.currentMergeId}`, { method: 'DELETE' });
    }
    document.getElementById('mergeResults').classList.add('hidden');
    state.currentMergeId = null;
}

// ===================== УТИЛИТЫ =====================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatSize(bytes) {
    if (!bytes) return '0 Б';
    const k = 1024;
    const sizes = ['Б', 'КБ', 'МБ', 'ГБ'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });
}
