// СравнениеДок Платформа - Фронтенд
const API_BASE = '/api/v1';

let state = {
    documents: [],
    selectedMode: 'line-by-line',
    selectedStrategy: 'MOST_RECENT',
    selectedMergeDocs: [],
    currentMergeId: null,
    currentView: 'compare',
    currentTool: null,
    lastMergedDocumentId: null,
    currentUser: null,
    toolsFile: null // shared file for tools section
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
        // Приоритет: email > full_name > username
        const name = state.currentUser.email ||
            state.currentUser.full_name ||
            state.currentUser.username ||
            'Пользователь';
        console.log('[AUTH] Displaying user name:', name);
        userNameEl.textContent = name;
    } else {
        console.log('[AUTH] No user data, showing fallback');
        userNameEl.textContent = 'Пользователь';
    }
}

// Logout - redirect to Keycloak logout endpoint
function logout() {
    console.log('[AUTH] Logging out...');
    const redirectUri = encodeURIComponent(window.location.origin);
    // Формируем Keycloak logout URL с client_id и redirect
    const keycloakLogout = 'https://auth.nir.center/realms/platform/protocol/openid-connect/logout'
        + '?client_id=oauth2-proxy'
        + '&post_logout_redirect_uri=' + redirectUri;
    // Передаём через oauth2-proxy sign_out, кодируя весь URL
    window.location.href = '/oauth2/sign_out?rd=' + encodeURIComponent(keycloakLogout);
}

// Инициализация - oauth2-proxy handles auth via cookies, no Bearer tokens needed
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    loadDocuments();
    setupEventListeners();
    setupToolsUploadZone();
    showView('compare');
    checkAnonMLStatus(); // Check ML status on load
});

function setupEventListeners() {
    // Sidebar navigation
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            const tool = item.dataset.tool;
            if (view) showView(view, tool);
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

function showView(viewId, toolId) {
    state.currentView = viewId;
    state.currentTool = toolId || null;

    // Скрыть все секции
    document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
    // Показать выбранную
    document.getElementById(viewId)?.classList.remove('hidden');

    // Обновить sidebar навигацию
    document.querySelectorAll('.sidebar-item').forEach(l => l.classList.remove('active'));
    if (toolId) {
        // Find the sidebar item with matching data-tool
        document.querySelector(`.sidebar-item[data-tool="${toolId}"]`)?.classList.add('active');
    } else {
        document.querySelector(`.sidebar-item[data-view="${viewId}"]`)?.classList.add('active');
    }

    // For tools view, show the specific tool panel
    if (viewId === 'tools' && toolId) {
        // Hide all tool panels
        document.querySelectorAll('#tools .tool-panel').forEach(p => p.classList.add('hidden'));
        // Show the target tool panel
        document.getElementById(toolId)?.classList.remove('hidden');

        // Update section title
        const titleMap = {
            'toolAnonymize': 'Обезличивание',
            'daToolOcr': 'OCR / Распознавание',
            'daToolAsk': 'Вопрос по документу',
            'daToolProtocol': 'Протокол / Суммаризация',
            'daToolTable': 'Извлечение таблиц',
            'daToolMindmap': 'Ментальные карты',
            'daToolCheck': 'Проверка и редактирование',
            'daToolTranslate': 'Перевод документа'
        };
        const titleEl = document.getElementById('toolsSectionTitle');
        if (titleEl) titleEl.textContent = titleMap[toolId] || 'Инструменты';

        // Enable/disable process button for anonymize based on file
        if (toolId === 'toolAnonymize') {
            const btn = document.getElementById('processBtnAnon');
            if (btn) btn.disabled = !state.toolsFile;
        }

        checkAnonMLStatus();
    }
}

// Sidebar toggle
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    // Save state
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
}

// Restore sidebar state from localStorage
document.addEventListener('DOMContentLoaded', () => {
    const collapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (collapsed) {
        document.getElementById('sidebar')?.classList.add('collapsed');
    }
});

// ===================== UNIFIED TOOLS UPLOAD =====================
function setupToolsUploadZone() {
    const zone = document.getElementById('uploadZoneTools');
    const input = document.getElementById('fileInputTools');
    if (!zone || !input) return;

    zone.addEventListener('click', (e) => {
        if (e.target.tagName !== 'BUTTON') input.click();
    });
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) handleToolsUpload(e.dataTransfer.files[0]);
    });
    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleToolsUpload(e.target.files[0]);
    });
}

async function handleToolsUpload(file) {
    const allowedExts = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExts.includes(ext)) {
        showToast(`Неподдерживаемый формат: ${ext}`, 'error');
        return;
    }
    if (file.size > 50 * 1024 * 1024) {
        showToast('Файл слишком большой (макс. 50 МБ)', 'error');
        return;
    }

    // Store file for shared use
    state.toolsFile = file;

    // Show file info while uploading
    document.getElementById('toolsFileInfo').classList.remove('hidden');
    document.getElementById('toolsFileName').textContent = file.name;
    document.getElementById('toolsFileSize').textContent = formatSize(file.size) + ' — загрузка...';
    document.getElementById('uploadZoneTools').style.display = 'none';

    // Also set file for anonymizer
    anonState.selectedFile = file;
    const processBtnAnon = document.getElementById('processBtnAnon');
    if (processBtnAnon) processBtnAnon.disabled = false;

    // Upload to docanalysis backend for parsing/tokens
    try {
        const formData = new FormData();
        formData.append('file', file);

        const resp = await fetch(`${DA_API}/upload`, { method: 'POST', body: formData });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        daState.taskId = data.task_id;
        daState.fileName = data.filename;
        daState.totalTokens = data.total_tokens || 0;

        document.getElementById('toolsFileSize').textContent = formatSize(data.file_size);

        // Show stats
        document.getElementById('daSheetsCount').textContent = data.sheets_count;
        document.getElementById('daTotalTokens').textContent = data.total_tokens.toLocaleString('ru-RU');

        // Calculate cost
        daUpdateCost();

        document.getElementById('daStatsGrid').classList.remove('hidden');

        // Show sheets details
        if (data.sheets && data.sheets.length > 0) {
            const list = document.getElementById('daSheetsList');
            list.innerHTML = data.sheets.map((s, i) => `
                <div class="da-sheet-item">
                    <span class="da-sheet-name">${escapeHtml(s.name)}</span>
                    <span class="da-sheet-tokens">${s.tokens.toLocaleString('ru-RU')} токенов</span>
                </div>
            `).join('');
            document.getElementById('daSheetsDetails').classList.remove('hidden');
        }

        showToast(`✓ ${file.name} загружен и проанализирован`, 'success');

    } catch (error) {
        showToast(`Ошибка загрузки: ${error.message}`, 'error');
        document.getElementById('uploadZoneTools').style.display = '';
        document.getElementById('toolsFileInfo').classList.add('hidden');
        state.toolsFile = null;
        anonState.selectedFile = null;
        if (processBtnAnon) processBtnAnon.disabled = true;
    }
}

function toolsRemoveFile() {
    state.toolsFile = null;
    anonState.selectedFile = null;
    anonState.currentTaskId = null;

    if (daState.taskId) {
        fetch(`${DA_API}/${daState.taskId}`, { method: 'DELETE' }).catch(() => { });
    }
    daState.taskId = null;
    daState.fileName = null;
    daState.totalTokens = 0;

    document.getElementById('uploadZoneTools').style.display = '';
    document.getElementById('toolsFileInfo').classList.add('hidden');
    document.getElementById('fileInputTools').value = '';
    document.getElementById('daStatsGrid')?.classList.add('hidden');
    document.getElementById('daSheetsDetails')?.classList.add('hidden');

    // Reset anonymizer state
    document.getElementById('processBtnAnon').disabled = true;
    document.getElementById('resultsSectionAnon')?.classList.add('hidden');
    document.getElementById('progressSectionAnon')?.classList.add('hidden');

    // Reset DA tool results
    document.getElementById('daAskResult')?.classList.add('hidden');
    document.getElementById('daSummaryResult')?.classList.add('hidden');
    document.getElementById('daTableResult')?.classList.add('hidden');
    document.getElementById('daOcrResult')?.classList.add('hidden');
    document.getElementById('daEditResult')?.classList.add('hidden');
    document.getElementById('daEditDownloadActions')?.classList.add('hidden');
    document.getElementById('daTranslateResult')?.classList.add('hidden');
    document.getElementById('daTranslateDownloadActions')?.classList.add('hidden');
    document.getElementById('daStructureResult')?.classList.add('hidden');
    document.getElementById('daStructureDownloadActions')?.classList.add('hidden');
    document.getElementById('daDownloadProtocolBtn')?.classList.add('hidden');
    document.getElementById('daDownloadTableBtn')?.classList.add('hidden');
    document.getElementById('daDownloadOcrBtn')?.classList.add('hidden');
    document.getElementById('daDownloadOcrPdfBtn')?.classList.add('hidden');
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
                showToast(`❌ Ошибка загрузки: ${errorMsg}`, 'error');
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
            <span class="doc-size-compact">${formatSize(doc.file_size)}</span>
            <button class="doc-download-btn" onclick="event.preventDefault(); event.stopPropagation(); downloadDocument('${doc.id}', '${escapeHtml(doc.name).replace(/'/g, "\\'")}');" title="Скачать">📥</button>
            <button class="doc-delete-btn" onclick="event.preventDefault(); event.stopPropagation(); deleteDocument('${doc.id}')" title="Удалить">🗑</button>
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
                'Content-Type': 'application/json'
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
                    'Content-Type': 'application/json'
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
            method: 'POST'
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
        const response = await fetch(`${API_BASE}/documents/${docId}/download`);

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

// ===================== ОБЕЗЛИЧИВАНИЕ (ANONYMIZER) =====================

const ANON_API = '/api/v1/anonymizer';

// Anonymizer state
let anonState = {
    selectedFile: null,
    currentTaskId: null,
    pollInterval: null,
};

// Profile definitions (from backend DEFAULT_PROFILES)
const ANON_PROFILES = {
    full: {
        name: "Полное обезличивание",
        options: ["prices", "companies", "logos", "personal", "addresses", "requisites", "dates", "technical", "metadata", "watermarks"]
    },
    media: {
        name: "Для СМИ",
        options: ["prices", "companies", "logos", "personal", "addresses", "requisites", "metadata", "watermarks"]
    },
    partners: {
        name: "Для партнеров",
        options: ["prices", "personal", "requisites", "metadata"]
    }
};

// Initialize anonymizer on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    setupAnonEventListeners();
    checkAnonMLStatus();
});

function checkAnonMLStatus() {
    console.log('[DEBUG] Checking status indicators...');
    const gptStatus = document.getElementById('gptStatusAnon');
    const visionStatus = document.getElementById('visionStatusAnon');

    // Simulate checking status (in real app, this would be an API call)
    // For now, we'll set them to active (green pulsing)
    if (gptStatus) {
        console.log('[DEBUG] Setting GPT status to active');
        gptStatus.classList.add('status-active');
        gptStatus.classList.remove('status-inactive');
    } else {
        console.warn('[DEBUG] GPT status element not found');
    }

    if (visionStatus) {
        console.log('[DEBUG] Setting Vision status to active');
        visionStatus.classList.add('status-active');
        visionStatus.classList.remove('status-inactive');
    } else {
        console.warn('[DEBUG] Vision status element not found');
    }
}

function setupAnonEventListeners() {
    // Upload zone now handled by unified tools upload (setupToolsUploadZone)

    // Remove file button
    const removeBtn = document.getElementById('removeFileAnon');
    if (removeBtn) {
        removeBtn.addEventListener('click', clearAnonFile);
    }

    // Profile selector
    const profileSelect = document.getElementById('profileSelectAnon');
    if (profileSelect) {
        profileSelect.addEventListener('change', (e) => {
            const profile = ANON_PROFILES[e.target.value];
            if (profile) {
                applyAnonProfile(profile.options);
            }
        });
    }

    // Select all / Clear all
    const selectAll = document.getElementById('selectAllAnon');
    const clearAll = document.getElementById('clearAllAnon');
    if (selectAll) selectAll.addEventListener('click', () => setAllAnonOptions(true));
    if (clearAll) clearAll.addEventListener('click', () => setAllAnonOptions(false));

    // Process button
    const processBtn = document.getElementById('processBtnAnon');
    if (processBtn) {
        processBtn.addEventListener('click', startAnonymization);
    }

    // Result buttons
    const downloadBtn = document.getElementById('downloadBtnAnon');
    const downloadPdfBtn = document.getElementById('downloadPdfBtnAnon');
    const viewBtn = document.getElementById('viewBtnAnon');
    const previewBtn = document.getElementById('previewBtnAnon');
    const mappingBtn = document.getElementById('mappingBtnAnon');

    if (downloadBtn) downloadBtn.addEventListener('click', () => anonDownload('file'));
    if (downloadPdfBtn) downloadPdfBtn.addEventListener('click', () => anonDownload('pdf'));
    if (viewBtn) viewBtn.addEventListener('click', anonView);
    if (previewBtn) previewBtn.addEventListener('click', anonPreview);
    if (mappingBtn) mappingBtn.addEventListener('click', anonMapping);

    // Close preview modal
    const closePreview = document.getElementById('closePreviewAnon');
    if (closePreview) {
        closePreview.addEventListener('click', () => {
            document.getElementById('previewModalAnon').classList.remove('show');
        });
    }
    // Close modal on backdrop click
    const modal = document.getElementById('previewModalAnon');
    if (modal) {
        const backdrop = modal.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', () => modal.classList.remove('show'));
        }
    }
}

// handleAnonFile and clearAnonFile are now handled by unified tools upload
// anonState.selectedFile is set by handleToolsUpload()

function applyAnonProfile(options) {
    document.querySelectorAll('.anon-option-card input[type="checkbox"]').forEach(cb => {
        cb.checked = options.includes(cb.value);
    });
}

function setAllAnonOptions(checked) {
    document.querySelectorAll('.anon-option-card input[type="checkbox"]').forEach(cb => {
        cb.checked = checked;
    });
}

function getAnonSettings() {
    const settings = {};
    document.querySelectorAll('.anon-option-card input[type="checkbox"]').forEach(cb => {
        settings[cb.value] = cb.checked;
    });
    return settings;
}

async function startAnonymization() {
    if (!anonState.selectedFile) {
        showToast('Выберите файл для обезличивания', 'warning');
        return;
    }

    const settings = getAnonSettings();
    const anySelected = Object.values(settings).some(v => v);
    if (!anySelected) {
        showToast('Выберите хотя бы один параметр обезличивания', 'warning');
        return;
    }

    // Show progress
    const progressSection = document.getElementById('progressSectionAnon');
    progressSection.classList.remove('hidden');
    document.getElementById('progressFillAnon').style.width = '0%';
    document.getElementById('progressPercentAnon').textContent = '0%';
    document.getElementById('progressStatusAnon').textContent = 'Загрузка файла...';
    document.getElementById('progressMessageAnon').textContent = '';
    document.getElementById('resultsSectionAnon').classList.add('hidden');
    document.getElementById('processBtnAnon').disabled = true;

    // Reset and show log container
    const logsContent = document.getElementById('logsContentAnon');
    if (logsContent) {
        const now = new Date().toLocaleTimeString('ru-RU');
        logsContent.innerHTML = `<div class="anon-log-entry"><span class="anon-log-time">[${now}]</span> Загрузка файла...</div>`;
    }

    const formData = new FormData();
    formData.append('file', anonState.selectedFile);
    formData.append('settings', JSON.stringify(settings));

    try {
        const response = await fetch(`${ANON_API}/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка загрузки');
        }

        const data = await response.json();
        anonState.currentTaskId = data.task_id;

        // Start polling
        pollAnonStatus();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
        document.getElementById('processBtnAnon').disabled = false;
        progressSection.classList.add('hidden');
    }
}

function pollAnonStatus() {
    if (anonState.pollInterval) clearInterval(anonState.pollInterval);
    let lastLogCount = 0;

    anonState.pollInterval = setInterval(async () => {
        if (!anonState.currentTaskId) {
            clearInterval(anonState.pollInterval);
            return;
        }

        try {
            const response = await fetch(`${ANON_API}/status/${anonState.currentTaskId}`);
            if (!response.ok) {
                clearInterval(anonState.pollInterval);
                showToast('Ошибка получения статуса', 'error');
                return;
            }

            const data = await response.json();

            // Update progress bar
            document.getElementById('progressFillAnon').style.width = `${data.progress}%`;
            document.getElementById('progressPercentAnon').textContent = `${data.progress}%`;
            document.getElementById('progressStatusAnon').textContent =
                data.status === 'done' ? 'Завершено!' : (data.message || 'Обработка...');

            // Update progress message (short status)
            if (data.logs && data.logs.length > 0) {
                const lastLog = data.logs[data.logs.length - 1];
                document.getElementById('progressMessageAnon').textContent = `[${lastLog.time}] ${lastLog.message}`;
            }

            // Render full log entries
            const logsContent = document.getElementById('logsContentAnon');
            if (logsContent && data.logs && data.logs.length > lastLogCount) {
                lastLogCount = data.logs.length;
                logsContent.innerHTML = data.logs.map(log =>
                    `<div class="anon-log-entry"><span class="anon-log-time">[${log.time}]</span> ${log.message}</div>`
                ).join('');
                logsContent.scrollTop = logsContent.scrollHeight;
            }

            if (data.status === 'done') {
                clearInterval(anonState.pollInterval);
                showAnonResults();
            } else if (data.status === 'error') {
                clearInterval(anonState.pollInterval);
                showToast('Ошибка обработки: ' + (data.message || ''), 'error');
                document.getElementById('processBtnAnon').disabled = false;
            }
        } catch (error) {
            console.error('Poll error:', error);
        }
    }, 300);
}

async function showAnonResults() {
    if (!anonState.currentTaskId) return;

    try {
        const response = await fetch(`${ANON_API}/preview/${anonState.currentTaskId}`);
        if (!response.ok) throw new Error('Ошибка загрузки результатов');

        const data = await response.json();

        // Keep progress/log section visible (like standalone DOC_anonymizer)
        const resultsSection = document.getElementById('resultsSectionAnon');
        resultsSection.classList.remove('hidden');

        // Stats
        document.getElementById('replacementsCountAnon').textContent = data.replacements_count || 0;

        const confidence = data.validation?.confidence || 0;
        document.getElementById('confidenceValueAnon').textContent = Math.round(confidence * 100) + '%';

        // Validation badge
        const badge = document.getElementById('validationBadgeAnon');
        const hasIssues = data.validation?.issues?.length > 0;
        const hasWarnings = data.validation?.warnings?.length > 0;

        if (hasIssues || !data.validation?.is_valid) {
            badge.className = 'anon-validation-badge invalid';
            badge.textContent = '❌ Проблемы';
        } else if (hasWarnings) {
            badge.className = 'anon-validation-badge warning';
            badge.textContent = '⚠️ С замечаниями';
        } else {
            badge.className = 'anon-validation-badge valid';
            badge.textContent = '✅ Успешно';
        }

        // Validation issues
        const issues = data.validation?.issues || [];
        const warnings = data.validation?.warnings || [];
        const allIssues = [...issues, ...warnings];

        const issuesSection = document.getElementById('validationIssuesAnon');
        const issuesList = document.getElementById('issuesListAnon');

        if (allIssues.length > 0) {
            issuesSection.style.display = 'block';
            issuesList.innerHTML = allIssues.map(i => `<li>• ${escapeHtml(i)}</li>`).join('');
        } else {
            issuesSection.style.display = 'none';
        }

        // Show PDF button for markdown outputs
        const pdfBtn = document.getElementById('downloadPdfBtnAnon');
        if (data.file_type === 'pdf') {
            pdfBtn.style.display = 'inline-flex';
        } else {
            pdfBtn.style.display = 'none';
        }

        document.getElementById('processBtnAnon').disabled = false;

    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
        document.getElementById('processBtnAnon').disabled = false;
    }
}

async function anonDownload(type) {
    if (!anonState.currentTaskId) return;

    const endpoint = type === 'pdf' ? 'download-pdf' : 'download';
    try {
        const response = await fetch(`${ANON_API}/${endpoint}/${anonState.currentTaskId}`);
        if (!response.ok) throw new Error('Ошибка скачивания');

        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'anonymized_document';

        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) {
                filename = decodeURIComponent(utf8Match[1]);
            } else {
                const match = contentDisposition.match(/filename="?([^";\n]+)"?/i);
                if (match) filename = match[1];
            }
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        showToast('Файл скачан!', 'success');
    } catch (error) {
        showToast('Ошибка скачивания: ' + error.message, 'error');
    }
}

function anonView() {
    if (!anonState.currentTaskId) return;
    window.open(`${ANON_API}/view/${anonState.currentTaskId}`, '_blank');
}

async function anonPreview() {
    if (!anonState.currentTaskId) return;

    try {
        const response = await fetch(`${ANON_API}/preview/${anonState.currentTaskId}`);
        if (!response.ok) throw new Error('Ошибка загрузки');

        const data = await response.json();

        document.getElementById('originalPreviewAnon').textContent = data.original || '(пусто)';
        document.getElementById('anonymizedPreviewAnon').textContent = data.anonymized || '(пусто)';

        document.getElementById('previewModalAnon').classList.add('show');
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    }
}

async function anonMapping() {
    if (!anonState.currentTaskId) return;

    try {
        const response = await fetch(`${ANON_API}/mapping/${anonState.currentTaskId}`);
        if (!response.ok) throw new Error('Ошибка загрузки');

        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mapping_${anonState.currentTaskId.substring(0, 8)}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        showToast('Журнал замен скачан', 'success');
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    }
}

async function checkAnonMLStatus() {
    try {
        const response = await fetch(`${ANON_API}/ml-status`);
        if (!response.ok) return;

        const data = await response.json();

        const gptDot = document.getElementById('gptStatusAnon');
        const visionDot = document.getElementById('visionStatusAnon');

        if (gptDot) {
            gptDot.classList.toggle('active', !!data.gpt);
            gptDot.title = data.gpt ? 'GPT: подключено' : 'GPT: недоступен';
        }
        if (visionDot) {
            visionDot.classList.toggle('active', !!data.vision);
            visionDot.title = data.vision ? 'Vision: подключено' : 'Vision: недоступен';
        }
    } catch (error) {
        console.error('Anonymizer ML status error:', error);
    }
}

// ===================== АНАЛИЗ ДОКУМЕНТА (DOC ANALYSIS) =====================

const DA_API = '/api/v1/docanalysis';

let daState = {
    taskId: null,
    fileName: null,
    totalTokens: 0
};

// Initialize DA on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    setupDAListeners();
});

function setupDAListeners() {
    // Upload zone now handled by unified tools upload (setupToolsUploadZone)

    // Enter key handlers
    const askInput = document.getElementById('daAskInput');
    if (askInput) askInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') daAsk(); });

    // Cost rate handler
    const costInput = document.getElementById('daCostRate');
    if (costInput) {
        costInput.addEventListener('input', daUpdateCost);
        costInput.addEventListener('change', daUpdateCost);
    }

    // Navigation Buttons handled by sidebar
}

// handleDAUpload is now handled by unified tools upload (handleToolsUpload)

function daUpdateCost() {
    if (!daState.totalTokens) return;

    const rateInput = document.getElementById('daCostRate');
    const rate = parseFloat(rateInput.value) || 0;

    // Cost = (tokens / 1000) * rate
    const cost = (daState.totalTokens / 1000) * rate;

    // Format: "12.34 руб"
    document.getElementById('daEstCost').textContent = `${cost.toFixed(2)} руб`;
}

function daRemoveDocument() {
    if (daState.taskId) {
        fetch(`${DA_API}/${daState.taskId}`, { method: 'DELETE' }).catch(() => { });
    }
    daState.taskId = null;
    daState.fileName = null;
    daState.totalTokens = 0;
    daResetUI();
    document.getElementById('uploadZoneDA').style.display = '';
    document.getElementById('fileInputDA').value = '';
}

function daResetUI() {
    // Reset tool results (file info/stats managed by toolsRemoveFile)
    document.getElementById('daAskResult')?.classList.add('hidden');
    document.getElementById('daSummaryResult')?.classList.add('hidden');
    document.getElementById('daTableResult')?.classList.add('hidden');
    document.getElementById('daOcrResult')?.classList.add('hidden');
    document.getElementById('daEditResult')?.classList.add('hidden');
    document.getElementById('daEditDownloadActions')?.classList.add('hidden');
    document.getElementById('daTranslateResult')?.classList.add('hidden');
    document.getElementById('daTranslateDownloadActions')?.classList.add('hidden');
    document.getElementById('daStructureResult')?.classList.add('hidden');
    document.getElementById('daStructureDownloadActions')?.classList.add('hidden');

    // Reset buttons
    document.getElementById('daDownloadProtocolBtn')?.classList.add('hidden');
    document.getElementById('daDownloadTableBtn')?.classList.add('hidden');
    document.getElementById('daDownloadOcrBtn')?.classList.add('hidden');
    document.getElementById('daDownloadOcrPdfBtn')?.classList.add('hidden');
}

// Helper to get specific prompt
function _daGetPrompt(id) {
    return (document.getElementById(id)?.value || '').trim();
}

// ---- Ask ----
async function daAsk() {
    if (!daState.taskId) { showToast('Сначала загрузите документ', 'warning'); return; }
    const question = document.getElementById('daAskInput').value.trim();
    if (!question) { showToast('Введите вопрос', 'warning'); return; }

    const result = document.getElementById('daAskResult');
    const btn = document.getElementById('daAskBtn');
    result.innerHTML = '<div class="da-loading">🧠 AI думает...</div>';
    result.classList.remove('hidden');
    btn.disabled = true;

    try {
        const resp = await fetch(`${DA_API}/ask/${daState.taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, custom_prompt: _daGetPrompt('daAskPrompt') }),
        });
        if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Ошибка');
        const data = await resp.json();
        result.innerHTML = `<div class="da-answer">${_daFormatMarkdown(data.answer)}</div>
            <div class="da-meta">Использовано: ${data.tokens_used?.toLocaleString('ru-RU') || '?'} токенов</div>`;
    } catch (error) {
        result.innerHTML = `<div class="da-error">❌ ${escapeHtml(error.message)}</div>`;
    } finally {
        btn.disabled = false;
    }
}

// ---- Summarize ----
async function daSummarize() {
    if (!daState.taskId) { showToast('Сначала загрузите документ', 'warning'); return; }

    const result = document.getElementById('daSummaryResult');
    const btn = document.getElementById('daSummarizeBtn');
    const dlBtn = document.getElementById('daDownloadProtocolBtn');

    result.innerHTML = '<div class="da-loading">📋 Создаётся протокол...</div>';
    result.classList.remove('hidden');
    btn.disabled = true;
    dlBtn.classList.add('hidden');

    try {
        const resp = await fetch(`${DA_API}/summarize/${daState.taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ custom_prompt: _daGetPrompt('daSummarizePrompt') }),
        });
        if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Ошибка');
        const data = await resp.json();
        result.innerHTML = `<div class="da-answer">${_daFormatMarkdown(data.summary)}</div>
            <div class="da-meta">Использовано: ${data.tokens_used?.toLocaleString('ru-RU') || '?'} токенов</div>`;

        // Show download button
        dlBtn.classList.remove('hidden');

    } catch (error) {
        result.innerHTML = `<div class="da-error">❌ ${escapeHtml(error.message)}</div>`;
    } finally {
        btn.disabled = false;
    }
}

async function daDownloadProtocol() {
    if (!daState.taskId) return;
    try {
        const resp = await fetch(`${DA_API}/download/${daState.taskId}/protocol`);
        if (!resp.ok) throw new Error('Ошибка скачивания');
        const blob = await resp.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Extract filename
        const contentDisposition = resp.headers.get('Content-Disposition');
        let filename = 'Protocol.docx';
        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) filename = decodeURIComponent(utf8Match[1]);
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast('Протокол скачан', 'success');
    } catch (e) {
        showToast('Ошибка скачивания: ' + e.message, 'error');
    }
}

// ---- Generate Table ----
async function daGenerateTable() {
    if (!daState.taskId) { showToast('Сначала загрузите документ', 'warning'); return; }

    const result = document.getElementById('daTableResult');
    const btn = document.getElementById('daTableBtn');
    const dlBtn = document.getElementById('daDownloadTableBtn');

    result.innerHTML = '<div class="da-loading">📊 Генерация таблицы...</div>';
    result.classList.remove('hidden');
    btn.disabled = true;
    dlBtn.classList.add('hidden');

    try {
        const resp = await fetch(`${DA_API}/table/${daState.taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ custom_prompt: _daGetPrompt('daTablePrompt') }),
        });
        if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Ошибка');
        const data = await resp.json();

        let html = '';

        if (data.tables && data.tables.length > 0) {
            for (const tbl of data.tables) {
                html += `<div class="da-table-block">`;
                if (tbl.title) html += `<h5 class="da-table-title">${escapeHtml(tbl.title)}</h5>`;

                html += `<div class="da-table-scroll"><table class="da-gen-table">`;
                // Headers
                if (tbl.headers && tbl.headers.length > 0) {
                    html += '<thead><tr>';
                    for (const h of tbl.headers) {
                        html += `<th>${escapeHtml(h)}</th>`;
                    }
                    html += '</tr></thead>';
                }

                // Rows
                if (tbl.rows && tbl.rows.length > 0) {
                    html += '<tbody>';
                    for (const row of tbl.rows) {
                        html += '<tr>';
                        for (const cell of row) {
                            html += `<td>${escapeHtml(String(cell))}</td>`;
                        }
                        html += '</tr>';
                    }
                    html += '</tbody>';
                }
                html += '</table></div></div>';
            }
            html += `<div class="da-meta">Использовано: ${data.tokens_used?.toLocaleString('ru-RU') || '?'} токенов</div>`;

            // Show download button
            dlBtn.classList.remove('hidden');

        } else if (data.markdown) {
            html = `<div class="da-answer">${_daFormatMarkdown(data.markdown)}</div>
                <div class="da-meta">Использовано: ${data.tokens_used?.toLocaleString('ru-RU') || '?'} токенов</div>`;
        } else {
            html = '<div class="da-empty">Не удалось создать таблицу из документа</div>';
        }

        result.innerHTML = html;
    } catch (error) {
        result.innerHTML = `<div class="da-error">❌ ${escapeHtml(error.message)}</div>`;
    } finally {
        btn.disabled = false;
    }
}

async function daDownloadTable() {
    if (!daState.taskId) return;
    try {
        const resp = await fetch(`${DA_API}/download/${daState.taskId}/table`);
        if (!resp.ok) throw new Error('Ошибка скачивания');
        const blob = await resp.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        const contentDisposition = resp.headers.get('Content-Disposition');
        let filename = 'Table.xlsx';
        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) filename = decodeURIComponent(utf8Match[1]);
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast('Таблица скачана', 'success');
    } catch (e) {
        showToast('Ошибка скачивания: ' + e.message, 'error');
    }
}

// ---- OCR ----
async function daOCR() {
    if (!daState.taskId) { showToast('Сначала загрузите документ (PDF или картинку)', 'warning'); return; }

    const result = document.getElementById('daOcrResult');
    const btn = document.getElementById('daOcrBtn');
    const dlBtn = document.getElementById('daDownloadOcrBtn');
    const dlPdfBtn = document.getElementById('daDownloadOcrPdfBtn');

    result.innerHTML = '<div class="da-loading">🔍 Идёт распознавание (это может занять время)...</div>';
    result.classList.remove('hidden');
    btn.disabled = true;
    dlBtn.classList.add('hidden');
    if (dlPdfBtn) dlPdfBtn.classList.add('hidden');

    try {
        const resp = await fetch(`${DA_API}/ocr/${daState.taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Ошибка OCR');
        const data = await resp.json();

        result.innerHTML = `<div class="da-answer">
            <div class="alert alert-success">✅ Распознавание завершено</div>
            <div class="da-preview" style="max-height: 200px; overflow: auto; opacity: 0.8; font-size: 0.9em;">
                ${_daFormatMarkdown(data.preview)}
            </div>
            <div class="da-meta" style="text-align: right; margin-top: 10px; font-size: 0.85em; color: #666;">
                Обработано страниц: <b>${data.pages_count || 1}</b> • 
                Токенов: <b>${data.tokens_used || 0}</b> • 
                Время: <b>${data.processing_time || 0} сек</b>
            </div>
        </div>`;

        // Show download buttons
        dlBtn.classList.remove('hidden');
        if (dlPdfBtn) dlPdfBtn.classList.remove('hidden');

    } catch (error) {
        result.innerHTML = `<div class="da-error">❌ ${escapeHtml(error.message)}</div>`;
    } finally {
        btn.disabled = false;
    }
}

async function daDownloadOCR() {
    if (!daState.taskId) return;
    try {
        const resp = await fetch(`${DA_API}/download/${daState.taskId}/ocr_docx`);
        if (!resp.ok) throw new Error('Ошибка скачивания');
        const blob = await resp.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        const contentDisposition = resp.headers.get('Content-Disposition');
        let filename = 'OCR_Result.docx';
        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) filename = decodeURIComponent(utf8Match[1]);
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast('DOCX скачан', 'success');
    } catch (e) {
        showToast('Ошибка скачивания: ' + e.message, 'error');
    }
}

async function daDownloadOCRPDF() {
    if (!daState.taskId) return;
    try {
        const resp = await fetch(`${DA_API}/download/${daState.taskId}/ocr_pdf`);
        if (!resp.ok) throw new Error('Ошибка скачивания');
        const blob = await resp.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        const contentDisposition = resp.headers.get('Content-Disposition');
        let filename = 'OCR_Result.pdf';
        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) filename = decodeURIComponent(utf8Match[1]);
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast('PDF скачан', 'success');
    } catch (e) {
        showToast('Ошибка скачивания: ' + e.message, 'error');
    }
}


// ---- Structure / Mind Map ----
async function daGenerateStructure() {
    if (!daState.taskId) { showToast('Сначала загрузите документ', 'warning'); return; }

    const mode = document.getElementById('daStructureMode').value;
    const resultBox = document.getElementById('daStructureResult');
    const container = document.getElementById('daMermaidContainer');
    const btn = document.getElementById('daStructureBtn');
    const downloadActions = document.getElementById('daStructureDownloadActions');

    resultBox.classList.remove('hidden');
    container.innerHTML = '<div class="da-loading">🧠 AI строит структуру...</div>';
    downloadActions.classList.add('hidden');
    btn.disabled = true;

    try {
        const resp = await fetch(`${DA_API}/structure/${daState.taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode: mode,
                custom_prompt: _daGetPrompt('daStructurePrompt')
            }),
        });

        if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Ошибка генерации');
        const data = await resp.json();

        // Render Mermaid
        container.innerHTML = ''; // clear loading
        const graphDefinition = data.mermaid_code;

        // Create a unique ID for the graph
        const id = 'mermaid-graph-' + Date.now();

        // Use mermaid API to render
        try {
            const { svg } = await mermaid.render(id, graphDefinition);
            container.innerHTML = svg;
            downloadActions.classList.remove('hidden');
            // Center content
            container.style.textAlign = 'center';
            container.querySelector('svg').style.maxWidth = '100%';
        } catch (renderError) {
            console.error(renderError);
            container.innerHTML = `<div class="da-error">Ошибка отрисовки Mermaid: ${renderError.message}.<br><pre>${escapeHtml(graphDefinition)}</pre></div>`;
        }

    } catch (error) {
        container.innerHTML = `<div class="da-error">❌ ${escapeHtml(error.message)}</div>`;
    } finally {
        btn.disabled = false;
    }
}

async function daDownloadMermaidSvg() {
    const container = document.getElementById('daMermaidContainer');
    const svgElement = container.querySelector('svg');
    if (!svgElement) return;

    const svgData = new XMLSerializer().serializeToString(svgElement);
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = "diagram.svg";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 100);
}

async function daDownloadMermaidPng() {
    const container = document.getElementById('daMermaidContainer');
    const svgElement = container.querySelector('svg');
    if (!svgElement) return;

    // 1. Get SVG string
    const serializer = new XMLSerializer();
    let svgString = serializer.serializeToString(svgElement);

    // 2. Canvas setup
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    // 3. Size calculation (High Res)
    const scale = 3;
    // Handle both viewBox and width/height attributes
    const viewBox = svgElement.viewBox.baseVal;
    let width = viewBox ? viewBox.width : parseFloat(svgElement.getAttribute('width'));
    let height = viewBox ? viewBox.height : parseFloat(svgElement.getAttribute('height'));

    // Fallback if dimensions missing
    if (!width || !height) {
        const bbox = svgElement.getBoundingClientRect();
        width = bbox.width;
        height = bbox.height;
    }

    canvas.width = width * scale;
    canvas.height = height * scale;

    // 4. Create Image
    const img = new Image();
    // Encode SVG string to base64 to avoid tainting canvas
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    img.onload = function () {
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        try {
            const pngUrl = canvas.toDataURL('image/png');
            const a = document.createElement('a');
            a.href = pngUrl;
            a.download = `Diagram_${new Date().getTime()}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (e) {
            console.error(e);
            showToast('Ошибка сохранения PNG (возможно диаграмма слишком большая)', 'error');
        } finally {
            URL.revokeObjectURL(url);
        }
    };
    img.src = url;
}

// ---- Check & Edit ----
async function daEditDocument() {
    if (!daState.taskId) { showToast('Сначала загрузите документ', 'warning'); return; }

    const mode = document.getElementById('daEditMode').value;
    const result = document.getElementById('daEditResult');
    const btn = document.getElementById('daEditBtn');
    const downloadActions = document.getElementById('daEditDownloadActions');

    result.innerHTML = '<div class="da-loading">✨ AI обрабатывает документ...</div>';
    result.classList.remove('hidden');
    downloadActions.classList.add('hidden');
    btn.disabled = true;

    try {
        const resp = await fetch(`${DA_API}/edit/${daState.taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode: mode,
                custom_prompt: _daGetPrompt('daEditPrompt')
            }),
        });

        if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Ошибка обработки');
        const data = await resp.json();

        let resultHtml = '';
        if (data.diff_view) {
            // If backend returned a diff, use it directly (it has inline styles)
            // Wrap in <pre> to preserve whitespace if needed, or div with whitespace-pre-wrap
            resultHtml = `<div style="white-space: pre-wrap; font-family: inherit;">${data.diff_view}</div>`;
        } else {
            resultHtml = _daFormatMarkdown(data.preview);
        }

        result.innerHTML = `<div class="da-answer">
            <div class="alert alert-success">✅ Обработка завершена</div>
            <div class="da-preview" style="max-height: 400px; overflow: auto; opacity: 1.0; font-size: 0.95em; background: #fff; padding: 10px; border: 1px solid #eee;">
                ${resultHtml}
            </div>
            <div class="da-meta" style="text-align: right; margin-top: 10px; font-size: 0.85em; color: #666;">
                Токенов: <b>${data.tokens_used || 0}</b> • 
                Время: <b>${data.processing_time || 0} сек</b>
            </div>
        </div>`;

        downloadActions.classList.remove('hidden');

    } catch (error) {
        result.innerHTML = `<div class="da-error">❌ ${escapeHtml(error.message)}</div>`;
    } finally {
        btn.disabled = false;
    }
}

async function daDownloadEditDocx() {
    if (!daState.taskId) return;
    try {
        const resp = await fetch(`${DA_API}/download/${daState.taskId}/edit_docx`);
        if (!resp.ok) throw new Error('Ошибка скачивания');
        const blob = await resp.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "Edited_Document.docx"; // Fallback

        const contentDisposition = resp.headers.get('Content-Disposition');
        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) a.download = decodeURIComponent(utf8Match[1]);
        }

        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast('DOCX скачан', 'success');
    } catch (e) {
        showToast('Ошибка скачивания: ' + e.message, 'error');
    }
}

async function daDownloadEditPdf() {
    if (!daState.taskId) return;
    try {
        const resp = await fetch(`${DA_API}/download/${daState.taskId}/edit_pdf`);
        if (!resp.ok) throw new Error('Ошибка скачивания');
        const blob = await resp.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "Edited_Document.pdf";

        const contentDisposition = resp.headers.get('Content-Disposition');
        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) a.download = decodeURIComponent(utf8Match[1]);
        }

        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showToast('PDF скачан', 'success');
    } catch (e) {
        showToast('Ошибка скачивания: ' + e.message, 'error');
    }
}




// ---- Translation ----
async function daTranslateDocument() {
    if (!daState.taskId) { showToast('Сначала загрузите документ', 'warning'); return; }

    const lang = document.getElementById('daTranslateLang').value;
    const result = document.getElementById('daTranslateResult');
    const btn = document.getElementById('daTranslateBtn');
    const downloadActions = document.getElementById('daTranslateDownloadActions');

    result.innerHTML = '<div class="da-loading">🌐 AI переводит документ...</div>';
    result.classList.remove('hidden');
    downloadActions.classList.add('hidden');
    btn.disabled = true;

    try {
        const resp = await fetch(`${DA_API}/translate/${daState.taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_language: lang,
                custom_prompt: _daGetPrompt('daTranslatePrompt')
            }),
        });

        if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Ошибка перевода');
        const data = await resp.json();

        result.innerHTML = `<div class="da-answer">
            <div class="alert alert-success">✅ Перевод завершен (${data.target_language})</div>
            <div class="da-preview" style="max-height: 400px; overflow: auto; opacity: 1.0; font-size: 0.95em; background: #fff; padding: 10px; border: 1px solid #eee;">
                ${_daFormatMarkdown(data.translated_text)}
            </div>
            <div class="da-meta" style="text-align: right; margin-top: 10px; font-size: 0.85em; color: #666;">
                Токенов: <b>${data.tokens_used || 0}</b> • 
                Время: <b>${data.processing_time || 0} сек</b>
            </div>
        </div>`;

        downloadActions.classList.remove('hidden');

    } catch (error) {
        result.innerHTML = `<div class="da-error">❌ ${escapeHtml(error.message)}</div>`;
    } finally {
        btn.disabled = false;
    }
}

async function daDownloadTranslateDocx() {
    if (!daState.taskId) return;
    try {
        const resp = await fetch(`${DA_API}/download/${daState.taskId}/translate_docx`);
        if (!resp.ok) throw new Error('Ошибка скачивания');
        const blob = await resp.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        let filename = "Translated.docx";
        const contentDisposition = resp.headers.get('Content-Disposition');
        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) filename = decodeURIComponent(utf8Match[1]);
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    } catch (e) {
        showToast('Ошибка скачивания: ' + e.message, 'error');
    }
}

async function daDownloadTranslatePdf() {
    if (!daState.taskId) return;
    try {
        const resp = await fetch(`${DA_API}/download/${daState.taskId}/translate_pdf`);
        if (!resp.ok) throw new Error('Ошибка скачивания');
        const blob = await resp.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        let filename = "Translated.pdf";
        const contentDisposition = resp.headers.get('Content-Disposition');
        if (contentDisposition) {
            const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
            if (utf8Match) filename = decodeURIComponent(utf8Match[1]);
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    } catch (e) {
        showToast('Ошибка скачивания: ' + e.message, 'error');
    }
}


function _daFormatMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Code
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h5>$1</h5>');
    html = html.replace(/^## (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^# (.+)$/gm, '<h3>$1</h3>');
    // Lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');
    // Horizontal rules
    html = html.replace(/^---+$/gm, '<hr>');
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    return html;
}
