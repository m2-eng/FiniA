// Category Automation Management - JavaScript Logic

// Use existing variables from settings.js if available, otherwise initialize
if (typeof allRules === 'undefined') window.allRules = [];
if (typeof allAccounts === 'undefined') window.allAccounts = [];
if (typeof allCategories === 'undefined') window.allCategories = [];

let selectedRuleId = null;
let selectedRules = new Set();
let sortColumn = null;
let sortDirection = 'asc';
let automationAccountsLoading = false;

async function ensureAccountsLoaded() {
  if (Array.isArray(allAccounts) && allAccounts.length > 0) return allAccounts;
  if (automationAccountsLoading) {
    await new Promise(resolve => setTimeout(resolve, 150));
    if (Array.isArray(allAccounts) && allAccounts.length > 0) return allAccounts;
  }
  await loadAccounts();
  return allAccounts || [];
}

// ================== Initialization ==================

// Don't auto-initialize on DOMContentLoaded (will be called manually from settings page)
async function initializeCategoryAutomation() {
  // Run sequentially to ensure categories/accounts are ready before rendering rules
  await loadAccounts();
  await loadCategories();
  await loadRules();
  if (selectedRuleId) displayRuleDetails(selectedRuleId);
}

async function loadAccounts() {
  try {
    automationAccountsLoading = true;
    const response = await fetch(`${API_BASE}/accounts/list?page_size=1000`);
    const data = await response.json();
    window.allAccounts = data.accounts || [];
    allAccounts = window.allAccounts;
  } catch (error) {
    console.error('Failed to load accounts:', error);
    showError('Fehler beim Laden der Konten');
  } finally {
    automationAccountsLoading = false;
  }
}

async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/categories/list`);
    const data = await response.json();
    allCategories = data.categories || [];
  } catch (error) {
    console.error('Failed to load categories:', error);
    showError('Fehler beim Laden der Kategorien');
  }
}

async function loadRules() {
  const loadingIndicator = document.getElementById('loadingIndicator');
  const rulesTable = document.getElementById('rulesTable');
  const errorMessage = document.getElementById('errorMessage');

  loadingIndicator.style.display = 'block';
  rulesTable.style.display = 'none';
  errorMessage.style.display = 'none';

  try {
    const response = await fetch(`${API_BASE}/category-automation/rules`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    allRules = data.rules || [];
    
    renderRulesTable();
    loadingIndicator.style.display = 'none';
    rulesTable.style.display = 'table';
  } catch (error) {
    console.error('Error loading rules:', error);
    loadingIndicator.style.display = 'none';
    showError(`Fehler beim Laden der Regeln: ${error.message}`);
  }
}

// ================== Table Rendering ==================

function renderRulesTable() {
  const tbody = document.getElementById('rulesBody');
  tbody.innerHTML = '';

  let filteredRules = filterRules();
  if (sortColumn) {
    filteredRules = sortRulesBy(filteredRules, sortColumn, sortDirection);
  }

  if (filteredRules.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">Keine Regeln gefunden</td></tr>';
    return;
  }

  filteredRules.forEach(rule => {
    const row = tbody.insertRow();
    row.className = rule.id === selectedRuleId ? 'rule-row selected' : 'rule-row';
    row.onclick = () => selectRule(rule.id);

    // Checkbox
    const checkCell = row.insertCell();
    checkCell.style.textAlign = 'center';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = selectedRules.has(rule.id);
    checkbox.onclick = (e) => {
      e.stopPropagation();
      toggleRuleSelection(rule.id);
    };
    checkCell.appendChild(checkbox);

    // Description
    row.insertCell().textContent = rule.description || '(keine Beschreibung)';

    // Category
    const categoryName =
      allCategories.find(c => c.id === rule.category)?.fullname ||
      rule.category_name ||
      rule.category_fullname ||
      `ID: ${rule.category}`;
    row.insertCell().textContent = categoryName;

    // Accounts
    const accountsCell = row.insertCell();
    accountsCell.style.textAlign = 'center';
    if (!rule.accounts || rule.accounts.length === 0) {
      accountsCell.textContent = 'Alle';
    } else {
      accountsCell.textContent = `${rule.accounts.length} Konto(en)`;
    }

    // Conditions
    const conditionsCell = row.insertCell();
    conditionsCell.style.textAlign = 'center';
    conditionsCell.textContent = `${rule.conditions.length}`;

    // Active
    const activeCell = row.insertCell();
    activeCell.style.textAlign = 'center';
    activeCell.textContent = rule.enabled ? '✓' : '✗';
    activeCell.style.color = rule.enabled ? 'green' : 'red';

    // Actions
    const actionsCell = row.insertCell();
    actionsCell.className = 'rule-actions';
    actionsCell.innerHTML = `
      <button class="btn-small test" onclick="event.stopPropagation(); openTestModal('${rule.id}')">Test</button>
      <button class="btn-small delete" onclick="event.stopPropagation(); deleteRule('${rule.id}')">Löschen</button>
    `;
  });
}

function filterRules() {
  const searchText = document.getElementById('rulesSearch').value.toLowerCase();
  const hideInactive = document.getElementById('hideInactive').checked;

  return allRules.filter(rule => {
    if (hideInactive && !rule.enabled) return false;
    
    if (searchText) {
      const description = (rule.description || '').toLowerCase();
      const categoryName = (allCategories.find(c => c.id === rule.category)?.fullname || '').toLowerCase();
      if (!description.includes(searchText) && !categoryName.includes(searchText)) {
        return false;
      }
    }
    
    return true;
  });
}

function sortRulesBy(rules, column, direction) {
  return [...rules].sort((a, b) => {
    let aVal, bVal;
    
    if (column === 'description') {
      aVal = (a.description || '').toLowerCase();
      bVal = (b.description || '').toLowerCase();
    } else if (column === 'category') {
      aVal = (allCategories.find(c => c.id === a.category)?.fullname || '').toLowerCase();
      bVal = (allCategories.find(c => c.id === b.category)?.fullname || '').toLowerCase();
    }
    
    if (aVal < bVal) return direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return direction === 'asc' ? 1 : -1;
    return 0;
  });
}

function sortRules(column) {
  if (sortColumn === column) {
    sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    sortColumn = column;
    sortDirection = 'asc';
  }
  
  // Update sort indicators
  document.querySelectorAll('.sort-indicator').forEach(el => el.textContent = '');
  const indicator = document.getElementById(`sort-${column}`);
  if (indicator) indicator.textContent = sortDirection === 'asc' ? '▲' : '▼';
  
  renderRulesTable();
}

// ================== Rule Selection ==================

async function selectRule(ruleId) {
  selectedRuleId = ruleId;
  renderRulesTable();
  await displayRuleDetails(ruleId);
}

function toggleRuleSelection(ruleId) {
  if (selectedRules.has(ruleId)) {
    selectedRules.delete(ruleId);
  } else {
    selectedRules.add(ruleId);
  }
  
  document.getElementById('selectedRulesCount').textContent = selectedRules.size;
  document.getElementById('mergeButton').disabled = selectedRules.size < 2;
  renderRulesTable();
}

function toggleSelectAll(checked) {
  selectedRules.clear();
  if (checked) {
    filterRules().forEach(rule => selectedRules.add(rule.id));
  }
  
  document.getElementById('selectedRulesCount').textContent = selectedRules.size;
  document.getElementById('mergeButton').disabled = selectedRules.size < 2;
  renderRulesTable();
}

// ================== Rule Details Display ==================

async function displayRuleDetails(ruleId) {
  const rule = allRules.find(r => r.id === ruleId);
  if (!rule) return;

  const detailsContent = document.getElementById('detailsContent');
  if (detailsContent) {
    detailsContent.innerHTML = '<p class="details-meta">Konten werden geladen...</p>';
  }

  const accounts = await ensureAccountsLoaded();

  const detailsTitle = document.getElementById('detailsTitle');
  // detailsContent already retrieved above
  
  detailsTitle.textContent = 'Details';
  
  detailsContent.innerHTML = `
    <div class="detail-item">
      <span>Beschreibung</span>
      <input type="text" id="editDescription" class="input-sm" value="${escapeHtml(rule.description || '')}" placeholder="Kurze Beschreibung der Regel">
    </div>
    
    <div class="detail-item">
      <span>Kategorie</span>
      <select id="editCategory" class="input-sm">
        ${allCategories.map(cat => `<option value="${cat.id}" ${cat.id === rule.category ? 'selected' : ''}>${escapeHtml(cat.fullname)}</option>`).join('')}
      </select>
    </div>
    
    <div class="detail-item">
      <span>Konten (Mehrfachauswahl möglich)</span>
      <div class="account-select-box">
        <label>
          <input type="checkbox" id="account-all" ${!rule.accounts || rule.accounts.length === 0 ? 'checked' : ''} onchange="toggleAllAccounts()"> 
          <strong>Alle Konten</strong>
        </label>
        <hr style="margin: 4px 0;">
        ${accounts.length === 0 ? '<div class="details-meta">Keine Konten geladen.</div>' : accounts.map(acc => `
          <label>
            <input type="checkbox" class="account-checkbox" value="${acc.id}" ${rule.accounts && rule.accounts.includes(acc.id) ? 'checked' : ''}> 
            ${escapeHtml(acc.name)} (${escapeHtml(acc.iban || 'keine IBAN')})
          </label>
        `).join('')}
      </div>
    </div>
    
    <div class="detail-item">
      <span>Aktiv</span>
      <label style="cursor: pointer;">
        <input type="checkbox" id="editActive" ${rule.enabled ? 'checked' : ''}> 
        Regel ist aktiv
      </label>
    </div>
    
    <div class="detail-item">
      <span>Bedingungen</span>
      <div id="conditionsContainer">
        ${rule.conditions.map((cond, idx) => renderConditionRow(cond, idx)).join('')}
      </div>
      <div style="margin-top: 8px;">
        <button class="btn-small" onclick="addCondition()" style="width: 100%;">Bedingung hinzufügen</button>
      </div>
    </div>
    
    <div class="detail-item">
      <span>Bedingungslogik</span>
      <input type="text" id="editLogic" class="input-sm" value="${escapeHtml(rule.conditionLogic || '')}" placeholder="z.B. 1 OR 2 AND 3">
      <div class="logic-preview">
        <strong>Bedeutung:</strong> ${interpretLogic(rule.conditionLogic, rule.conditions)}
      </div>
    </div>
    
    <div class="detail-actions">
      <button class="btn" onclick="saveCurrentRule()">Speichern</button>
      <button class="btn btn-secondary" onclick="openTestModal('${rule.id}')">Regel testen</button>
      <button class="btn-small delete" onclick="deleteRule('${rule.id}')">Löschen</button>
    </div>
  `;
}

function renderConditionRow(condition, index) {
  const types = ['contains', 'equals', 'startsWith', 'endsWith', 'regex', 'amountRange'];
  const columns = ['description', 'recipientApplicant', 'iban', 'amount'];
  
  let valueInput = '';
  if (condition.type === 'amountRange') {
    valueInput = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
        <input type="number" class="input-sm cond-min" value="${condition.minAmount || ''}" placeholder="Min" step="0.01">
        <input type="number" class="input-sm cond-max" value="${condition.maxAmount || ''}" placeholder="Max" step="0.01">
      </div>
    `;
  } else {
    valueInput = `
      <div style="display: flex; gap: 4px; align-items: center;">
        <input type="text" class="input-sm cond-value" value="${escapeHtml(condition.value || '')}" placeholder="Wert" style="flex: 1;">
        <label style="white-space: nowrap; cursor: pointer;">
          <input type="checkbox" class="cond-case" ${condition.caseSensitive ? 'checked' : ''}> 
          <span style="font-size: 0.85em;">Aa</span>
        </label>
      </div>
    `;
  }
  
  return `
    <div class="condition-row" data-index="${index}">
      <span class="condition-number">${index + 1}.</span>
      <select class="input-sm cond-column">
        ${columns.map(col => `<option value="${col}" ${col === condition.columnName ? 'selected' : ''}>${getColumnLabel(col)}</option>`).join('')}
      </select>
      <select class="input-sm cond-type" onchange="onConditionTypeChange(${index})">
        ${types.map(type => `<option value="${type}" ${type === condition.type ? 'selected' : ''}>${getTypeLabel(type)}</option>`).join('')}
      </select>
      ${valueInput}
      <button class="btn-small delete" onclick="removeCondition(${index})" title="Bedingung löschen" style="width: 100%;">Löschen</button>
    </div>
  `;
}

function getColumnLabel(column) {
  const labels = {
    description: 'Beschreibung',
    recipientApplicant: 'Empf./Absend.',
    iban: 'IBAN',
    amount: 'Betrag'
  };
  return labels[column] || column;
}

function getTypeLabel(type) {
  const labels = {
    contains: 'Enthält',
    equals: 'Gleich',
    startsWith: 'Beginnt mit',
    endsWith: 'Endet mit',
    regex: 'Regex',
    amountRange: 'Bereich'
  };
  return labels[type] || type;
}

function interpretLogic(logic, conditions) {
  if (!logic || conditions.length === 0) return 'Keine Bedingungen';
  if (conditions.length === 1) return 'Bedingung 1 muss zutreffen';
  
  // Replace numbers with descriptions
  let interpretation = logic;
  conditions.forEach((cond, idx) => {
    const desc = `"${getColumnLabel(cond.column)} ${getTypeLabel(cond.type)} ${cond.value || ''}"`;
    interpretation = interpretation.replace(new RegExp(`\\b${idx + 1}\\b`, 'g'), desc);
  });
  
  return interpretation;
}

function onConditionTypeChange(index) {
  const rule = allRules.find(r => r.id === selectedRuleId);
  if (!rule) return;
  
  const row = document.querySelector(`.condition-row[data-index="${index}"]`);
  const typeSelect = row.querySelector('.cond-type');
  const newType = typeSelect.value;
  
  rule.conditions[index].type = newType;
  displayRuleDetails(selectedRuleId);
}

function addCondition() {
  const rule = allRules.find(r => r.id === selectedRuleId);
  if (!rule) return;
  
  rule.conditions.push({
    id: rule.conditions.length + 1,
    columnName: 'description',
    type: 'contains',
    value: '',
    caseSensitive: false
  });
  
  displayRuleDetails(selectedRuleId);
}

function removeCondition(index) {
  const rule = allRules.find(r => r.id === selectedRuleId);
  if (!rule || rule.conditions.length <= 1) {
    alert('Eine Regel muss mindestens eine Bedingung haben!');
    return;
  }
  
  rule.conditions.splice(index, 1);
  
  // Update logic string (remove references to removed condition)
  const logicInput = document.getElementById('editLogic');
  if (logicInput) {
    let logic = logicInput.value;
    // Remove the number and renumber subsequent ones
    logic = logic.replace(new RegExp(`\\b${index + 1}\\b`, 'g'), '');
    rule.conditionLogic = logic;
  }
  
  displayRuleDetails(selectedRuleId);
}

function toggleAllAccounts() {
  const allCheckbox = document.getElementById('account-all');
  const accountCheckboxes = document.querySelectorAll('.account-checkbox');
  
  if (allCheckbox.checked) {
    accountCheckboxes.forEach(cb => cb.checked = false);
  }
}

// ================== Save Rule ==================

async function saveCurrentRule() {
  const rule = allRules.find(r => r.id === selectedRuleId);
  if (!rule) return;
  
  // Collect data from form
  rule.name = document.getElementById('editDescription').value; // name = description for simplicity
  rule.description = document.getElementById('editDescription').value;
  rule.category = parseInt(document.getElementById('editCategory').value);
  rule.enabled = document.getElementById('editActive').checked;
  rule.conditionLogic = document.getElementById('editLogic').value;
  
  // Collect account IDs
  const allAccountsChecked = document.getElementById('account-all').checked;
  if (allAccountsChecked) {
    rule.accounts = [];
  } else {
    rule.accounts = Array.from(document.querySelectorAll('.account-checkbox:checked')).map(cb => parseInt(cb.value));
  }
  
  // Collect conditions
  const conditionRows = document.querySelectorAll('.condition-row');
  rule.conditions = Array.from(conditionRows).map((row, idx) => {
    const columnName = row.querySelector('.cond-column').value;
    const type = row.querySelector('.cond-type').value;
    
    const condition = { 
      id: idx + 1,
      columnName, 
      type 
    };
    
    if (type === 'amountRange') {
      condition.minAmount = parseFloat(row.querySelector('.cond-min').value) || null;
      condition.maxAmount = parseFloat(row.querySelector('.cond-max').value) || null;
    } else {
      condition.value = row.querySelector('.cond-value').value;
      condition.caseSensitive = row.querySelector('.cond-case').checked;
    }
    
    return condition;
  });
  
  // Validation
  if (!rule.name || !rule.description) {
    alert('Bitte geben Sie eine Beschreibung ein.');
    return;
  }
  if (!rule.category) {
    alert('Bitte wählen Sie eine Kategorie.');
    return;
  }
  if (rule.conditions.length === 0) {
    alert('Eine Regel muss mindestens eine Bedingung haben.');
    return;
  }
  
  // Save to API
  try {
    const response = await fetch(`${API_BASE}/category-automation/rules/${rule.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rule)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Fehler beim Speichern');
    }
    
    await loadRules();
    selectRule(rule.id);
  } catch (error) {
    console.error('Save error:', error);
    alert(`Fehler beim Speichern: ${error.message}`);
  }
}

// ================== Create New Rule ==================

function createNewRule() {
  const newRule = {
    id: `new-${Date.now()}`,
    name: 'Neue Regel',
    description: 'Neue Regel',
    category: allCategories[0]?.id || 1,
    accounts: [],
    enabled: true,
    conditions: [{
      id: 1,
      columnName: 'description',
      type: 'contains',
      value: '',
      caseSensitive: false
    }],
    conditionLogic: '1'
  };
  
  allRules.unshift(newRule);
  renderRulesTable();
  selectRule(newRule.id);
}

// ================== Delete Rule ==================

async function deleteRule(ruleId) {
  if (!confirm('Möchten Sie diese Regel wirklich löschen?')) return;
  
  try {
    const response = await fetch(`${API_BASE}/category-automation/rules/${ruleId}`, {
      method: 'DELETE'
    });
    
    if (!response.ok) throw new Error('Fehler beim Löschen');
    
    allRules = allRules.filter(r => r.id !== ruleId);
    selectedRuleId = null;
    renderRulesTable();
    
    document.getElementById('detailsContent').innerHTML = '<p class="details-meta">Regel wurde gelöscht.</p>';
  } catch (error) {
    console.error('Delete error:', error);
    alert(`Fehler beim Löschen: ${error.message}`);
  }
}

// ================== Test Modal ==================

function openTestModal(ruleId) {
  selectedRuleId = ruleId;
  document.getElementById('testModal').style.display = 'block';
  document.getElementById('testResult').innerHTML = '';
}

function closeTestModal() {
  document.getElementById('testModal').style.display = 'none';
}

async function executeTest() {
  const rule = allRules.find(r => r.id === selectedRuleId);
  if (!rule) return;
  
  const transaction = {
    description: document.getElementById('testDescription').value,
    recipientApplicant: document.getElementById('testRecipient').value,
    iban: document.getElementById('testIban').value,
    amount: parseFloat(document.getElementById('testAmount').value) || 0
  };
  
  try {
    const response = await fetch(`${API_BASE}/category-automation/test-rule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rule, transaction })
    });
    
    const result = await response.json();
    
    const resultDiv = document.getElementById('testResult');
    if (result.matches) {
      resultDiv.innerHTML = '<div class="test-result success">✓ Regel trifft zu!</div>';
    } else {
      resultDiv.innerHTML = '<div class="test-result failure">✗ Regel trifft nicht zu</div>';
    }
  } catch (error) {
    console.error('Test error:', error);
    alert(`Fehler beim Testen: ${error.message}`);
  }
}

// ================== Merge Modal ==================

async function mergeSelectedRules() {
  if (selectedRules.size < 2) {
    alert('Bitte wählen Sie mindestens 2 Regeln zum Zusammenführen aus.');
    return;
  }
  const previewEl = document.getElementById('mergePreview');
  if (previewEl) previewEl.innerHTML = '<p class="details-meta">Konten werden geladen...</p>';

  const accounts = await ensureAccountsLoaded();
  
  const rules = Array.from(selectedRules).map(id => allRules.find(r => r.id === id));
  
  // Build preview
  const preview = document.getElementById('mergePreview');
  preview.innerHTML = `
    <h4>Ausgewählte Regeln (${rules.length}):</h4>
    <ul>
      ${rules.map(r => `<li>${escapeHtml(r.description)} (${r.conditions.length} Bedingungen)</li>`).join('')}
    </ul>
    <p><strong>Gesamt:</strong> ${rules.reduce((sum, r) => sum + r.conditions.length, 0)} Bedingungen</p>
  `;
  
  // Auto-generate description
  const categories = [...new Set(rules.map(r => allCategories.find(c => c.id === r.category_id)?.fullname))];
  document.getElementById('mergeDescription').value = `Zusammengeführt: ${rules.map(r => r.description).join(', ')}`;
  
  // Merge all accounts from selected rules
  const allAccountIds = rules.flatMap(r => r.accounts || []);
  const uniqueAccountIds = [...new Set(allAccountIds)];
  
  // Populate account checkboxes
  const accountsBox = document.getElementById('mergeAccountsBox');
  const allAccountsCheckbox = document.getElementById('merge-account-all');
  
  if (uniqueAccountIds.length === 0) {
    allAccountsCheckbox.checked = true;
    accountsBox.style.display = 'none';
  } else {
    allAccountsCheckbox.checked = false;
    accountsBox.style.display = 'block';
    const accounts = Array.isArray(allAccounts) ? allAccounts : [];
    accountsBox.innerHTML = accounts.length === 0 ? '<div class="details-meta">Keine Konten geladen.</div>' : accounts.map(acc => {
      const isChecked = uniqueAccountIds.includes(acc.id);
      return `
        <label>
          <input type="checkbox" class="merge-account-checkbox" value="${acc.id}" ${isChecked ? 'checked' : ''}> 
          ${escapeHtml(acc.name)}
        </label>
      `;
    }).join('');
  }
  
  // Auto-generate logic (all conditions OR)
  let conditionCount = 0;
  const logic = rules.map(r => {
    const start = conditionCount + 1;
    conditionCount += r.conditions.length;
    if (r.conditions.length === 1) return `${start}`;
    const nums = Array.from({length: r.conditions.length}, (_, i) => start + i).join(' AND ');
    return `(${nums})`;
  }).join(' OR ');
  
  document.getElementById('mergeLogic').value = logic;
  document.getElementById('mergeLogicPreview').textContent = `${conditionCount} Bedingungen verknüpft mit OR`;
  
  document.getElementById('mergeModal').style.display = 'block';
}

function closeMergeModal() {
  document.getElementById('mergeModal').style.display = 'none';
}

function toggleMergeAllAccounts() {
  const allChecked = document.getElementById('merge-account-all').checked;
  const accountsBox = document.getElementById('mergeAccountsBox');
  accountsBox.style.display = allChecked ? 'none' : 'block';
}

async function executeMerge() {
  const description = document.getElementById('mergeDescription').value;
  const logic = document.getElementById('mergeLogic').value;
  
  if (!description) {
    alert('Bitte geben Sie eine Beschreibung ein.');
    return;
  }
  
  const rules = Array.from(selectedRules).map(id => allRules.find(r => r.id === id));
  
  // Check all rules have same category
  const categories = [...new Set(rules.map(r => r.category))];
  if (categories.length > 1) {
    if (!confirm('Die ausgewählten Regeln haben unterschiedliche Kategorien. Die Kategorie der ersten Regel wird verwendet. Fortfahren?')) {
      return;
    }
  }
  
  // Merge conditions
  const mergedConditions = rules.flatMap(r => r.conditions);
  
  // Renumber condition IDs to ensure uniqueness
  mergedConditions.forEach((condition, index) => {
    condition.id = index + 1;
  });
  
  // Get accounts from UI selection
  const allAccountsChecked = document.getElementById('merge-account-all').checked;
  let selectedAccountIds = [];
  if (!allAccountsChecked) {
    selectedAccountIds = Array.from(document.querySelectorAll('.merge-account-checkbox:checked')).map(cb => parseInt(cb.value));
  }
  
  const mergedRule = {
    name: description,
    description,
    category: rules[0].category,
    accounts: selectedAccountIds,
    enabled: true,
    conditions: mergedConditions,
    conditionLogic: logic
  };
  
  try {
    // Create new merged rule
    const response = await fetch(`${API_BASE}/category-automation/rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mergedRule)
    });
    
    if (!response.ok) throw new Error('Fehler beim Erstellen der zusammengeführten Regel');
    
    // Delete old rules
    for (const ruleId of selectedRules) {
      await fetch(`${API_BASE}/category-automation/rules/${ruleId}`, { method: 'DELETE' });
    }
    
    alert(`${selectedRules.size} Regeln erfolgreich zusammengeführt!`);
    selectedRules.clear();
    closeMergeModal();
    await loadRules();
  } catch (error) {
    console.error('Merge error:', error);
    alert(`Fehler beim Zusammenführen: ${error.message}`);
  }
}

// ================== Utility Functions ==================

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

function showError(message) {
  const errorDiv = document.getElementById('errorMessage');
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
}
