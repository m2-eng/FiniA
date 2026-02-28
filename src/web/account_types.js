// Account types page logic

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