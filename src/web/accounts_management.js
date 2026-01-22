// Account Management page logic
let currentPage = 1;
let searchTerm = '';
let selectedAccountId = null;
let allAccountTypes = [];
let allImportFormats = [];
let allAccounts = [];
let currentSortColumn = null;
let currentSortDirection = 'asc';
let cachedAccounts = [];
let currentAccountData = null;

// Hilfsfunktion: Bestimme ob ein Konto aktiv oder beendet ist
function getAccountStatus(account) {
  if (!account.dateEnd) {
    return { text: 'Aktiv', class: 'status-active', isActive: true };
  }
  
  // Vergleiche aktuelles Datum mit Enddatum
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const endDate = new Date(account.dateEnd);
  endDate.setHours(0, 0, 0, 0);
  
  if (today >= endDate) {
    // Aktuelles Datum ist gleich oder nach Enddatum → Beendet
    return { text: 'Beendet', class: 'status-inactive', isActive: false };
  } else {
    // Enddatum liegt in der Zukunft → Aktiv
    return { text: 'Aktiv', class: 'status-active', isActive: true };
  }
}

async function loadAccountTypes() {
  try {
    const response = await fetch(`${API_BASE}/accounts/types/list`);
    const data = await response.json();
    allAccountTypes = data.types || [];
    populateAccountTypeDropdown();
  } catch (error) {
    console.error('Failed to load account types:', error);
    allAccountTypes = [];
  }
}

async function loadImportFormats() {
  try {
    const response = await fetch(`${API_BASE}/accounts/formats/list`);
    const data = await response.json();
    allImportFormats = data.formats || [];
    populateImportFormatDropdown();
  } catch (error) {
    console.error('Failed to load import formats:', error);
    allImportFormats = [];
  }
}

function populateAccountTypeDropdown() {
  populateDropdown('accountType', allAccountTypes, 'type', '-- Typ wählen --');
}

function populateImportFormatDropdown() {
  populateDropdown('importFormat', allImportFormats, 'type', '-- Format wählen --');
}

function sortAccounts(column) {
  if (currentSortColumn === column) {
    currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    currentSortColumn = column;
    currentSortDirection = 'asc';
  }

  const sorted = [...cachedAccounts].sort((a, b) => {
    let valA, valB;
    
    switch(column) {
      case 'name':
        valA = (a.name || '').toLowerCase();
        valB = (b.name || '').toLowerCase();
        break;
      case 'iban':
        valA = (a.iban_accountNumber || '').toLowerCase();
        valB = (b.iban_accountNumber || '').toLowerCase();
        break;
      case 'type':
        valA = (a.type_name || '').toLowerCase();
        valB = (b.type_name || '').toLowerCase();
        break;
      case 'status':
        const statusA = getAccountStatus(a);
        const statusB = getAccountStatus(b);
        valA = statusA.isActive ? 0 : 1;
        valB = statusB.isActive ? 0 : 1;
        break;
      default:
        return 0;
    }

    if (valA < valB) return currentSortDirection === 'asc' ? -1 : 1;
    if (valA > valB) return currentSortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  displayAccounts(sorted);
  updateSortIndicators();
}

function updateSortIndicators() {
  document.querySelectorAll('.transactions-table th').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
  });
  
  if (currentSortColumn) {
    const columnMap = {
      'name': 0,
      'iban': 1,
      'type': 2,
      'status': 3
    };
    const columnIndex = columnMap[currentSortColumn];
    if (columnIndex !== undefined) {
      const th = document.querySelectorAll('.transactions-table th')[columnIndex];
      if (th) {
        th.classList.add(currentSortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
      }
    }
  }
}

async function loadAccounts(page = 1) {
  currentPage = page;
  const searchInput = document.getElementById('searchInput');
  searchTerm = searchInput ? searchInput.value : '';

  const loadingIndicator = document.getElementById('loadingIndicator');
  const accountsTable = document.getElementById('accountsTable');
  const errorMessage = document.getElementById('errorMessage');

  if (loadingIndicator) loadingIndicator.style.display = 'block';
  if (accountsTable) accountsTable.style.display = 'none';
  if (errorMessage) errorMessage.style.display = 'none';

  try {
    const params = new URLSearchParams({ page, page_size: 50 });
    if (searchTerm) params.append('search', searchTerm);

    const response = await fetch(`${API_BASE}/accounts/list?${params}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const data = await response.json();
    displayAccounts(data.accounts, true);
    displayPagination(data.page, Math.ceil(data.total / data.page_size));

    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (accountsTable) accountsTable.style.display = 'table';

    const stillVisible = data.accounts.some(a => a.id === selectedAccountId);
    if (!stillVisible) clearDetails();
  } catch (error) {
    console.error('Error loading accounts:', error);
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (errorMessage) {
      errorMessage.textContent = `Fehler beim Laden der Konten: ${error.message}`;
      errorMessage.style.display = 'block';
    }
  }
}

function displayAccounts(accounts, isInitialLoad = false) {
  const tbody = document.getElementById('accountsBody');
  if (!tbody) return;
  
  if (isInitialLoad) {
    cachedAccounts = accounts;
    if (currentSortColumn) {
      sortAccounts(currentSortColumn);
      return;
    }
  }
  
  tbody.innerHTML = '';

  accounts.forEach(account => {
    const row = document.createElement('tr');
    row.dataset.id = String(account.id);
    if (account.id === selectedAccountId) row.classList.add('selected');
    
    const status = getAccountStatus(account);
    
    row.innerHTML = `
      <td>${account.name || '-'}</td>
      <td>${account.iban_accountNumber || '-'}</td>
      <td>${account.type_name || '-'}</td>
      <td style="text-align: center;"><span class="${status.class}">${status.text}</span></td>
    `;
    row.onclick = () => showAccountDetails(account.id);
    tbody.appendChild(row);
  });
}

function displayPagination(currentPageNum, totalPages) {
  const pagination = document.getElementById('pagination');
  if (!pagination) return;
  pagination.innerHTML = '';

  const prevBtn = document.createElement('button');
  prevBtn.textContent = '← Vorherige';
  prevBtn.disabled = currentPageNum === 1;
  prevBtn.onclick = () => loadAccounts(currentPageNum - 1);
  pagination.appendChild(prevBtn);

  const pageInfo = document.createElement('span');
  pageInfo.textContent = `Seite ${currentPageNum} von ${totalPages}`;
  pageInfo.style.padding = '8px 16px';
  pagination.appendChild(pageInfo);

  const nextBtn = document.createElement('button');
  nextBtn.textContent = 'Nächste →';
  nextBtn.disabled = currentPageNum === totalPages;
  nextBtn.onclick = () => loadAccounts(currentPageNum + 1);
  pagination.appendChild(nextBtn);
}

function clearDetails() {
  selectedAccountId = null;
  currentAccountData = null;
  const detailsPanel = document.getElementById('detailsPanel');
  if (detailsPanel) detailsPanel.style.display = 'none';
  resetForm();
  document.querySelectorAll('#accountsBody tr.selected').forEach(tr => tr.classList.remove('selected'));
}

function resetSearch() {
  const input = document.getElementById('searchInput');
  if (input) input.value = '';
  loadAccounts(1);
  clearDetails();
}

async function showAccountDetails(accountId) {
  try {
    const response = await fetch(`${API_BASE}/accounts/${accountId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const account = await response.json();
    
    selectedAccountId = account.id;
    currentAccountData = account;

    document.querySelectorAll('#accountsBody tr').forEach(tr => {
      if (tr.dataset.id === String(account.id)) tr.classList.add('selected');
      else tr.classList.remove('selected');
    });

    // Load clearing accounts FIRST (before setting the value)
    await loadClearingAccounts(account.id);

    // Populate form fields
    document.getElementById('accountName').value = account.name || '';
    document.getElementById('accountIban').value = account.iban_accountNumber || '';
    document.getElementById('accountBic').value = account.bic_market || '';
    document.getElementById('accountType').value = account.type || '';
    document.getElementById('startAmount').value = account.startAmount || 0;
    document.getElementById('startDate').value = toDateInputValue(account.dateStart);
    document.getElementById('endDate').value = toDateInputValue(account.dateEnd);
    document.getElementById('importFormat').value = account.importFormat || '';
    document.getElementById('importPath').value = account.importPath || '';
    
    // Set clearing account AFTER options are loaded
    document.getElementById('clearingAccount').value = account.clearingAccount || '';

    const detailsPanel = document.getElementById('detailsPanel');
    detailsPanel.style.display = 'block';
  } catch (error) {
    console.error('Error loading account details:', error);
    alert(`Fehler beim Laden der Kontoinformationen: ${error.message}`);
  }
}

async function loadClearingAccounts(excludeId) {
  try {
    const response = await fetch(`${API_BASE}/accounts/list?page_size=1000`);
    const data = await response.json();
    const dropdown = document.getElementById('clearingAccount');
    dropdown.innerHTML = '<option value="">-- Keine Auswahl --</option>';
    
    data.accounts.forEach(account => {
      if (account.id !== excludeId) {
        const option = document.createElement('option');
        option.value = account.id;
        option.textContent = account.name;
        dropdown.appendChild(option);
      }
    });
  } catch (error) {
    console.error('Error loading clearing accounts:', error);
  }
}

function resetForm() {
  document.getElementById('accountName').value = '';
  document.getElementById('accountIban').value = '';
  document.getElementById('accountBic').value = '';
  document.getElementById('accountType').value = '';
  document.getElementById('startAmount').value = '';
  document.getElementById('startDate').value = '';
  document.getElementById('endDate').value = '';
  document.getElementById('clearingAccount').value = '';
  document.getElementById('importFormat').value = '';
  document.getElementById('importPath').value = '';
}

async function saveAccount() {
  if (!selectedAccountId) {
    alert('Kein Konto ausgewählt.');
    return;
  }

  const saveButton = document.getElementById('saveButton');
  const originalText = saveButton.textContent;
  saveButton.textContent = 'Speichert...';
  saveButton.disabled = true;

  try {
    const accountData = {
      name: document.getElementById('accountName').value,
      iban_accountNumber: document.getElementById('accountIban').value,
      bic_market: document.getElementById('accountBic').value,
      type: parseInt(document.getElementById('accountType').value) || null,
      startAmount: parseFloat(document.getElementById('startAmount').value) || 0,
      dateStart: document.getElementById('startDate').value,
      dateEnd: document.getElementById('endDate').value || null,
      clearingAccount: parseInt(document.getElementById('clearingAccount').value) || null,
      importFormat: parseInt(document.getElementById('importFormat').value) || null,
      importPath: document.getElementById('importPath').value
    };

    const response = await fetch(`${API_BASE}/accounts/${selectedAccountId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(accountData)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    const updatedAccount = await response.json();
    currentAccountData = updatedAccount;
    await loadAccounts(currentPage);
    alert('Konto erfolgreich gespeichert!');
  } catch (error) {
    console.error('Error saving account:', error);
    alert(`Fehler beim Speichern: ${error.message}`);
  } finally {
    saveButton.textContent = originalText;
    saveButton.disabled = false;
  }
}

async function deleteAccount() {
  if (!selectedAccountId) {
    alert('Kein Konto ausgewählt.');
    return;
  }

  const accountName = document.getElementById('accountName').value;
  if (!confirm(`Wirklich das Konto "${accountName}" löschen? Diese Aktion kann nicht rückgängig gemacht werden.`)) {
    return;
  }

  const deleteButton = document.getElementById('deleteButton');
  const originalText = deleteButton.textContent;
  deleteButton.textContent = 'Löscht...';
  deleteButton.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/accounts/${selectedAccountId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    alert('Konto erfolgreich gelöscht!');
    clearDetails();
    await loadAccounts(1);
  } catch (error) {
    console.error('Error deleting account:', error);
    alert(`Fehler beim Löschen: ${error.message}`);
  } finally {
    deleteButton.textContent = originalText;
    deleteButton.disabled = false;
  }
}

// Page initialization
async function initAccountsManagement() {
  await loadAccountTypes();
  await loadImportFormats();
  
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') loadAccounts(1);
    });
  }
  await loadAccounts(1);
}

// Keep original behavior for standalone page
window.addEventListener('DOMContentLoaded', initAccountsManagement);
