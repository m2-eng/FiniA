// Settings page logic

// Global variables (shared with category_automation.js)

window.allCategories = [];
let currentSettings = [];  // Array of {category_id, type}
let importFormats = [];    // Array of {id, name, config}
let selectedImportFormatId = null;
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

function getImportFormatDefault(config) {
  if (!config) return '-';
  if (config.default) return String(config.default);
  const configDefault = config.config && config.config.default;
  if (configDefault) return String(configDefault);
  return '-';
}

function getImportFormatVersions(config) {
  if (!config) return [];
  const versionsFromVersions = Array.isArray(config.versions) ? config.versions : null;
  if (versionsFromVersions) return versionsFromVersions.map(v => String(v));

  const versionKeys = Object.keys(config).filter(key => key !== 'default' && key !== 'config');
  if (versionKeys.length > 0) return versionKeys;

  const nestedConfig = config.config || null;
  if (!nestedConfig) return [];
  return Object.keys(nestedConfig).filter(key => key !== 'default');
}

function renderImportFormatDetails(format) {
  const container = document.getElementById('import-format-details');
  if (!container) return;

  if (!format) {
    container.innerHTML = '<div class="details-meta">Wählen Sie ein Format, um Details anzuzeigen.</div>';
    return;
  }

  const defaultVersion = getImportFormatDefault(format.config);
  const versions = getImportFormatVersions(format.config);

  const versionOptions = versions
    .map(v => `<option value="${v}">${v}</option>`)
    .join('');

  const selectedVersion = versions.length > 0 ? versions[0] : '';
  const configObject = getImportFormatConfigObject(format.config, selectedVersion);

  container.innerHTML = `
    <div class="details-header" style="margin-bottom: 12px;">
      <div>
        <h2 style="margin: 0;">${format.name}</h2>
        <div class="details-meta">Standardversion: ${defaultVersion}</div>
      </div>
      <div class="details-actions">
        <button class="btn btn-danger" data-action="delete">Format löschen</button>
      </div>
    </div>

    <div class="details-section">
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
        <div style="flex: 1;">
          <label for="import-format-version-select">Version auswählen</label>
          <div style="display: flex; gap: 8px; align-items: center;">
            <select id="import-format-version-select" class="input-sm" style="flex: 1;">
              ${versionOptions || '<option value="">-</option>'}
            </select>
            <button class="btn btn-sm" id="rename-version-btn" title="Version umbenennen" style="padding: 6px 10px;">Umbenennen</button>
          </div>
        </div>
        <button class="btn btn-sm" id="add-version-btn" style="margin-top: 20px;">+ Version hinzufügen</button>
      </div>
    </div>

    <div class="details-section">
      <div class="details-meta" style="margin-bottom: 12px;">Konfiguration</div>
      <form id="import-format-config-form">
        <div id="import-format-config" class="import-format-config"></div>
        <div style="margin-top: 12px; display: flex; gap: 8px;">
          <button type="submit" class="btn btn-sm" id="save-version-btn">Speichern</button>
          <button type="button" class="btn btn-sm btn-danger" id="delete-version-btn">Version löschen</button>
        </div>
      </form>
    </div>
  `;

  const configContainer = document.getElementById('import-format-config');
  if (configContainer) {
    renderImportFormatConfigForm(configContainer, configObject, format, selectedVersion);
  }

  const select = document.getElementById('import-format-version-select');
  if (select) {
    select.value = selectedVersion;
    select.addEventListener('change', (e) => {
      const newVersion = e.target.value;
      const configContainer = container.querySelector('#import-format-config');
      if (configContainer) {
        const updatedConfig = getImportFormatConfigObject(format.config, newVersion);
        renderImportFormatConfigForm(configContainer, updatedConfig, format, newVersion);
      }
    });
  }

  const deleteBtn = container.querySelector('button[data-action="delete"]');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', () => removeImportFormat(format.id));
  }

  const addVersionBtn = container.querySelector('#add-version-btn');
  if (addVersionBtn) {
    addVersionBtn.addEventListener('click', () => showAddVersionDialog(format));
  }

  const renameVersionBtn = container.querySelector('#rename-version-btn');
  if (renameVersionBtn) {
    renameVersionBtn.addEventListener('click', () => {
      const versionSelect = container.querySelector('#import-format-version-select');
      const currentVersion = versionSelect?.value;
      if (!currentVersion) {
        showImportFormatsStatus('Bitte wählen Sie eine Version aus.', true);
        return;
      }
      showRenameVersionDialog(format, currentVersion);
    });
  }

  const saveVersionBtn = container.querySelector('#save-version-btn');
  if (saveVersionBtn) {
    const form = container.querySelector('#import-format-config-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const version = document.getElementById('import-format-version-select')?.value;
        if (!version) {
          showImportFormatsStatus('Bitte wählen Sie eine Version aus.', true);
          return;
        }
        saveImportFormatVersion(format.id, version, generateConfigFromForm(form));
      });
    }
  }

  const deleteVersionBtn = container.querySelector('#delete-version-btn');
  if (deleteVersionBtn) {
    deleteVersionBtn.addEventListener('click', () => {
      const version = document.getElementById('import-format-version-select')?.value;
      if (!version) {
        showImportFormatsStatus('Bitte wählen Sie eine Version aus.', true);
        return;
      }
      deleteImportFormatVersion(format.id, version);
    });
  }
}

function getImportFormatConfigObject(config, version) {
  if (!config) return null;
  let versionConfig = null;

  if (version && config[version]) {
    versionConfig = config[version];
  } else if (version && config.config && config.config[version]) {
    versionConfig = config.config[version];
  }

  if (!versionConfig && config.config && typeof config.config === 'object') {
    versionConfig = config.config;
  }

  if (!versionConfig && typeof config === 'object') {
    versionConfig = config;
  }

  return versionConfig;
}

function renderImportFormatConfig(container, value) {
  container.innerHTML = '';

  const node = buildImportFormatConfigNode(value);
  if (node) {
    container.appendChild(node);
  } else {
    container.textContent = '-';
  }
}

function buildImportFormatConfigNode(value) {
  if (value === null || value === undefined) {
    return document.createTextNode('-');
  }

  if (Array.isArray(value)) {
    const list = document.createElement('ul');
    list.className = 'config-list';
    value.forEach(item => {
      const itemNode = buildImportFormatConfigNode(item);
      const li = document.createElement('li');
      if (itemNode) li.appendChild(itemNode);
      list.appendChild(li);
    });
    return list;
  }

  if (typeof value === 'object') {
    const list = document.createElement('dl');
    list.className = 'config-list';
    Object.entries(value).forEach(([key, val]) => {
      const dt = document.createElement('dt');
      dt.textContent = key;
      const dd = document.createElement('dd');
      const child = buildImportFormatConfigNode(val);
      if (child) dd.appendChild(child);
      list.appendChild(dt);
      list.appendChild(dd);
    });
    return list;
  }

  const text = document.createElement('span');
  text.textContent = String(value);
  return text;
}

function renderImportFormatConfigForm(container, configObject, format, selectedVersion) {
  container.innerHTML = '';

  if (!configObject || typeof configObject !== 'object') {
    container.innerHTML = '<div class="details-meta">Ungültige Konfiguration.</div>';
    return;
  }

  const form = document.createElement('div');

  // Helper function to generate field name and label
  const toLabel = (key) => {
    const map = {
      'encoding': 'Encoding',
      'delimiter': 'Delimiter',
      'decimal': 'Dezimal',
      'date_format': 'Datumsformat',
      'header_skip': 'Header Zeilen überspringen'
    };
    return map[key] || key.replace(/_/g, ' ');
  };

  // Standard fields (corrected according to YAML structure)
  const standardFields = ['encoding', 'delimiter', 'decimal', 'date_format', 'header_skip'];
  const columnsObj = configObject.columns || {};
  const headerArray = configObject.header || [];

  // Render standard fields in one row
  const standardFieldsRow = document.createElement('div');
  standardFieldsRow.style.display = 'grid';
  standardFieldsRow.style.gridTemplateColumns = 'repeat(5, 1fr)';
  standardFieldsRow.style.gap = '8px';
  standardFieldsRow.style.marginBottom = '20px';

  standardFields.forEach(fieldKey => {
    const value = configObject[fieldKey] || '';
    const label = toLabel(fieldKey);
    
    const fieldGroup = document.createElement('div');
    fieldGroup.style.display = 'flex';
    fieldGroup.style.flexDirection = 'column';
    fieldGroup.style.gap = '4px';
    
    const labelEl = document.createElement('label');
    labelEl.textContent = label;
    labelEl.style.fontSize = '0.85em';
    labelEl.style.fontWeight = '500';
    labelEl.style.color = 'var(--color-text-secondary)';
    
    const inputEl = document.createElement('input');
    inputEl.type = fieldKey === 'header_skip' ? 'number' : 'text';
    inputEl.className = 'input-sm';
    inputEl.name = fieldKey;
    inputEl.value = String(value).replace(/"/g, '&quot;');
    inputEl.style.padding = '6px 8px';
    inputEl.style.fontSize = '0.9em';
    if (fieldKey === 'header_skip') inputEl.min = '0';
    
    fieldGroup.appendChild(labelEl);
    fieldGroup.appendChild(inputEl);
    standardFieldsRow.appendChild(fieldGroup);
  });

  form.appendChild(standardFieldsRow);

  // Header Array section (optional)
  const headerSection = document.createElement('div');
  headerSection.style.marginTop = '16px';
  headerSection.style.marginBottom = '20px';

  const headerTitleEl = document.createElement('div');
  headerTitleEl.className = 'details-meta';
  headerTitleEl.innerText = 'CSV-Spalten (Header) - Optional';
  headerTitleEl.style.margin = '0 0 8px 0';

  const headerDescEl = document.createElement('div');
  headerDescEl.style.fontSize = '0.85em';
  headerDescEl.style.color = 'var(--color-text-secondary)';
  headerDescEl.style.marginBottom = '8px';
  headerDescEl.innerText = 'CSV-Spaltennamen in Reihenfolge eingeben (durch Pipe | trennen)';

  const headerInputEl = document.createElement('input');
  headerInputEl.type = 'text';
  headerInputEl.className = 'input-sm';
  headerInputEl.name = 'header';
  headerInputEl.value = Array.isArray(headerArray) ? headerArray.join(' | ') : '';
  headerInputEl.placeholder = 'z.B. Datum | Betrag | Beschreibung | IBAN';
  headerInputEl.style.width = '100%';
  headerInputEl.style.padding = '6px 8px';
  headerInputEl.style.marginBottom = '4px';

  headerSection.appendChild(headerTitleEl);
  headerSection.appendChild(headerDescEl);
  headerSection.appendChild(headerInputEl);
  form.appendChild(headerSection);

  // Column Mapping section
  const columnsSection = document.createElement('div');
  columnsSection.style.marginTop = '12px';

  const columnsTitleEl = document.createElement('div');
  columnsTitleEl.className = 'details-meta';
  columnsTitleEl.innerText = 'Spalten-Zuordnung (Column Mapping)';
  columnsTitleEl.style.margin = '0 0 12px 0';
  columnsSection.appendChild(columnsTitleEl);

  // Column mapping table
  const table = document.createElement('table');
  table.style.width = '100%';
  table.style.borderCollapse = 'collapse';
  table.style.marginBottom = '12px';

  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr style="border-bottom: 2px solid var(--color-border); background-color: var(--color-bg-detail);">
      <th style="text-align: left; padding: 8px; font-weight: 600; font-size: 0.9em; width: 120px;">Feld</th>
      <th style="text-align: left; padding: 8px; font-weight: 600; font-size: 0.9em; width: 150px;">Strategie</th>
      <th style="text-align: left; padding: 8px; font-weight: 600; font-size: 0.9em; flex: 1;">Konfiguration</th>
    </tr>
  `;
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  tbody.id = 'columns-mapping-body';

  // Known column keys from typical import format structures
  const knownColumns = ['dateValue', 'dateCreation', 'amount', 'description', 'recipientApplicant', 'iban', 'bic', 'account'];
  
  knownColumns.forEach(colKey => {
    const colConfig = columnsObj[colKey] || null;
    addColumnMappingRow(tbody, colKey, colConfig);
  });

  table.appendChild(tbody);
  columnsSection.appendChild(table);
  form.appendChild(columnsSection);

  container.appendChild(form);
}

function addColumnMappingRow(tbody, columnKey, columnConfig) {
  const row = document.createElement('tr');
  row.style.borderBottom = '1px solid var(--color-border)';
  row.style.backgroundColor = 'var(--color-bg-base)';
  row.dataset.columnKey = columnKey;

  // Determine strategy
  let strategy = 'null';
  let configData = null;
  
  if (columnConfig === null) {
    strategy = 'null';
  } else if (typeof columnConfig === 'object') {
    if (columnConfig.name) {
      strategy = 'name';
      configData = columnConfig.name;
    } else if (columnConfig.join) {
      strategy = 'join';
      configData = columnConfig;
    } else if (columnConfig.sources) {
      strategy = 'regex';
      configData = columnConfig;
    }
  }

  row.innerHTML = `
    <td style="padding: 8px; font-weight: 500;">${columnKey}</td>
    <td style="padding: 8px; width: 150px;">
      <select class="input-sm column-strategy" data-column="${columnKey}" style="width: 100%; padding: 4px 6px; font-size: 0.9em; box-sizing: border-box;">
        <option value="null" ${strategy === 'null' ? 'selected' : ''}>Nicht verwendet</option>
        <option value="name" ${strategy === 'name' ? 'selected' : ''}>Name</option>
        <option value="join" ${strategy === 'join' ? 'selected' : ''}>Join</option>
        <option value="regex" ${strategy === 'regex' ? 'selected' : ''}>Regex</option>
      </select>
    </td>
    <td style="padding: 8px;" data-config-cell="true">
      <div id="config-${columnKey}" class="column-config-container"></div>
    </td>
  `;

  // Update config display when strategy changes
  const strategySelect = row.querySelector('.column-strategy');
  
  strategySelect.addEventListener('change', (e) => {
    const newStrategy = e.target.value;
    renderColumnConfigUI(row, columnKey, newStrategy, null);
  });

  // Initial render
  renderColumnConfigUI(row, columnKey, strategy, configData);

  tbody.appendChild(row);
}

function renderColumnConfigUI(row, columnKey, strategy, configData) {
  const configContainer = row.querySelector(`#config-${columnKey}`);
  if (!configContainer) return;

  configContainer.innerHTML = '';
  configContainer.style.display = 'flex';
  configContainer.style.flexDirection = 'column';
  configContainer.style.gap = '4px';

  if (strategy === 'null') {
    const note = document.createElement('div');
    note.style.fontSize = '0.85em';
    note.style.color = 'var(--color-text-secondary)';
    note.innerText = 'Dieses Feld wird nicht importiert';
    configContainer.appendChild(note);
  } 
  else if (strategy === 'name') {
    // Simple name: just one column
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'input-sm column-config-name';
    input.placeholder = 'z.B. Buchungstag, Betrag, IBAN...';
    input.value = configData || '';
    configContainer.appendChild(input);
  } 
  else if (strategy === 'join') {
    // Join: multiple columns + separator
    const colsInput = document.createElement('input');
    colsInput.type = 'text';
    colsInput.className = 'input-sm column-config-join-cols';
    colsInput.placeholder = 'Spalten (mit | trennen): Feld1 | Feld2 | Feld3';
    colsInput.value = (configData && Array.isArray(configData.join)) ? configData.join.join(' | ') : '';
    colsInput.style.marginBottom = '4px';

    const sepInput = document.createElement('input');
    sepInput.type = 'text';
    sepInput.className = 'input-sm column-config-join-sep';
    sepInput.placeholder = 'Trennzeichen (z.B. " | ")';
    sepInput.value = (configData && configData.separator) ? configData.separator : ' | ';

    configContainer.appendChild(colsInput);
    configContainer.appendChild(sepInput);
  } 
  else if (strategy === 'regex') {
    // Regex: multiple sources with regex patterns
    const sourcesContainer = document.createElement('div');
    sourcesContainer.id = `regex-sources-${columnKey}`;
    sourcesContainer.style.display = 'flex';
    sourcesContainer.style.flexDirection = 'column';
    sourcesContainer.style.gap = '8px';

    const sources = (configData && configData.sources) ? configData.sources : [];
    
    sources.forEach((source, idx) => {
      const sourceDiv = document.createElement('div');
      sourceDiv.style.padding = '8px';
      sourceDiv.style.backgroundColor = 'rgba(0,0,0,0.02)';
      sourceDiv.style.borderRadius = '3px';
      sourceDiv.style.display = 'grid';
      sourceDiv.style.gridTemplateColumns = '1fr 1fr 30px';
      sourceDiv.style.gap = '4px';

      const nameInput = document.createElement('input');
      nameInput.type = 'text';
      nameInput.className = 'input-sm column-config-regex-name';
      nameInput.placeholder = 'Feld-Name';
      nameInput.value = source.name || '';

      const regexInput = document.createElement('input');
      regexInput.type = 'text';
      regexInput.className = 'input-sm column-config-regex-pattern';
      regexInput.placeholder = 'Regex-Pattern';
      regexInput.value = source.regex || '';

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'action-btn delete';
      removeBtn.style.padding = '4px 6px';
      removeBtn.innerText = 'X';
      removeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        sourceDiv.remove();
      });

      sourceDiv.appendChild(nameInput);
      sourceDiv.appendChild(regexInput);
      sourceDiv.appendChild(removeBtn);
      sourcesContainer.appendChild(sourceDiv);
    });

    const addSourceBtn = document.createElement('button');
    addSourceBtn.type = 'button';
    addSourceBtn.className = 'btn btn-sm';
    addSourceBtn.style.alignSelf = 'flex-start';
    addSourceBtn.innerText = '+ Regex hinzufügen';
    addSourceBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const newSourceDiv = document.createElement('div');
      newSourceDiv.style.padding = '8px';
      newSourceDiv.style.backgroundColor = 'rgba(0,0,0,0.02)';
      newSourceDiv.style.borderRadius = '3px';
      newSourceDiv.style.display = 'grid';
      newSourceDiv.style.gridTemplateColumns = '1fr 1fr 30px';
      newSourceDiv.style.gap = '4px';

      const nameInput = document.createElement('input');
      nameInput.type = 'text';
      nameInput.className = 'input-sm column-config-regex-name';
      nameInput.placeholder = 'Feld-Name';

      const regexInput = document.createElement('input');
      regexInput.type = 'text';
      regexInput.className = 'input-sm column-config-regex-pattern';
      regexInput.placeholder = 'Regex-Pattern';

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'action-btn delete';
      removeBtn.style.padding = '4px 6px';
      removeBtn.innerText = 'X';
      removeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        newSourceDiv.remove();
      });

      newSourceDiv.appendChild(nameInput);
      newSourceDiv.appendChild(regexInput);
      newSourceDiv.appendChild(removeBtn);
      sourcesContainer.insertBefore(newSourceDiv, addSourceBtn);
    });

    configContainer.appendChild(sourcesContainer);
    configContainer.appendChild(addSourceBtn);
  }
}

function generateConfigFromForm(form) {
  const config = {};
  
  // Standard fields (encoding, delimiter, decimal, date_format, header_skip)
  const standardFields = ['encoding', 'delimiter', 'decimal', 'date_format', 'header_skip'];
  standardFields.forEach(fieldKey => {
    const input = form.querySelector(`input[name="${fieldKey}"]`);
    if (input && input.value) {
      config[fieldKey] = fieldKey === 'header_skip' ? parseInt(input.value) || 0 : input.value;
    }
  });

  // Header array (CSV column names)
  const headerInput = form.querySelector('input[name="header"]');
  if (headerInput && headerInput.value.trim()) {
    config.header = headerInput.value
      .split('|')
      .map(h => h.trim())
      .filter(h => h.length > 0);
  }

  // Column mappings
  const columns = {};
  const columnRows = form.querySelectorAll('tr[data-column-key]');
  
  columnRows.forEach(row => {
    const columnKey = row.dataset.columnKey;
    const strategySelect = row.querySelector('.column-strategy');
    const strategy = strategySelect ? strategySelect.value : 'null';
    const configContainer = row.querySelector(`#config-${columnKey}`);

    if (strategy === 'null') {
      // Don't include this column in the config
      return;
    } 
    else if (strategy === 'name') {
      // Simple name mapping
      const nameInput = configContainer.querySelector('.column-config-name');
      if (nameInput && nameInput.value) {
        columns[columnKey] = {
          name: nameInput.value
        };
      }
    } 
    else if (strategy === 'join') {
      // Join mapping with separator
      const colsInput = configContainer.querySelector('.column-config-join-cols');
      const sepInput = configContainer.querySelector('.column-config-join-sep');
      
      if (colsInput && colsInput.value) {
        const joinFields = colsInput.value
          .split('|')
          .map(f => f.trim())
          .filter(f => f.length > 0);
        
        columns[columnKey] = {
          join: joinFields,
          separator: sepInput ? sepInput.value : ' '
        };
      }
    } 
    else if (strategy === 'regex') {
      // Regex pattern mapping with sources
      const sourceContainers = configContainer.querySelectorAll('[class*="column-config-regex"]');
      const sources = [];
      
      const regexInputs = configContainer.querySelectorAll('.column-config-regex-name');
      regexInputs.forEach((nameInput, idx) => {
        const patternInput = configContainer.querySelectorAll('.column-config-regex-pattern')[idx];
        if (nameInput && nameInput.value && patternInput && patternInput.value) {
          sources.push({
            name: nameInput.value,
            regex: patternInput.value
          });
        }
      });

      if (sources.length > 0) {
        columns[columnKey] = {
          sources: sources
        };
      }
    }
  });

  if (Object.keys(columns).length > 0) {
    config.columns = columns;
  }

  return config;
}

async function saveImportFormatVersion(formatId, version, configObject) {
  const format = importFormats.find(f => f.id === formatId);
  if (!format) {
    showImportFormatsStatus('Format nicht mehr aufrufbar.', true);
    return;
  }

  try {
    const updatedConfig = { ...format.config };
    updatedConfig[version] = configObject;

    const updated = await updateImportFormat(formatId, format.name, updatedConfig);
    const idx = importFormats.findIndex(f => f.id === formatId);
    if (idx >= 0) {
      importFormats[idx] = updated;
      selectedImportFormatId = formatId;
      renderImportFormatsTable();
      showImportFormatsStatus(`Version "${version}" gespeichert.`);
    }
  } catch (err) {
    console.error('Save version failed:', err);
    showImportFormatsStatus(`Fehler beim Speichern: ${err.message}`, true);
  }
}

function renderImportFormatsTable() {
  const tbody = document.getElementById('import-formats-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (importFormats.length === 0) {
    tbody.innerHTML = '<tr><td colspan="2" style="text-align: center;">Keine Formate konfiguriert.</td></tr>';
    renderImportFormatDetails(null);
    return;
  }

  importFormats.forEach(format => {
    const tr = document.createElement('tr');
    const nameTd = document.createElement('td');
    const actionsTd = document.createElement('td');

    nameTd.style.textAlign = 'left';
    nameTd.textContent = format.name;

    actionsTd.style.textAlign = 'center';
    actionsTd.innerHTML = `
      <button class="action-btn delete" data-action="delete" data-id="${format.id}">Löschen</button>
    `;

    tr.dataset.id = String(format.id);
    tr.style.cursor = 'pointer';

    tr.appendChild(nameTd);
    tr.appendChild(actionsTd);
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('button[data-action="delete"]').forEach(btn => {
    btn.addEventListener('click', (event) => {
      event.stopPropagation();
      const id = parseInt(btn.getAttribute('data-id'), 10);
      removeImportFormat(id);
    });
  });

  tbody.querySelectorAll('tr').forEach(row => {
    row.addEventListener('click', () => {
      const id = parseInt(row.dataset.id, 10);
      if (!Number.isNaN(id)) {
        selectedImportFormatId = id;
        const selected = importFormats.find(f => f.id === id);
        renderImportFormatDetails(selected || null);
        tbody.querySelectorAll('tr').forEach(r => r.classList.remove('selected-row'));
        row.classList.add('selected-row');
      }
    });
  });

  if (selectedImportFormatId === null && importFormats.length > 0) {
    selectedImportFormatId = importFormats[0].id;
  }
  const current = importFormats.find(f => f.id === selectedImportFormatId) || importFormats[0];
  renderImportFormatDetails(current || null);
  if (current) {
    const activeRow = tbody.querySelector(`tr[data-id="${current.id}"]`);
    if (activeRow) activeRow.classList.add('selected-row');
  }
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

function showAddVersionDialog(format) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.id = 'add-version-modal';
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content" style="min-width: 40vw; max-width: 90vw;">
      <div class="modal-header">
        <h3>Neue Version hinzufügen</h3>
        <button class="btn-ghost" onclick="this.closest('.modal').remove()" aria-label="Schließen" style="color: white; font-size: 1.5em; background: none; border: none; cursor: pointer;">×</button>
      </div>
      <div class="modal-body">
        <form id="add-version-form">
          <div class="form-group">
            <label for="new-version-name">Versionsnummer</label>
            <input type="text" id="new-version-name" class="input-sm" required placeholder="z.B. v2.0">
          </div>
          <hr style="border: none; border-top: 1px solid var(--color-border); margin: 16px 0;">
          <div class="details-meta" style="margin-bottom: 12px;">Konfiguration</div>
          <div id="new-version-config-container"></div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="document.getElementById('add-version-modal').remove()">Abbrechen</button>
        <button type="button" class="btn" id="add-version-save-btn">Hinzufügen</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Handle click outside modal to close
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });

  // Get a template config from the first version
  const versions = getImportFormatVersions(format.config);
  const templateVersion = versions.length > 0 ? versions[0] : null;
  const templateConfig = templateVersion 
    ? getImportFormatConfigObject(format.config, templateVersion)
    : { encoding: 'utf-8', delimiter: ';', decimal: ',', date_format: '%d.%m.%Y', columns: {} };

  const configContainer = modal.querySelector('#new-version-config-container');
  renderImportFormatConfigForm(configContainer, templateConfig, format, 'new');

  // Handle save
  const saveBtn = modal.querySelector('#add-version-save-btn');
  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const form = modal.querySelector('#add-version-form');
      const versionInput = modal.querySelector('#new-version-name');
      const newVersion = versionInput?.value?.trim();

      if (!newVersion) {
        showImportFormatsStatus('Versionsnummer ist erforderlich.', true);
        return;
      }

      try {
        const currentFormat = importFormats.find(f => f.id === format.id);
        if (!currentFormat) {
          showImportFormatsStatus('Format nicht mehr aufrufbar.', true);
          return;
        }

        const versions = getImportFormatVersions(currentFormat.config);
        if (versions.includes(newVersion)) {
          showImportFormatsStatus(`Version "${newVersion}" existiert bereits.`, true);
          return;
        }

        const configObj = generateConfigFromForm(form);
        const updatedConfig = { ...currentFormat.config };
        updatedConfig[newVersion] = configObj;

        const updated = await updateImportFormat(currentFormat.id, currentFormat.name, updatedConfig);
        const idx = importFormats.findIndex(f => f.id === currentFormat.id);
        if (idx >= 0) {
          importFormats[idx] = updated;
          selectedImportFormatId = currentFormat.id;
          renderImportFormatsTable();
          showImportFormatsStatus(`Version "${newVersion}" hinzugefügt.`);
          modal.remove();
        }
      } catch (err) {
        console.error('Add version failed:', err);
        showImportFormatsStatus(`Fehler beim Hinzufügen: ${err.message}`, true);
      }
    });
  }
}


function showRenameVersionDialog(format, currentVersion) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content" style="min-width: 30vw; max-width: 60vw;">
      <div class="modal-header">
        <h3>Version umbenennen</h3>
        <button class="btn-ghost" onclick="this.closest('.modal').remove()" aria-label="Schließen" style="color: white; font-size: 1.5em; background: none; border: none; cursor: pointer;">×</button>
      </div>
      <div class="modal-body">
        <form id="rename-version-form">
          <div class="form-group">
            <label for="rename-version-old">Aktuelle Version</label>
            <input type="text" id="rename-version-old" class="input-sm" value="${currentVersion}" readonly style="background-color: var(--color-bg-detail); cursor: not-allowed;">
          </div>
          <div class="form-group">
            <label for="rename-version-new">Neue Versionsnummer</label>
            <input type="text" id="rename-version-new" class="input-sm" required placeholder="z.B. v2.1" value="${currentVersion}">
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Abbrechen</button>
        <button type="button" class="btn" id="rename-version-save-btn">Umbenennen</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Handle click outside modal to close
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });

  // Handle save
  const saveBtn = modal.querySelector('#rename-version-save-btn');
  const newVersionInput = modal.querySelector('#rename-version-new');
  
  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const newVersion = newVersionInput?.value?.trim();
      
      if (!newVersion) {
        alert('Bitte geben Sie eine neue Versionsnummer ein.');
        return;
      }

      if (newVersion === currentVersion) {
        alert('Die neue Versionsnummer ist gleich wie die aktuelle.');
        return;
      }

      const currentFormat = importFormats.find(f => f.id === format.id);
      if (!currentFormat) {
        showImportFormatsStatus('Format nicht mehr aufrufbar.', true);
        modal.remove();
        return;
      }

      const versions = getImportFormatVersions(currentFormat.config);
      if (versions.includes(newVersion)) {
        alert(`Version "${newVersion}" existiert bereits.`);
        return;
      }

      try {
        const updatedConfig = { ...currentFormat.config };
        
        // Copy the configuration from old version to new version
        updatedConfig[newVersion] = updatedConfig[currentVersion];
        
        // Update default version if it was the renamed version
        if (updatedConfig.default === currentVersion) {
          updatedConfig.default = newVersion;
        }
        
        // Delete old version
        delete updatedConfig[currentVersion];

        const updated = await updateImportFormat(currentFormat.id, currentFormat.name, updatedConfig);
        const idx = importFormats.findIndex(f => f.id === currentFormat.id);
        if (idx >= 0) {
          importFormats[idx] = updated;
          selectedImportFormatId = currentFormat.id;
          renderImportFormatsTable();
          showImportFormatsStatus(`Version "${currentVersion}" → "${newVersion}" umbenannt.`);
          modal.remove();
        }
      } catch (err) {
        console.error('Rename version failed:', err);
        showImportFormatsStatus(`Fehler beim Umbenennen: ${err.message}`, true);
      }
    });
  }
}


async function deleteImportFormatVersion(formatId, version) {
  const format = importFormats.find(f => f.id === formatId);
  if (!format) return;

  const versions = getImportFormatVersions(format.config);
  if (versions.length <= 1) {
    showImportFormatsStatus('Das Format muss mindestens eine Version haben.', true);
    return;
  }

  if (!confirm(`Version "${version}" wirklich löschen?`)) return;

  try {
    const updatedConfig = { ...format.config };
    delete updatedConfig[version];

    const updated = await updateImportFormat(formatId, format.name, updatedConfig);
    const idx = importFormats.findIndex(f => f.id === formatId);
    if (idx >= 0) {
      importFormats[idx] = updated;
      selectedImportFormatId = formatId;
      renderImportFormatsTable();
      showImportFormatsStatus(`Version "${version}" gelöscht.`);
    }
  } catch (err) {
    console.error('Delete version failed:', err);
    showImportFormatsStatus(`Fehler beim Löschen: ${err.message}`, true);
  }
}

async function removeImportFormat(id) {
  const format = importFormats.find(f => f.id === id);
  if (!format) return;
  if (!confirm(`Format "${format.name}" wirklich löschen?`)) return;

  try {
    await deleteImportFormat(id);
    importFormats = importFormats.filter(f => f.id !== id);
    showImportFormatsStatus('Format gelöscht.');
    if (selectedImportFormatId === id) {
      selectedImportFormatId = null;
    }
    renderImportFormatsTable();
  } catch (err) {
    console.error('Delete failed:', err);
    showImportFormatsStatus(`Fehler beim Löschen: ${err.message}`, true);
  }
}

async function initializeImportFormats() {
  console.log('Starte initializeImportFormats()...');
  try {
    importFormats = await fetchImportFormats();
    renderImportFormatsTable();

    const addBtn = document.getElementById('add-import-format-btn');
    if (addBtn) {
      console.log('Add-Button gefunden, registriere Click-Handler');
      addBtn.addEventListener('click', () => showImportFormatDialog());
    } else {
      console.warn('Add-Button nicht gefunden');
    }

    const reloadBtn = document.getElementById('reload-import-formats-btn');
    if (reloadBtn) {
      console.log('Reload-Button gefunden, registriere Click-Handler');
      reloadBtn.addEventListener('click', async () => {
        importFormats = await fetchImportFormats();
        renderImportFormatsTable();
        showImportFormatsStatus('Formate neu geladen.');
      });
    } else {
      console.warn('Reload-Button nicht gefunden');
    }

    const fileInput = document.getElementById('import-format-file-input');
    if (fileInput) {
      console.log('Dateielement gefunden, registriere Change-Handler');
      console.log('Dateielement Details:', {
        id: fileInput.id,
        type: fileInput.type,
        accept: fileInput.accept,
        display: window.getComputedStyle(fileInput).display
      });
      fileInput.addEventListener('change', (e) => {
        console.log('Change-Event ausgelöst für Dateielement');
        handleImportFormatFileUpload(e);
      });      
      console.log('Change-Handler registriert');
    } else {
      console.error('Dateielement mit ID "import-format-file-input" nicht gefunden!');
    }
  } catch (err) {
    console.error('Import formats init failed:', err);
    showImportFormatsStatus(`Fehler beim Laden: ${err.message}`, true);
  }
}

async function handleImportFormatFileUpload(event) {
  console.log('handleImportFormatFileUpload() wurde aufgerufen!');
  
  const file = event.target.files[0];
  if (!file) {
    console.warn('Keine Datei ausgewählt');
    return;
  }

  console.log('Datei ausgewählt:', {
    name: file.name,
    size: file.size,
    type: file.type
  });

  try {
    showImportFormatsStatus(`Lade YAML-Datei hoch und parse mit Python-Parser...`);
    
    // Use Python's yaml parser on the backend for correct parsing
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/settings/import-formats/upload-yaml', {
      method: 'POST',
      headers: getAuthHeaders(),  // Add auth header
      body: formData
    });
    
    const result = await response.json();
    
    if (!response.ok) {
      const errorMsg = result.detail || 'Unbekannter Fehler beim Upload';
      console.error('Backend-Fehler:', errorMsg);
      showImportFormatsStatus(`Fehler: ${errorMsg}`, true);
      event.target.value = '';
      return;
    }
    
    console.log('Python YAML-Parser erfolgreich:', result);
    
    if (result.imported_count > 0) {
      showImportFormatsStatus(
        `${result.imported_count}/${result.total_formats} Formate erfolgreich importiert!`
      );
      
      if (result.errors && result.errors.length > 0) {
        console.warn('Fehler bei einigen Formaten:', result.errors);
        for (const error of result.errors) {
          showImportFormatsStatus(`Fehler: ${error}`);
        }
      }
      
      // Reload formats list
      console.log('🔄 Laden Formate neu...');
      importFormats = await fetchImportFormats();
      renderImportFormatsTable();
    } else {
      showImportFormatsStatus(
        `Keine Formate importiert. ${result.errors ? result.errors.join(', ') : ''}`,
        true
      );
    }
    
    event.target.value = '';
  } catch (err) {
    console.error('Upload-Fehler:', err);
    showImportFormatsStatus(`Fehler beim Upload: ${err.message}`, true);
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
  console.log('Fetching account types...');
  try {
    const response = await authenticatedFetch('/api/settings/account-types');
    const data = await response.json();
    console.log('Received account types:', data);
    accountTypes = data.account_types || [];
    return accountTypes;
  } catch (error) {
    console.error('Error fetching account types:', error);
    showAccountTypesStatus(`Fehler beim Laden: ${error.message}`, true);
    return [];
  }
}

function renderAccountTypesTable() {
  const tbody = document.getElementById('account-types-tbody');
  if (!tbody) {
    console.error('account-types-tbody not found');
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
    console.error('Error fetching planning cycles:', error);
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

  // Map for readable units
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
  console.log(`Adding account type: ${typeName}`);
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
  console.log(`Updating account type ${typeId}: ${typeName}`);
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
  console.log(`Deleting account type ${typeId}`);
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
  console.log('handleAccountTypeFileUpload() wurde aufgerufen!');
  
  const file = event.target.files[0];
  if (!file) {
    console.warn('Keine Datei ausgewählt');
    return;
  }

  console.log('Datei ausgewählt:', {
    name: file.name,
    size: file.size,
    type: file.type
  });

  try {
    const content = await file.text();
    console.log('Dateiinhalt gelesen, starte YAML-Parsing...', {fileSize: content.length});
    
    const parsed = parseYAML(content);
    console.log('YAML erfolgreich geparst:', parsed);
    
    if (!parsed || !parsed.accountType) {
      showAccountTypesStatus('YAML-Datei enthält keinen "accountType"-Abschnitt.', true);
      return;
    }

    const accountTypeData = parsed.accountType;
    console.log('Account Type Daten:', accountTypeData);
    
    if (!Array.isArray(accountTypeData)) {
      showAccountTypesStatus('YAML-Format ungültig. Erwartet: Array von Kontotypen.', true);
      event.target.value = '';
      return;
    }
    
    console.log(`${accountTypeData.length} Kontotypen gefunden`);
    
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
    console.error('Fehler beim Verarbeiten:', error);
    showAccountTypesStatus(`Fehler beim Import: ${error.message}`, true);
    event.target.value = '';
  }
}

async function initializeAccountTypes() {
  console.log('Initializing account types tab...');
  
  try {
    await fetchAccountTypes();
    renderAccountTypesTable();
    
    const addBtn = document.getElementById('add-account-type-btn');
    const reloadBtn = document.getElementById('reload-account-types-btn');
    const fileInput = document.getElementById('account-type-file-input');
    
    console.log('Button-Suche:', { addBtn: !!addBtn, reloadBtn: !!reloadBtn, fileInput: !!fileInput });
    
    if (addBtn) {
      addBtn.addEventListener('click', showAddAccountTypeDialog);
      console.log('Add-Button Event-Listener hinzugefügt');
    } else {
      console.error('add-account-type-btn nicht gefunden!');
    }
    
    if (reloadBtn) {
      reloadBtn.addEventListener('click', async () => {
        await fetchAccountTypes();
        renderAccountTypesTable();
        showAccountTypesStatus('Kontotypen neu geladen.');
      });
      console.log('Reload-Button Event-Listener hinzugefügt');
    } else {
      console.error('reload-account-types-btn nicht gefunden!');
    }
    
    if (fileInput) {
      fileInput.addEventListener('change', handleAccountTypeFileUpload);
      console.log('File-Input Event-Listener hinzugefügt');
    } else {
      console.error('account-type-file-input nicht gefunden!');
    }
    
    console.log('Account Types Tab initialisiert');
  } catch (error) {
    console.error('Fehler bei der Initialisierung:', error);
    showAccountTypesStatus(`Initialisierungsfehler: ${error.message}`, true);
  }
}

// ========================================

document.addEventListener('DOMContentLoaded', () => {
  initSettingsPage();
});
