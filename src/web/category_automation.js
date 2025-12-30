// Category Automation Management page logic
let currentPage = 1;
let allAccounts = [];
let allCategories = [];
let cachedRules = [];
let selectedRuleId = null;
let currentRuleData = null;

async function loadAccounts() {
  try {
    const response = await fetch(`${API_BASE}/accounts/list?page_size=1000`);
    const data = await response.json();
    allAccounts = data.accounts || [];
    populateAccountDropdown();
  } catch (error) {
    console.error('Failed to load accounts:', error);
    allAccounts = [];
  }
}

async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/categories/`);
    const data = await response.json();
    allCategories = data.categories || [];
    populateCategoryDropdown();
  } catch (error) {
    console.error('Failed to load categories:', error);
    allCategories = [];
  }
}

function populateAccountDropdown() {
  populateDropdown('accountFilter', allAccounts, 'name', '-- Alle Konten --');
  populateDropdown('ruleAccount', allAccounts, 'name', '-- Konto wählen --');
}

function populateCategoryDropdown() {
  populateDropdown('ruleCategory', allCategories, 'fullname', '-- Kategorie wählen --');
}

function onRuleTypeChange() {
  const ruleType = document.getElementById('ruleType').value;
  const valueSection = document.getElementById('valueSection');
  const amountSection = document.getElementById('amountSection');
  
  if (ruleType === 'amountRange') {
    valueSection.style.display = 'none';
    amountSection.style.display = 'block';
  } else {
    valueSection.style.display = 'block';
    amountSection.style.display = 'none';
  }
}

function onRuleChange() {
  // Called whenever rule fields change
}

async function loadRules(page = 1) {
  currentPage = page;
  const selectedAccount = document.getElementById('accountFilter').value;

  const loadingIndicator = document.getElementById('loadingIndicator');
  const rulesTable = document.getElementById('rulesTable');
  const errorMessage = document.getElementById('errorMessage');

  if (loadingIndicator) loadingIndicator.style.display = 'block';
  if (rulesTable) rulesTable.style.display = 'none';
  if (errorMessage) errorMessage.style.display = 'none';

  try {
    const params = new URLSearchParams({ page, page_size: 50 });
    if (selectedAccount) params.append('account', selectedAccount);

    const response = await fetch(`${API_BASE}/category-automation/list?${params}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const data = await response.json();
    displayRules(data.rules);
    displayPagination(data.page, Math.ceil(data.total / data.page_size));

    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (rulesTable) rulesTable.style.display = 'table';

    const stillVisible = data.rules.some(r => r.id === selectedRuleId);
    if (!stillVisible) clearRuleDetails();
  } catch (error) {
    console.error('Error loading rules:', error);
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (errorMessage) {
      errorMessage.textContent = `Fehler beim Laden der Regeln: ${error.message}`;
      errorMessage.style.display = 'block';
    }
  }
}

function displayRules(rules) {
  const tbody = document.getElementById('rulesBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  rules.forEach(rule => {
    const row = document.createElement('tr');
    row.dataset.id = String(rule.id);
    if (rule.id === selectedRuleId) row.classList.add('selected');
    
    const ruleDesc = formatRuleDescription(rule);
    
    row.innerHTML = `
      <td>${rule.account_name || '-'}</td>
      <td>${rule.columnName}</td>
      <td title="${ruleDesc}">${ruleDesc.substring(0, 40)}...</td>
      <td>${rule.category_name || '-'}</td>
      <td style="text-align: center;">${rule.priority}</td>
    `;
    row.onclick = () => showRuleDetails(rule.id);
    tbody.appendChild(row);
  });
}

function formatRuleDescription(rule) {
  const type = rule.type || 'contains';
  const value = rule.value || '';
  
  if (rule.type === 'amountRange') {
    const min = rule.minAmount !== null ? rule.minAmount : '0';
    const max = rule.maxAmount !== null ? rule.maxAmount : '∞';
    return `${type}: €${min} - €${max}`;
  }
  
  return `${type}: "${value}"`;
}

function displayPagination(currentPageNum, totalPages) {
  const pagination = document.getElementById('pagination');
  if (!pagination) return;
  pagination.innerHTML = '';

  const prevBtn = document.createElement('button');
  prevBtn.textContent = '← Vorherige';
  prevBtn.disabled = currentPageNum === 1;
  prevBtn.onclick = () => loadRules(currentPageNum - 1);
  pagination.appendChild(prevBtn);

  const pageInfo = document.createElement('span');
  pageInfo.textContent = `Seite ${currentPageNum} von ${totalPages}`;
  pageInfo.style.padding = '8px 16px';
  pagination.appendChild(pageInfo);

  const nextBtn = document.createElement('button');
  nextBtn.textContent = 'Nächste →';
  nextBtn.disabled = currentPageNum === totalPages;
  nextBtn.onclick = () => loadRules(currentPageNum + 1);
  pagination.appendChild(nextBtn);
}

function clearRuleDetails() {
  selectedRuleId = null;
  currentRuleData = null;
  const detailsPanel = document.getElementById('detailsPanel');
  if (detailsPanel) detailsPanel.style.display = 'none';
  clearRuleForm();
  document.querySelectorAll('#rulesBody tr.selected').forEach(tr => tr.classList.remove('selected'));
}

function filterByAccount() {
  loadRules(1);
}

function resetRuleFilter() {
  document.getElementById('accountFilter').value = '';
  loadRules(1);
  clearRuleDetails();
}

async function showRuleDetails(ruleId) {
  try {
    const response = await fetch(`${API_BASE}/category-automation/${ruleId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const rule = await response.json();
    
    selectedRuleId = rule.id;
    currentRuleData = rule;

    document.querySelectorAll('#rulesBody tr').forEach(tr => {
      if (tr.dataset.id === String(rule.id)) tr.classList.add('selected');
      else tr.classList.remove('selected');
    });

    // Populate form fields
    document.getElementById('ruleAccount').value = rule.account || '';
    document.getElementById('ruleColumn').value = rule.columnName || '';
    document.getElementById('ruleType').value = rule.type || 'contains';
    document.getElementById('ruleValue').value = rule.value || '';
    document.getElementById('ruleCaseSensitive').checked = rule.caseSensitive || false;
    document.getElementById('ruleMinAmount').value = rule.minAmount || '';
    document.getElementById('ruleMaxAmount').value = rule.maxAmount || '';
    document.getElementById('ruleCategory').value = rule.category || '';
    document.getElementById('rulePriority').value = rule.priority || 1;
    
    onRuleTypeChange();

    const detailsPanel = document.getElementById('detailsPanel');
    detailsPanel.style.display = 'block';
  } catch (error) {
    console.error('Error loading rule details:', error);
    alert(`Fehler beim Laden der Regelinformationen: ${error.message}`);
  }
}

function clearRuleForm() {
  selectedRuleId = null;
  currentRuleData = null;
  document.getElementById('ruleAccount').value = '';
  document.getElementById('ruleColumn').value = 'description';
  document.getElementById('ruleType').value = 'contains';
  document.getElementById('ruleValue').value = '';
  document.getElementById('ruleCaseSensitive').checked = false;
  document.getElementById('ruleMinAmount').value = '';
  document.getElementById('ruleMaxAmount').value = '';
  document.getElementById('ruleCategory').value = '';
  document.getElementById('rulePriority').value = 1;
  document.getElementById('testResult').style.display = 'none';
  onRuleTypeChange();
}

async function testRule() {
  const ruleType = document.getElementById('ruleType').value;
  const columnName = document.getElementById('ruleColumn').value;
  const value = document.getElementById('ruleValue').value;
  const caseSensitive = document.getElementById('ruleCaseSensitive').checked;
  const minAmount = document.getElementById('ruleMinAmount').value;
  const maxAmount = document.getElementById('ruleMaxAmount').value;
  
  const testDescription = document.getElementById('testDescription').value;
  const testRecipient = document.getElementById('testRecipient').value;
  const testAmount = document.getElementById('testAmount').value;

  if (!testDescription && ruleType !== 'amountRange') {
    alert('Bitte geben Sie mindestens eine Test-Beschreibung ein');
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/category-automation/test-rule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rule: {
          type: ruleType,
          columnName: columnName,
          value: value,
          caseSensitive: caseSensitive,
          minAmount: minAmount ? parseFloat(minAmount) : null,
          maxAmount: maxAmount ? parseFloat(maxAmount) : null,
          priority: 1,
          account: 1,
          category: 1
        },
        transaction: {
          description: testDescription,
          recipientApplicant: testRecipient || null,
          amount: testAmount && testAmount.trim() !== '' ? testAmount : null,
          iban: null
        }
      })
    });

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const result = await response.json();

    const resultDiv = document.getElementById('testResult');
    const resultText = document.getElementById('testResultText');
    resultText.textContent = result.message;
    resultText.style.color = result.matches ? 'var(--color-amount-positive)' : 'var(--color-amount-negative)';
    resultDiv.style.display = 'block';
  } catch (error) {
    console.error('Error testing rule:', error);
    alert(`Fehler beim Testen der Regel: ${error.message}`);
  }
}

async function saveRule() {
  const account = parseInt(document.getElementById('ruleAccount').value);
  const category = parseInt(document.getElementById('ruleCategory').value);
  const ruleType = document.getElementById('ruleType').value;
  const columnName = document.getElementById('ruleColumn').value;
  const value = document.getElementById('ruleValue').value;
  const caseSensitive = document.getElementById('ruleCaseSensitive').checked;
  const minAmount = document.getElementById('ruleMinAmount').value;
  const maxAmount = document.getElementById('ruleMaxAmount').value;
  const priority = parseInt(document.getElementById('rulePriority').value);

  if (!account || !category) {
    alert('Bitte wählen Sie Konto und Kategorie aus');
    return;
  }

  const ruleData = {
    type: ruleType,
    columnName: columnName,
    value: value || null,
    caseSensitive: caseSensitive,
    minAmount: minAmount ? parseFloat(minAmount) : null,
    maxAmount: maxAmount ? parseFloat(maxAmount) : null,
    priority: priority,
    account: account,
    category: category
  };

  const saveButton = document.getElementById('saveButton');
  const originalText = saveButton.textContent;
  saveButton.textContent = 'Speichert...';
  saveButton.disabled = true;

  try {
    let response;
    
    if (selectedRuleId) {
      response = await fetch(`${API_BASE}/category-automation/${selectedRuleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData)
      });
    } else {
      response = await fetch(`${API_BASE}/category-automation/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData)
      });
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    alert('Regel erfolgreich gespeichert!');
    clearRuleForm();
    await loadRules(currentPage);
  } catch (error) {
    console.error('Error saving rule:', error);
    alert(`Fehler beim Speichern: ${error.message}`);
  } finally {
    saveButton.textContent = originalText;
    saveButton.disabled = false;
  }
}

async function deleteRule() {
  if (!selectedRuleId) {
    alert('Keine Regel ausgewählt.');
    return;
  }

  if (!confirm('Wirklich diese Regel löschen?')) {
    return;
  }

  const deleteButton = document.getElementById('deleteButton');
  const originalText = deleteButton.textContent;
  deleteButton.textContent = 'Löscht...';
  deleteButton.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/category-automation/${selectedRuleId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    alert('Regel erfolgreich gelöscht!');
    clearRuleDetails();
    await loadRules(1);
  } catch (error) {
    console.error('Error deleting rule:', error);
    alert(`Fehler beim Löschen: ${error.message}`);
  } finally {
    deleteButton.textContent = originalText;
    deleteButton.disabled = false;
  }
}

// Page initialization
window.addEventListener('DOMContentLoaded', async () => {
  await loadAccounts();
  await loadCategories();
  loadRules(1);
});
