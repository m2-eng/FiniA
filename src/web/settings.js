// Settings page logic

// Global variables (shared with category_automation.js)

// Auth-Check: User muss eingeloggt sein
requireAuth();

window.allCategories = [];
let currentSettings = [];  // Array of {category_id, type}
let importFormats = [];    // Array of {id, name, config}
let accountTypes = [];     // Array of {id, type, dateImport}
let planningCycles = [];   // Array of {id, cycle, periodValue, periodUnit, dateImport}

// Modal helper functions
function closeModal() {
  const modal = document.getElementById('formModal');
  if (modal) modal.style.display = 'none';
}

function showFormModal({ title, fields, onSubmit }) {
  const modal = document.getElementById('formModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const modalSaveBtn = document.getElementById('modalSaveBtn');
  const modalCancelBtn = document.getElementById('modalCancelBtn');
  const modalCloseBtn = document.getElementById('modalCloseBtn');

  if (!modal || !modalTitle || !modalBody || !modalSaveBtn) {
    console.error('Modal elements missing');
    return;
  }

  modalTitle.textContent = title;
  modalBody.innerHTML = '';

  fields.forEach((field) => {
    const group = document.createElement('div');
    group.className = 'form-group';

    const label = document.createElement('label');
    label.textContent = field.label;
    label.setAttribute('for', `modal-input-${field.id}`);

    let control;
    if (field.type === 'select') {
      control = document.createElement('select');
      control.className = 'input-sm';
      control.id = `modal-input-${field.id}`;
      if (field.options && Array.isArray(field.options)) {
        field.options.forEach(opt => {
          const optionEl = document.createElement('option');
          optionEl.value = opt.value;
          optionEl.textContent = opt.label;
          if (String(opt.value) === String(field.value || '')) {
            optionEl.selected = true;
          }
          control.appendChild(optionEl);
        });
      }
    } else if (field.type === 'textarea') {
      control = document.createElement('textarea');
      control.id = `modal-input-${field.id}`;
      control.className = 'input-sm';
      control.rows = field.rows || 8;
      if (field.value !== undefined && field.value !== null) {
        control.value = field.value;
      }
    } else {
      control = document.createElement('input');
      control.id = `modal-input-${field.id}`;
      control.type = field.type || 'text';
      control.className = 'input-sm';
      if (field.value !== undefined && field.value !== null) {
        control.value = field.value;
      }
    }

    if (field.required) {
      control.required = true;
    }

    group.appendChild(label);
    group.appendChild(control);
    modalBody.appendChild(group);
  });

  modalSaveBtn.onclick = async () => {
    const values = {};
    for (const field of fields) {
      const input = document.getElementById(`modal-input-${field.id}`);
      if (!input) continue;
      values[field.id] = input.value.trim();
      if (field.required && !values[field.id]) {
        input.focus();
        return;
      }
    }

    const shouldClose = await onSubmit(values);
    if (shouldClose !== false) {
      closeModal();
    }
  };

  if (modalCancelBtn) modalCancelBtn.onclick = closeModal;
  if (modalCloseBtn) modalCloseBtn.onclick = closeModal;

  modal.onclick = (event) => {
    if (event.target === modal) closeModal();
  };

  modal.style.display = 'block';
}

// API functions
async function fetchCategories() {
  const res = await authenticatedFetch(`${API_BASE}/categories/list`);
  const data = await res.json();
  return data.categories || [];
}

async function fetchSettings() {
  const res = await authenticatedFetch(`${API_BASE}/settings/shares-tx-categories`);
  const data = await res.json();
  return data.categories || [];
}

async function addSetting(categoryId, type) {
  const res = await authenticatedFetch(`${API_BASE}/settings/shares-tx-categories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category_id: categoryId, type: type })
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error: ${error}`);
  }
  return res.json();
}

async function deleteSetting(categoryId, type) {
  const res = await authenticatedFetch(`${API_BASE}/settings/shares-tx-categories`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category_id: categoryId, type: type })
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error: ${error}`);
  }
  return res.json();
}

// Import format API
async function fetchImportFormats() {
  const res = await authenticatedFetch(`${API_BASE}/settings/import-formats`);
  const data = await res.json();
  return data.formats || [];
}

async function addImportFormat(name, config) {
  const res = await authenticatedFetch(`${API_BASE}/settings/import-formats`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, config })
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error: ${error}`);
  }
  return res.json();
}

async function updateImportFormat(id, name, config) {
  const res = await authenticatedFetch(`${API_BASE}/settings/import-formats/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, config })
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error: ${error}`);
  }
  return res.json();
}

async function deleteImportFormat(id) {
  const res = await authenticatedFetch(`${API_BASE}/settings/import-formats/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error: ${error}`);
  }
  return res.json();
}

// UI functions
function showStatus(msg, isError = false) {
  const el = document.getElementById('settings-status');
  if (!el) return;
  el.textContent = msg;
  el.style.color = isError ? 'var(--color-danger)' : 'var(--color-text)';
}

function showImportFormatsStatus(msg, isError = false) {
  const el = document.getElementById('import-formats-status');
  if (!el) return;
  el.textContent = msg;
  el.style.color = isError ? 'var(--color-danger)' : 'var(--color-text)';
}

function getCategoryName(catId) {
  const cat = allCategories.find(c => c.id === catId);
  return cat ? cat.fullname : `ID: ${catId}`;
}

function getTypeLabel(type) {
  const labels = { buy: 'Kauf', sell: 'Verkauf', dividend: 'Dividende' };
  return labels[type] || type;
}

function renderTable() {
  const tbody = document.getElementById('categories-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (currentSettings.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">Keine Kategorien konfiguriert.</td></tr>';
    return;
  }

  currentSettings.forEach(setting => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="text-align: left;">${getCategoryName(setting.category_id)}</td>
      <td style="text-align: center;">${getTypeLabel(setting.type)}</td>
      <td style="text-align: center;">
        <button class="action-btn delete" data-id="${setting.category_id}" data-type="${setting.type}">Löschen</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('.action-btn.delete').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.getAttribute('data-id'), 10);
      const type = btn.getAttribute('data-type');
      removeCategory(id, type);
    });
  });
}

function renderImportFormatsTable() {
  const tbody = document.getElementById('import-formats-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (importFormats.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">Keine Formate konfiguriert.</td></tr>';
    return;
  }

  importFormats.forEach(format => {
    const tr = document.createElement('tr');
    const nameTd = document.createElement('td');
    const configTd = document.createElement('td');
    const actionsTd = document.createElement('td');

    nameTd.style.textAlign = 'left';
    nameTd.textContent = format.name;

    configTd.style.textAlign = 'left';
    configTd.style.whiteSpace = 'pre-wrap';
    configTd.style.fontFamily = 'ui-monospace, SFMono-Regular, Menlo, monospace';
    configTd.textContent = JSON.stringify(format.config, null, 2);

    actionsTd.style.textAlign = 'center';
    actionsTd.innerHTML = `
      <button class="action-btn" data-action="edit" data-id="${format.id}">Bearbeiten</button>
      <button class="action-btn delete" data-action="delete" data-id="${format.id}">Löschen</button>
    `;

    tr.appendChild(nameTd);
    tr.appendChild(configTd);
    tr.appendChild(actionsTd);
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('button[data-action="edit"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.getAttribute('data-id'), 10);
      const format = importFormats.find(f => f.id === id);
      if (format) showImportFormatDialog(format);
    });
  });

  tbody.querySelectorAll('button[data-action="delete"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.getAttribute('data-id'), 10);
      removeImportFormat(id);
    });
  });
}

function showImportFormatDialog(format = null) {
  const isEdit = !!format;
  const title = isEdit ? 'Import-Format bearbeiten' : 'Import-Format hinzufügen';
  const initialName = format ? format.name : '';
  const initialConfig = format ? JSON.stringify(format.config, null, 2) : '{\n  "encoding": "utf-8",\n  "delimiter": ";",\n  "decimal": ",",\n  "date_format": "%d.%m.%Y",\n  "columns": {}\n}';

  showFormModal({
    title,
    fields: [
      { id: 'name', label: 'Name', type: 'text', required: true, value: initialName },
      { id: 'config', label: 'Konfiguration (JSON)', type: 'textarea', required: true, value: initialConfig, rows: 10 }
    ],
    onSubmit: async (values) => {
      let configObj;
      try {
        configObj = JSON.parse(values.config);
      } catch (err) {
        showImportFormatsStatus('Ungültiges JSON in der Konfiguration.', true);
        return false;
      }

      try {
        if (isEdit) {
          const updated = await updateImportFormat(format.id, values.name, configObj);
          importFormats = importFormats.map(f => f.id === format.id ? updated : f);
          showImportFormatsStatus('Format aktualisiert.');
        } else {
          const created = await addImportFormat(values.name, configObj);
          importFormats.push(created);
          showImportFormatsStatus('Format hinzugefügt.');
        }
        renderImportFormatsTable();
        return true;
      } catch (err) {
        console.error('Import format save failed:', err);
        showImportFormatsStatus(`Fehler beim Speichern: ${err.message}`, true);
        return false;
      }
    }
  });
}

async function removeImportFormat(id) {
  const format = importFormats.find(f => f.id === id);
  if (!format) return;
  if (!confirm(`Format "${format.name}" wirklich löschen?`)) return;

  try {
    await deleteImportFormat(id);
    importFormats = importFormats.filter(f => f.id !== id);
    showImportFormatsStatus('Format gelöscht.');
    renderImportFormatsTable();
  } catch (err) {
    console.error('Delete failed:', err);
    showImportFormatsStatus(`Fehler beim Löschen: ${err.message}`, true);
  }
}

async function initializeImportFormats() {
  console.log('🚀 Starte initializeImportFormats()...');
  try {
    importFormats = await fetchImportFormats();
    renderImportFormatsTable();

    const addBtn = document.getElementById('add-import-format-btn');
    if (addBtn) {
      console.log('✅ Add-Button gefunden, registriere Click-Handler');
      addBtn.addEventListener('click', () => showImportFormatDialog());
    } else {
      console.warn('⚠️ Add-Button nicht gefunden');
    }

    const reloadBtn = document.getElementById('reload-import-formats-btn');
    if (reloadBtn) {
      console.log('✅ Reload-Button gefunden, registriere Click-Handler');
      reloadBtn.addEventListener('click', async () => {
        importFormats = await fetchImportFormats();
        renderImportFormatsTable();
        showImportFormatsStatus('Formate neu geladen.');
      });
    } else {
      console.warn('⚠️ Reload-Button nicht gefunden');
    }

    const fileInput = document.getElementById('import-format-file-input');
    if (fileInput) {
      console.log('✅ Dateielement gefunden, registriere Change-Handler');
      console.log('Dateielement Details:', {
        id: fileInput.id,
        type: fileInput.type,
        accept: fileInput.accept,
        display: window.getComputedStyle(fileInput).display
      });
      fileInput.addEventListener('change', (e) => {
        console.log('📁 Change-Event ausgelöst für Dateielement');
        handleImportFormatFileUpload(e);
      });
      console.log('✅ Change-Handler registriert');
    } else {
      console.error('❌ Dateielement mit ID "import-format-file-input" nicht gefunden!');
    }
  } catch (err) {
    console.error('Import formats init failed:', err);
    showImportFormatsStatus(`Fehler beim Laden: ${err.message}`, true);
  }
}

function parseYAML(yamlContent) {
  /**
   * Generic YAML parser for nested structures.
   * Supports: root: { name: { key: value, nested: { key: value }, list: [...] } }
   * Also supports: root: [item1, item2, ...]
   */
  const result = {};
  let currentRoot = null;
  let stack = []; // Stack to track nesting level: [{level, key, obj}, ...]

  const lines = yamlContent.split('\n');

  for (let lineNum = 0; lineNum < lines.length; lineNum++) {
    const line = lines[lineNum];
    
    // Skip empty lines and comments
    if (!line.trim() || line.trim().startsWith('#')) continue;

    const leadingSpaces = line.match(/^(\s*)/)[1].length;
    const trimmed = line.trim();

    // Root element (0 spaces, ends with :)
    if (leadingSpaces === 0 && trimmed.endsWith(':')) {
      currentRoot = trimmed.slice(0, -1);
      
      // Check if next non-empty line is a list item
      let isArray = false;
      for (let j = lineNum + 1; j < lines.length; j++) {
        const nextLine = lines[j];
        if (!nextLine.trim() || nextLine.trim().startsWith('#')) continue;
        if (nextLine.trim().startsWith('-')) {
          isArray = true;
        }
        break;
      }
      
      if (isArray) {
        result[currentRoot] = [];
        stack = [{level: 0, key: currentRoot, obj: result[currentRoot]}];
      } else {
        result[currentRoot] = {};
        stack = [{level: 0, key: currentRoot, obj: result[currentRoot]}];
      }
      continue;
    }

    if (!currentRoot) continue;

    // Handle nested structures and key-value pairs
    if (trimmed.endsWith(':')) {
      // Key with nested structure (object or array)
      const key = trimmed.slice(0, -1);
      
      // Pop stack to current level
      while (stack.length > 1 && stack[stack.length - 1].level >= leadingSpaces) {
        stack.pop();
      }

      const parentObj = stack[stack.length - 1].obj;
      
      // Check if next non-empty line is a list item (starts with -)
      let isArray = false;
      for (let j = lineNum + 1; j < lines.length; j++) {
        const nextLine = lines[j];
        if (!nextLine.trim() || nextLine.trim().startsWith('#')) continue;
        const nextSpaces = nextLine.match(/^(\s*)/)[1].length;
        if (nextSpaces <= leadingSpaces) break;
        if (nextLine.trim().startsWith('-')) {
          isArray = true;
        }
        break;
      }

      if (isArray) {
        parentObj[key] = [];
        stack.push({level: leadingSpaces, key, obj: parentObj[key]});
      } else {
        parentObj[key] = {};
        stack.push({level: leadingSpaces, key, obj: parentObj[key]});
      }
    } else if (trimmed.startsWith('-')) {
      // List item
      const parent = stack[stack.length - 1];
      if (Array.isArray(parent.obj)) {
        let value = trimmed.slice(1).trim();
        // Parse the value
        value = parseYAMLValue(value);
        parent.obj.push(value);
      }
    } else if (trimmed.includes(':')) {
      // Key-value pair
      const colonIdx = trimmed.indexOf(':');
      const key = trimmed.substring(0, colonIdx).trim();
      let value = trimmed.substring(colonIdx + 1).trim();

      // Pop stack to current level
      while (stack.length > 1 && stack[stack.length - 1].level >= leadingSpaces) {
        stack.pop();
      }

      value = parseYAMLValue(value);
      const parent = stack[stack.length - 1].obj;
      if (Array.isArray(parent)) {
        parent.push({[key]: value});
      } else {
        parent[key] = value;
      }
    }
  }

  return result;
}

function parseYAMLValue(value) {
  if (!value) return null;
  
  if (value === 'null') return null;
  if (value === 'true') return true;
  if (value === 'false') return false;
  if (!isNaN(value) && value !== '') return Number(value);
  
  // Remove quotes
  if ((value.startsWith("'") && value.endsWith("'")) ||
      (value.startsWith('"') && value.endsWith('"'))) {
    return value.slice(1, -1);
  }
  
  return value;
}

async function handleImportFormatFileUpload(event) {
  console.log('🎯 handleImportFormatFileUpload() wurde aufgerufen!');
  console.log('Event-Details:', {
    type: event.type,
    target: event.target,
    files: event.target?.files?.length
  });
  
  const file = event.target.files[0];
  if (!file) {
    console.warn('⚠️ Keine Datei ausgewählt');
    return;
  }

  console.log('📄 Datei ausgewählt:', {
    name: file.name,
    size: file.size,
    type: file.type
  });

  try {
    const content = await file.text();
    console.log('📥 Dateiinhalt gelesen, starte YAML-Parsing...', {fileSize: content.length});
    
    let formats;

    // Try to parse as YAML
    try {
      formats = parseYAML(content);
      console.log('✅ YAML-Parsing erfolgreich. Formate gefunden:', Object.keys(formats));
    } catch (err) {
      console.error('❌ YAML-Parsing-Fehler:', err);
      showImportFormatsStatus(`Fehler beim Parsen der YAML-Datei: ${err.message}`, true);
      event.target.value = '';
      return;
    }

    if (!formats || Object.keys(formats).length === 0) {
      console.warn('⚠️ Keine Formate in YAML gefunden');
      showImportFormatsStatus('Keine Formate in der Datei gefunden.', true);
      event.target.value = '';
      return;
    }

    // Batch upload all formats
    showImportFormatsStatus(`Lade ${Object.keys(formats).length} Format(e) hoch...`);
    let successCount = 0;
    let errorCount = 0;

    for (const [name, config] of Object.entries(formats)) {
      try {
        console.log(`📤 Uploade Format: ${name}`, config);
        
        // Check if format already exists
        const exists = importFormats.some(f => f.name === name);
        if (exists) {
          // Update existing
          const existing = importFormats.find(f => f.name === name);
          console.log(`🔄 Aktualisiere existierendes Format: ${name} (ID: ${existing.id})`);
          await updateImportFormat(existing.id, name, config);
          successCount++;
        } else {
          // Create new
          console.log(`✨ Erstelle neues Format: ${name}`);
          await addImportFormat(name, config);
          successCount++;
        }
      } catch (err) {
        console.error(`❌ Fehler beim Upload von Format '${name}':`, err);
        errorCount++;
      }
    }

    // Reload formats
    console.log('🔄 Laden Formate neu...');
    importFormats = await fetchImportFormats();
    renderImportFormatsTable();

    if (errorCount === 0) {
      console.log(`✅ Erfolgreich: ${successCount} Format(e) importiert`);
      showImportFormatsStatus(`✅ ${successCount} Format(e) erfolgreich importiert.`);
    } else {
      console.warn(`⚠️ Teilweise erfolgreich: ${successCount} OK, ${errorCount} Fehler`);
      showImportFormatsStatus(
        `⚠️ ${successCount} Format(e) importiert, ${errorCount} Fehler.`,
        true
      );
    }

    event.target.value = '';
  } catch (err) {
    console.error('❌ File upload error:', err);
    showImportFormatsStatus(`Fehler beim Hochladen der Datei: ${err.message}`, true);
    event.target.value = '';
  }
}

async function removeCategory(catId, type) {
  if (!confirm(`Kategorie "${getCategoryName(catId)}" (${getTypeLabel(type)}) wirklich entfernen?`)) return;
  
  try {
    await deleteSetting(catId, type);
    currentSettings = currentSettings.filter(s => !(s.category_id === catId && s.type === type));
    showStatus('Kategorie entfernt.');
    renderTable();
  } catch (err) {
    console.error('Remove failed:', err);
    showStatus(`Fehler beim Entfernen: ${err.message}`, true);
  }
}

function showAddCategoryDialog() {
  const usedCombinations = currentSettings.map(s => `${s.category_id}_${s.type}`);
  const availableCategories = allCategories.filter(cat => {
    return ['buy', 'sell', 'dividend'].some(type => 
      !usedCombinations.includes(`${cat.id}_${type}`)
    );
  });

  if (availableCategories.length === 0) {
    alert('Alle Kategorien sind bereits für alle Typen zugewiesen.');
    return;
  }

  const categoryOptions = availableCategories.map(cat => ({
    value: cat.id,
    label: cat.fullname
  }));

  const typeOptions = [
    { value: 'buy', label: 'Kauf' },
    { value: 'sell', label: 'Verkauf' },
    { value: 'dividend', label: 'Dividende' }
  ];

  showFormModal({
    title: 'Kategorie hinzufügen',
    fields: [
      { id: 'category', label: 'Kategorie', type: 'select', required: true, options: categoryOptions },
      { id: 'type', label: 'Typ', type: 'select', required: true, options: typeOptions }
    ],
    onSubmit: async (values) => {
      const catId = parseInt(values.category, 10);
      const type = values.type;

      if (currentSettings.some(s => s.category_id === catId && s.type === type)) {
        showStatus('Diese Kombination existiert bereits.', true);
        return false;
      }

      try {
        await addSetting(catId, type);
        currentSettings.push({ category_id: catId, type: type });
        showStatus('Kategorie hinzugefügt.');
        renderTable();
        return true;
      } catch (err) {
        console.error('Add failed:', err);
        showStatus(`Fehler beim Hinzufügen: ${err.message}`, true);
        return false;
      }
    }
  });
}

// Init
async function initSettingsPage() {
  loadTopNav('settings');

  try {
    [allCategories, currentSettings] = await Promise.all([
      fetchCategories(),
      fetchSettings()
    ]);

    renderTable();

    const addBtn = document.getElementById('add-category-btn');
    if (addBtn) {
      addBtn.addEventListener('click', showAddCategoryDialog);
    }

  } catch (error) {
    console.error('Settings init failed', error);
    showStatus(`Fehler beim Laden: ${error.message}`, true);
  }
}

// ========================================
// Account Types Management
// ========================================

async function fetchAccountTypes() {
  console.log('📥 Fetching account types...');
  try {
    const response = await authenticatedFetch('/api/settings/account-types');
    const data = await response.json();
    console.log('✅ Received account types:', data);
    accountTypes = data.account_types || [];
    return accountTypes;
  } catch (error) {
    console.error('❌ Error fetching account types:', error);
    showAccountTypesStatus(`Fehler beim Laden: ${error.message}`, true);
    return [];
  }
}

function renderAccountTypesTable() {
  const tbody = document.getElementById('account-types-tbody');
  if (!tbody) {
    console.error('❌ account-types-tbody not found');
    return;
  }

  if (accountTypes.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">Keine Kontotypen vorhanden</td></tr>';
    return;
  }

  tbody.innerHTML = accountTypes.map(at => `
    <tr data-type-id="${at.id}">
      <td>${at.id}</td>
      <td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(at.type)}</td>
      <td style="text-align: center;">
        <div style="display: inline-flex; gap: 4px; justify-content: center;">
          <button class="btn btn-sm" onclick="editAccountType(${at.id})">Bearbeiten</button>
          <button class="btn btn-sm btn-danger" onclick="deleteAccountType(${at.id}, '${escapeHtml(at.type)}')">Löschen</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function showAccountTypesStatus(message, isError = false) {
  const status = document.getElementById('account-types-status');
  if (!status) return;
  
  status.textContent = message;
  status.style.color = isError ? 'var(--color-red)' : 'var(--color-text)';
  
  setTimeout(() => {
    status.textContent = '';
  }, 5000);
}

// ========================================
// Planning Cycles Management
// ========================================

async function fetchPlanningCycles() {
  try {
    const response = await authenticatedFetch('/api/settings/planning-cycles');
    const data = await response.json();
    planningCycles = data.planning_cycles || [];
    return planningCycles;
  } catch (error) {
    console.error('❌ Error fetching planning cycles:', error);
    showPlanningCyclesStatus(`Fehler beim Laden: ${error.message}`, true);
    return [];
  }
}

function renderPlanningCyclesTable() {
  const tbody = document.getElementById('planning-cycles-tbody');
  if (!tbody) return;

  if (planningCycles.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">Keine Zyklen vorhanden</td></tr>';
    return;
  }

  // Map für lesbare Einheiten
  const unitLabels = {
    'd': 'Tag(e)',
    'm': 'Monat(e)',
    'y': 'Jahr(e)'
  };

  tbody.innerHTML = planningCycles.map(pc => {
    const unitLabel = unitLabels[pc.periodUnit] || pc.periodUnit;
    const valueDisplay = pc.periodValue === 0 ? '-' : `${pc.periodValue} ${unitLabel}`;
    
    return `
    <tr data-cycle-id="${pc.id}">
      <td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(pc.cycle)}</td>
      <td>${escapeHtml(valueDisplay)}</td>
      <td style="text-align: center;">
        <div style="display: inline-flex; gap: 4px; justify-content: center;">
          <button class="btn btn-sm" onclick="editPlanningCycle(${pc.id})">Bearbeiten</button>
          <button class="btn btn-sm btn-danger" onclick="deletePlanningCycle(${pc.id}, '${escapeHtml(pc.cycle)}')">Löschen</button>
        </div>
      </td>
    </tr>
    `;
  }).join('');
}

function showPlanningCyclesStatus(message, isError = false) {
  const status = document.getElementById('planning-cycles-status');
  if (!status) return;

  status.textContent = message;
  status.style.color = isError ? 'var(--color-red)' : 'var(--color-text)';

  setTimeout(() => {
    status.textContent = '';
  }, 5000);
}

async function addPlanningCycle(cycleName, periodValue, periodUnit) {
  const response = await authenticatedFetch('/api/settings/planning-cycles', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cycle: cycleName, periodValue, periodUnit })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

async function updatePlanningCycle(cycleId, cycleName, periodValue, periodUnit) {
  const response = await authenticatedFetch(`/api/settings/planning-cycles/${cycleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cycle: cycleName, periodValue, periodUnit })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

async function deletePlanningCycleAPI(cycleId) {
  const response = await authenticatedFetch(`/api/settings/planning-cycles/${cycleId}`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

function showAddPlanningCycleDialog() {
  showFormModal({
    title: 'Zyklus hinzufügen',
    fields: [
      { id: 'cycle', label: 'Zyklus-Name', type: 'text', required: true, value: '' },
      { id: 'periodValue', label: 'Periodenwert', type: 'number', required: true, value: '1' },
      { id: 'periodUnit', label: 'Einheit', type: 'select', required: true, value: 'm', options: [
        { value: 'd', label: 'Tag(e)' },
        { value: 'm', label: 'Monat(e)' },
        { value: 'y', label: 'Jahr(e)' }
      ]}
    ],
    onSubmit: async (values) => {
      const cycleName = values.cycle;
      const periodValue = parseFloat(values.periodValue);
      const periodUnit = values.periodUnit;

      if (planningCycles.some(pc => pc.cycle.toLowerCase() === cycleName.toLowerCase())) {
        showPlanningCyclesStatus('Dieser Zyklus existiert bereits.', true);
        return false;
      }

      try {
        const result = await addPlanningCycle(cycleName, periodValue, periodUnit);
        planningCycles.push({
          id: result.id,
          cycle: result.cycle,
          periodValue: result.periodValue,
          periodUnit: result.periodUnit,
          dateImport: new Date().toISOString()
        });
        showPlanningCyclesStatus('Zyklus hinzugefügt.');
        renderPlanningCyclesTable();
        return true;
      } catch (err) {
        console.error('Add failed:', err);
        showPlanningCyclesStatus(`Fehler beim Hinzufügen: ${err.message}`, true);
        return false;
      }
    }
  });
}

function editPlanningCycle(cycleId) {
  const cycle = planningCycles.find(pc => pc.id === cycleId);
  if (!cycle) {
    showPlanningCyclesStatus('Zyklus nicht gefunden.', true);
    return;
  }

  showFormModal({
    title: 'Zyklus bearbeiten',
    fields: [
      { id: 'cycle', label: 'Zyklus-Name', type: 'text', required: true, value: cycle.cycle },
      { id: 'periodValue', label: 'Periodenwert', type: 'number', required: true, value: String(cycle.periodValue) },
      { id: 'periodUnit', label: 'Einheit', type: 'select', required: true, value: cycle.periodUnit, options: [
        { value: 'd', label: 'Tag(e)' },
        { value: 'm', label: 'Monat(e)' },
        { value: 'y', label: 'Jahr(e)' }
      ]}
    ],
    onSubmit: async (values) => {
      const newName = values.cycle;
      const periodValue = parseFloat(values.periodValue);
      const periodUnit = values.periodUnit;

      const duplicate = planningCycles.find(pc => pc.id !== cycleId && pc.cycle.toLowerCase() === newName.toLowerCase());
      if (duplicate) {
        showPlanningCyclesStatus('Ein anderer Zyklus mit diesem Namen existiert bereits.', true);
        return false;
      }

      try {
        await updatePlanningCycle(cycleId, newName, periodValue, periodUnit);
        cycle.cycle = newName;
        cycle.periodValue = periodValue;
        cycle.periodUnit = periodUnit;
        showPlanningCyclesStatus('Zyklus aktualisiert.');
        renderPlanningCyclesTable();
        return true;
      } catch (err) {
        console.error('Update failed:', err);
        showPlanningCyclesStatus(`Fehler beim Aktualisieren: ${err.message}`, true);
        return false;
      }
    }
  });
}

async function deletePlanningCycle(cycleId, cycleName) {
  if (!confirm(`Möchten Sie den Zyklus "${cycleName}" wirklich löschen?`)) {
    return;
  }

  try {
    await deletePlanningCycleAPI(cycleId);
    planningCycles = planningCycles.filter(pc => pc.id !== cycleId);
    showPlanningCyclesStatus('Zyklus gelöscht.');
    renderPlanningCyclesTable();
  } catch (err) {
    console.error('Delete failed:', err);
    showPlanningCyclesStatus(`Fehler beim Löschen: ${err.message}`, true);
  }
}

async function handlePlanningCycleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) {
    return;
  }

  try {
    const content = await file.text();
    const parsed = parseYAML(content);

    if (!parsed || !parsed.planningCycle) {
      showPlanningCyclesStatus('YAML-Datei enthält keinen "planningCycle"-Abschnitt.', true);
      return;
    }

    const cycles = parsed.planningCycle;
    if (!Array.isArray(cycles)) {
      showPlanningCyclesStatus('YAML-Format ungültig. Erwartet: Liste von Zyklen.', true);
      return;
    }

    let created = 0;
    let skipped = 0;
    let errors = 0;

    for (const item of cycles) {
      const cycleName = item?.cycle;
      const periodValue = item?.periodValue;
      const periodUnit = item?.periodUnit;

      if (!cycleName || periodValue === undefined || !periodUnit) {
        errors++;
        continue;
      }

      const existing = planningCycles.find(pc => pc.cycle.toLowerCase() === String(cycleName).toLowerCase());
      if (existing) {
        skipped++;
        continue;
      }

      try {
        const result = await addPlanningCycle(cycleName, periodValue, periodUnit);
        planningCycles.push({
          id: result.id,
          cycle: result.cycle,
          periodValue: result.periodValue,
          periodUnit: result.periodUnit,
          dateImport: new Date().toISOString()
        });
        created++;
      } catch (err) {
        errors++;
        console.error('Import failed:', err);
      }
    }

    showPlanningCyclesStatus(
      `Import abgeschlossen: ${created} erstellt, ${skipped} übersprungen${errors > 0 ? `, ${errors} Fehler` : ''}`,
      errors > 0
    );

    renderPlanningCyclesTable();
    event.target.value = '';
  } catch (error) {
    console.error('YAML import failed:', error);
    showPlanningCyclesStatus(`Fehler beim Import: ${error.message}`, true);
    event.target.value = '';
  }
}

async function initializePlanningCycles() {
  try {
    await fetchPlanningCycles();
    renderPlanningCyclesTable();

    const addBtn = document.getElementById('add-planning-cycle-btn');
    const reloadBtn = document.getElementById('reload-planning-cycles-btn');
    const fileInput = document.getElementById('planning-cycle-file-input');

    if (addBtn) {
      addBtn.addEventListener('click', showAddPlanningCycleDialog);
    }

    if (reloadBtn) {
      reloadBtn.addEventListener('click', async () => {
        await fetchPlanningCycles();
        renderPlanningCyclesTable();
        showPlanningCyclesStatus('Zyklen neu geladen.');
      });
    }

    if (fileInput) {
      fileInput.addEventListener('change', handlePlanningCycleFileUpload);
    }
  } catch (error) {
    console.error('Planning cycles init failed:', error);
    showPlanningCyclesStatus(`Initialisierungsfehler: ${error.message}`, true);
  }
}

async function addAccountType(typeName) {
  console.log(`➕ Adding account type: ${typeName}`);
  const response = await authenticatedFetch('/api/settings/account-types', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: typeName })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

async function updateAccountType(typeId, typeName) {
  console.log(`✏️ Updating account type ${typeId}: ${typeName}`);
  const response = await authenticatedFetch(`/api/settings/account-types/${typeId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: typeName })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

async function deleteAccountTypeAPI(typeId) {
  console.log(`🗑️ Deleting account type ${typeId}`);
  const response = await authenticatedFetch(`/api/settings/account-types/${typeId}`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

function showAddAccountTypeDialog() {
  showFormModal({
    title: 'Kontotyp hinzufügen',
    fields: [
      { id: 'type', label: 'Typ-Name', type: 'text', required: true, value: '' }
    ],
    onSubmit: async (values) => {
      const typeName = values.type;

      if (accountTypes.some(at => at.type.toLowerCase() === typeName.toLowerCase())) {
        showAccountTypesStatus('Dieser Kontotyp existiert bereits.', true);
        return false;
      }

      try {
        const result = await addAccountType(typeName);
        accountTypes.push({ id: result.id, type: result.type, dateImport: new Date().toISOString() });
        showAccountTypesStatus('Kontotyp hinzugefügt.');
        renderAccountTypesTable();
        return true;
      } catch (err) {
        console.error('Add failed:', err);
        showAccountTypesStatus(`Fehler beim Hinzufügen: ${err.message}`, true);
        return false;
      }
    }
  });
}

function editAccountType(typeId) {
  const accountType = accountTypes.find(at => at.id === typeId);
  if (!accountType) {
    showAccountTypesStatus('Kontotyp nicht gefunden.', true);
    return;
  }

  showFormModal({
    title: 'Kontotyp bearbeiten',
    fields: [
      { id: 'type', label: 'Typ-Name', type: 'text', required: true, value: accountType.type }
    ],
    onSubmit: async (values) => {
      const newTypeName = values.type;

      const duplicate = accountTypes.find(at => at.id !== typeId && at.type.toLowerCase() === newTypeName.toLowerCase());
      if (duplicate) {
        showAccountTypesStatus('Ein anderer Kontotyp mit diesem Namen existiert bereits.', true);
        return false;
      }

      try {
        await updateAccountType(typeId, newTypeName);
        accountType.type = newTypeName;
        showAccountTypesStatus('Kontotyp aktualisiert.');
        renderAccountTypesTable();
        return true;
      } catch (err) {
        console.error('Update failed:', err);
        showAccountTypesStatus(`Fehler beim Aktualisieren: ${err.message}`, true);
        return false;
      }
    }
  });
}

async function deleteAccountType(typeId, typeName) {
  if (!confirm(`Möchten Sie den Kontotyp "${typeName}" wirklich löschen?\n\nHinweis: Dies schlägt fehl, wenn noch Konten mit diesem Typ existieren.`)) {
    return;
  }

  try {
    await deleteAccountTypeAPI(typeId);
    accountTypes = accountTypes.filter(at => at.id !== typeId);
    showAccountTypesStatus('Kontotyp gelöscht.');
    renderAccountTypesTable();
  } catch (err) {
    console.error('Delete failed:', err);
    showAccountTypesStatus(`Fehler beim Löschen: ${err.message}`, true);
  }
}

async function handleAccountTypeFileUpload(event) {
  console.log('🎯 handleAccountTypeFileUpload() wurde aufgerufen!');
  
  const file = event.target.files[0];
  if (!file) {
    console.warn('⚠️ Keine Datei ausgewählt');
    return;
  }

  console.log('📄 Datei ausgewählt:', {
    name: file.name,
    size: file.size,
    type: file.type
  });

  try {
    const content = await file.text();
    console.log('📥 Dateiinhalt gelesen, starte YAML-Parsing...', {fileSize: content.length});
    
    const parsed = parseYAML(content);
    console.log('✅ YAML erfolgreich geparst:', parsed);
    
    if (!parsed || !parsed.accountType) {
      showAccountTypesStatus('YAML-Datei enthält keinen "accountType"-Abschnitt.', true);
      return;
    }

    const accountTypeData = parsed.accountType;
    console.log('📊 Account Type Daten:', accountTypeData);
    
    if (!Array.isArray(accountTypeData)) {
      showAccountTypesStatus('YAML-Format ungültig. Erwartet: Array von Kontotypen.', true);
      event.target.value = '';
      return;
    }
    
    console.log(`📝 ${accountTypeData.length} Kontotypen gefunden`);
    
    let created = 0;
    let skipped = 0;
    let errors = 0;
    
    for (const typeName of accountTypeData) {
      const existing = accountTypes.find(at => at.type.toLowerCase() === typeName.toLowerCase());
      
      if (existing) {
        skipped++;
      } else {
        try {
          const result = await addAccountType(typeName);
          accountTypes.push({ 
            id: result.id, 
            type: result.type, 
            dateImport: new Date().toISOString() 
          });
          created++;
        } catch (err) {
          errors++;
          console.error(`Fehler bei ${typeName}:`, err);
        }
      }
    }
    
    showAccountTypesStatus(
      `Import abgeschlossen: ${created} erstellt, ${skipped} übersprungen${errors > 0 ? `, ${errors} Fehler` : ''}`,
      errors > 0
    );
    
    renderAccountTypesTable();
    
    // Reset file input
    event.target.value = '';
  } catch (error) {
    console.error('❌ Fehler beim Verarbeiten:', error);
    showAccountTypesStatus(`Fehler beim Import: ${error.message}`, true);
    event.target.value = '';
  }
}

async function initializeAccountTypes() {
  console.log('🚀 Initializing account types tab...');
  
  try {
    await fetchAccountTypes();
    renderAccountTypesTable();
    
    const addBtn = document.getElementById('add-account-type-btn');
    const reloadBtn = document.getElementById('reload-account-types-btn');
    const fileInput = document.getElementById('account-type-file-input');
    
    console.log('🔍 Button-Suche:', { addBtn: !!addBtn, reloadBtn: !!reloadBtn, fileInput: !!fileInput });
    
    if (addBtn) {
      addBtn.addEventListener('click', showAddAccountTypeDialog);
      console.log('✅ Add-Button Event-Listener hinzugefügt');
    } else {
      console.error('❌ add-account-type-btn nicht gefunden!');
    }
    
    if (reloadBtn) {
      reloadBtn.addEventListener('click', async () => {
        await fetchAccountTypes();
        renderAccountTypesTable();
        showAccountTypesStatus('Kontotypen neu geladen.');
      });
      console.log('✅ Reload-Button Event-Listener hinzugefügt');
    } else {
      console.error('❌ reload-account-types-btn nicht gefunden!');
    }
    
    if (fileInput) {
      fileInput.addEventListener('change', handleAccountTypeFileUpload);
      console.log('✅ File-Input Event-Listener hinzugefügt');
    } else {
      console.error('❌ account-type-file-input nicht gefunden!');
    }
    
    console.log('✅ Account Types Tab initialisiert');
  } catch (error) {
    console.error('❌ Fehler bei der Initialisierung:', error);
    showAccountTypesStatus(`Initialisierungsfehler: ${error.message}`, true);
  }
}

// ========================================

document.addEventListener('DOMContentLoaded', () => {
  initSettingsPage();
});
