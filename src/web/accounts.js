// Accounts page logic - reuses TableEngine

// Monthly header definition (as in year_overview.js)
const MONTH_HEADERS = [
  'Kategorie',
  'Januar',
  'Februar',
  'März',
  'April',
  'Mai',
  'Juni',
  'Juli',
  'August',
  'September',
  'Oktober',
  'November',
  'Dezember',
  'Gesamt'
];

// Global variable for synchronized category column width
let globalCategoryWidth = 150; // Default value

// Global variables for account filtering
let allAccounts = []; // All accounts with all details
let isFilterActive = true; // Filter status

// Function to calculate optimal category column width across all tables
function calculateGlobalCategoryWidth(tableIds) {
  let maxCategoryLength = 0;
  
  tableIds.forEach(tableId => {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    // Search all rows and find longest text in first column
    const rows = tbody.querySelectorAll('tr');
    rows.forEach(row => {
      const firstCell = row.querySelector('td:first-child');
      if (firstCell) {
        const text = firstCell.textContent.trim();
        maxCategoryLength = Math.max(maxCategoryLength, text.length);
      }
    });
  });
  
  // Calculate width: ~8px per character + 16px padding
  const width = Math.max(150, Math.min(400, maxCategoryLength * 8 + 16));
  return width;
}

// Function to apply global category column width to all tables
function applyGlobalCategoryWidth(tableIds, width) {
  globalCategoryWidth = width;
  
  tableIds.forEach(tableId => {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const firstColCells = table.querySelectorAll('th:first-child, td:first-child');
    firstColCells.forEach(cell => {
      cell.style.width = `${width}px`;
      cell.style.minWidth = `${width}px`;
      cell.style.maxWidth = `${width}px`;
    });
  });
}

// Generic table render function (reusable)
function renderTableGeneric(tableId, rows, headers = null) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const headersToUse = headers || MONTH_HEADERS;

  const thead = table.querySelector('thead');
  const tbody = table.querySelector('tbody');
  thead.innerHTML = '';
  tbody.innerHTML = '';

  const headerRow = document.createElement('tr');
  headersToUse.forEach(h => {
    const th = document.createElement('th');
    th.textContent = h;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  rows.forEach(row => {
    const tr = document.createElement('tr');
    headersToUse.forEach(key => {
      const td = document.createElement('td');
      const value = row[key] ?? '';
      if (typeof value === 'number') {
        td.textContent = value.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (value < 0) td.classList.add('amount-negative');
        if (value > 0) td.classList.add('amount-positive');
      } else {
        td.textContent = value;
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  // Add sum row for balance and account balance tables
  if ((tableId === 'monthly-table' || tableId === 'balances-table') && rows.length > 0) {
    const sumRow = document.createElement('tr');
    sumRow.className = 'sum-row';
    sumRow.style.fontWeight = 'bold';
    sumRow.style.borderTop = '2px solid #999';

    headersToUse.forEach((key, index) => {
      const td = document.createElement('td');
      
      // First column: Label "Summe"
      if (index === 0) {
        td.textContent = 'Summe';
        td.style.fontWeight = 'bold';
      } else {
        // Numeric columns: Calculate sum
        const sum = rows.reduce((acc, row) => {
          const val = row[key];
          return acc + (typeof val === 'number' ? val : 0);
        }, 0);
        
        td.textContent = sum.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (sum < 0) td.classList.add('amount-negative');
        if (sum > 0) td.classList.add('amount-positive');
        td.style.fontWeight = 'bold';
      }
      sumRow.appendChild(td);
    });
    tbody.appendChild(sumRow);
  }
}

// Helper function: Currently selected year
function getSelectedYear() {
  const saved = localStorage.getItem('selectedYear');
  if (saved) return saved;
  const selector = document.getElementById('year-selector');
  return selector?.value || new Date().getFullYear().toString();
}

// Helper function: Currently selected account
function getSelectedAccount() {
  const selector = document.getElementById('account-selector');
  if (selector && selector.value) {
    return selector.value;
  }
  // Fallback to localStorage
  return localStorage.getItem('selectedAccount') || '';
}

// Load account dropdown
async function loadAccountDropdown() {
  try {
    const response = await authenticatedFetch(`${API_BASE}/accounts/list`);
    const data = await response.json();
    const accountSelector = document.getElementById('account-selector');

    if (!accountSelector || !data.accounts || data.accounts.length === 0) return;

    // Store all accounts for filtering
    allAccounts = data.accounts;

    // Render dropdown initially with filter, if active
    const initialYear = isFilterActive ? getSelectedYear() : null;
    renderAccountDropdown(allAccounts, initialYear);
    
  } catch (error) {
    console.error('Failed to load accounts:', error);
  }
}

// Helper function: Check if account was active in given year
function isAccountActiveInYear(account, year) {
  if (!account.dateStart) return true; // No start date = always active
  
  const yearNum = parseInt(year);
  const startDate = new Date(account.dateStart);
  const startYear = startDate.getFullYear();
  
  // Account must start before or in year
  if (startYear > yearNum) return false;
  
  // If no end date, account is still active
  if (!account.dateEnd) return true;
  
  const endDate = new Date(account.dateEnd);
  const endYear = endDate.getFullYear();
  
  // Account must end after or in year
  return endYear >= yearNum;
}

// Render account dropdown (with optional filtering)
function renderAccountDropdown(accounts, filterYear = null) {
  const accountSelector = document.getElementById('account-selector');
  if (!accountSelector) return;
  
  // Remember currently selected account
  const currentSelection = accountSelector.value;
  
  // Apply filter if active
  let filteredAccounts = accounts;
  if (filterYear) {
    filteredAccounts = accounts.filter(acc => isAccountActiveInYear(acc, filterYear));
  }
  
  // Extract account names from filtered objects
  const accountNames = filteredAccounts.map(acc => acc.name).filter(Boolean);

  // Clear existing options
  accountSelector.innerHTML = '';

  // Add special aggregate options
  const allGiroOption = document.createElement('option');
  allGiroOption.value = '__ALL_GIRO__';
  allGiroOption.textContent = 'Alle Girokonten';
  accountSelector.appendChild(allGiroOption);

  const allLoansOption = document.createElement('option');
  allLoansOption.value = '__ALL_LOANS__';
  allLoansOption.textContent = 'Alle Darlehenskonten';
  accountSelector.appendChild(allLoansOption);

  const allAccountsOption = document.createElement('option');
  allAccountsOption.value = '__ALL_ACCOUNTS__';
  allAccountsOption.textContent = 'Alle Darlehens- und Girokonten';
  accountSelector.appendChild(allAccountsOption);

  // Get currently selected account from localStorage or use first account name
  const savedAccount = localStorage.getItem('selectedAccount');
  const defaultAccountName = savedAccount || accountNames[0];

  // Add account options (use names for value and label)
  accountNames.forEach(name => {
    const option = document.createElement('option');
    option.value = name;
    option.textContent = name;
    if (name === currentSelection || name === defaultAccountName) {
      option.selected = true;
    }
    accountSelector.appendChild(option);
  });

  // New selection after rendering
  const newSelection = accountSelector.value;
  
  // If selection changed (e.g. because previous account was filtered)
  if (currentSelection && currentSelection !== newSelection) {
    // Update localStorage
    localStorage.setItem('selectedAccount', newSelection);
    // Update tables
    const currentYear = getSelectedYear();
    if (currentYear) {
      engine.loadAllTables(currentYear, PAGE_TABLES, newSelection);
    }
  }

  // Save default account name if none was saved before
  if (!savedAccount && accountNames.length > 0) {
    localStorage.setItem('selectedAccount', accountNames[0]);
  }
  
  // Add change event listener (only once)
  if (!accountSelector.dataset.listenerAdded) {
    accountSelector.dataset.listenerAdded = 'true';
    accountSelector.addEventListener('change', (e) => {
      const selectedAccount = e.target.value;
      if (selectedAccount) {
        localStorage.setItem('selectedAccount', selectedAccount);
        // Trigger custom event for account change
        window.dispatchEvent(new CustomEvent('accountChanged', { detail: { account: selectedAccount } }));
      }
    });
  }
}

// Filter button toggle
function toggleFilter() {
  isFilterActive = !isFilterActive;
  const filterBtn = document.getElementById('filter-toggle-btn');
  const filterIcon = document.getElementById('filter-icon');
  
  if (isFilterActive) {
    filterBtn.classList.add('active');
    filterIcon.textContent = '✓';
    filterBtn.title = 'Filter aktiv - Nur Konten für ausgewähltes Jahr';
    // Apply filter
    const selectedYear = getSelectedYear();
    renderAccountDropdown(allAccounts, selectedYear);
  } else {
    filterBtn.classList.remove('active');
    filterIcon.textContent = '✗';
    filterBtn.title = 'Filter für aktive Konten im ausgewählten Jahr';
    // Show all accounts
    renderAccountDropdown(allAccounts, null);
  }
}

// Initialize TableEngine
const engine = new TableEngine(TABLE_CONFIGS);

// Table IDs for this page
const PAGE_TABLES = ['income-table', 'expenses-table', 'summary-table'];

// Initialize accounts page
function initAccounts() {
  const initialYear = getSelectedYear();
  const initialAccount = getSelectedAccount();
  
  if (initialAccount) {
    // Parallel loading for faster display
    engine.loadAllTables(initialYear, PAGE_TABLES, initialAccount);
  }

  // Listen to year changes
  window.addEventListener('yearChanged', (e) => {
    const nextYear = e.detail?.year;
    const currentAccount = getSelectedAccount();
    if (nextYear && currentAccount) {
      engine.loadAllTables(nextYear, PAGE_TABLES, currentAccount);
    }
    // With active filter: Re-render dropdown
    if (isFilterActive && nextYear) {
      renderAccountDropdown(allAccounts, nextYear);
    }
  });

  // Listen to account changes
  window.addEventListener('accountChanged', (e) => {
    const nextAccount = e.detail?.account;
    const currentYear = getSelectedYear();
    if (nextAccount && currentYear) {
      engine.loadAllTables(currentYear, PAGE_TABLES, nextAccount);
    }
  });

  // Refresh button for all tables
  const refreshAllBtn = document.getElementById('refresh-all-btn');
  if (refreshAllBtn) {
    refreshAllBtn.addEventListener('click', () => {
      const year = getSelectedYear();
      const account = getSelectedAccount();
      if (account) {
        engine.loadAllTables(year, PAGE_TABLES, account);
      }
    });
  }
  
  // Filter button event listener and set initial state
  const filterToggleBtn = document.getElementById('filter-toggle-btn');
  const filterIcon = document.getElementById('filter-icon');
  if (filterToggleBtn && filterIcon) {
    filterToggleBtn.addEventListener('click', toggleFilter);
    
    // Set initial visual state
    if (isFilterActive) {
      filterToggleBtn.classList.add('active');
      filterIcon.textContent = '✓';
      filterToggleBtn.title = 'Filter aktiv - Nur Konten für ausgewähltes Jahr';
    } else {
      filterToggleBtn.classList.remove('active');
      filterIcon.textContent = '✗';
      filterToggleBtn.title = 'Filter für aktive Konten im ausgewählten Jahr';
    }
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadTopNav('accounts');
  await loadAccountDropdown();
  initAccounts();
});
