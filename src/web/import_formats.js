// Import formats page logics

// ========================================
// Import Format Management
// ========================================
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

function showImportFormatsStatus(msg, isError = false) {
  const el = document.getElementById('import-formats-status');
  if (!el) return;
  el.textContent = msg;
  el.style.color = isError ? 'var(--color-danger)' : 'var(--color-text)';
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