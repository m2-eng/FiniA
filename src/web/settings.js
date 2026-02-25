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

// UI functions
function showStatus(msg, isError = false) {
  const el = document.getElementById('settings-status');
  if (!el) return;
  el.textContent = msg;
  el.style.color = isError ? 'var(--color-danger)' : 'var(--color-text)';
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

document.addEventListener('DOMContentLoaded', () => {
  initSettingsPage();
});
