// Accounts page logic - wiederverwendet TableEngine

// Monatliche Header-Definition (wie in year_overview.js)
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

// Generische Tabellen-Render-Funktion (wiederverwendbar)
function renderTableGeneric(tableId, rows) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const thead = table.querySelector('thead');
  const tbody = table.querySelector('tbody');
  thead.innerHTML = '';
  tbody.innerHTML = '';

  const headerRow = document.createElement('tr');
  MONTH_HEADERS.forEach(h => {
    const th = document.createElement('th');
    th.textContent = h;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  rows.forEach(row => {
    const tr = document.createElement('tr');
    MONTH_HEADERS.forEach(key => {
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
}

// Hilfsfunktion: Aktuell ausgewähltes Jahr
function getSelectedYear() {
  const saved = localStorage.getItem('selectedYear');
  if (saved) return saved;
  const selector = document.getElementById('year-selector');
  return selector?.value || new Date().getFullYear().toString();
}

// Hilfsfunktion: Aktuell ausgewähltes Konto
function getSelectedAccount() {
  const saved = localStorage.getItem('selectedAccount');
  if (saved) return saved;
  const selector = document.getElementById('account-selector');
  return selector?.value || '';
}

// Account-Dropdown laden
async function loadAccountDropdown() {
  try {
    const response = await fetch(`${API_BASE}/accounts/list`);
    const data = await response.json();
    const accountSelector = document.getElementById('account-selector');
    
    if (!accountSelector || !data.accounts || data.accounts.length === 0) return;
    
    // Clear existing options
    accountSelector.innerHTML = '';
    
    // Get currently selected account from localStorage or use first account
    const savedAccount = localStorage.getItem('selectedAccount');
    const defaultAccount = savedAccount || data.accounts[0];
    
    // Add account options
    data.accounts.forEach(account => {
      const option = document.createElement('option');
      option.value = account;
      option.textContent = account;
      if (account === defaultAccount) {
        option.selected = true;
      }
      accountSelector.appendChild(option);
    });
    
    // Save default account if none was saved before
    if (!savedAccount && data.accounts.length > 0) {
      localStorage.setItem('selectedAccount', data.accounts[0]);
    }
    
    // Add change event listener
    accountSelector.addEventListener('change', (e) => {
      const selectedAccount = e.target.value;
      if (selectedAccount) {
        localStorage.setItem('selectedAccount', selectedAccount);
        // Trigger custom event for account change
        window.dispatchEvent(new CustomEvent('accountChanged', { detail: { account: selectedAccount } }));
      }
    });
    
  } catch (error) {
    console.error('Failed to load accounts:', error);
  }
}

// TableEngine initialisieren
const engine = new TableEngine(TABLE_CONFIGS);

// Tabellen-IDs für diese Seite
const PAGE_TABLES = ['income-table', 'expenses-table', 'summary-table'];

// Initialisierung der Accounts-Seite
function initAccounts() {
  const initialYear = getSelectedYear();
  const initialAccount = getSelectedAccount();
  
  if (initialAccount) {
    // Paralleles Laden für schnellere Darstellung
    engine.loadAllTables(initialYear, PAGE_TABLES, initialAccount);
  }

  // Listen auf Jahr-Änderungen
  window.addEventListener('yearChanged', (e) => {
    const nextYear = e.detail?.year;
    const currentAccount = getSelectedAccount();
    if (nextYear && currentAccount) {
      engine.loadAllTables(nextYear, PAGE_TABLES, currentAccount);
    }
  });

  // Listen auf Account-Änderungen
  window.addEventListener('accountChanged', (e) => {
    const nextAccount = e.detail?.account;
    const currentYear = getSelectedYear();
    if (nextAccount && currentYear) {
      engine.loadAllTables(currentYear, PAGE_TABLES, nextAccount);
    }
  });

  // Manuelle Aktualisieren-Buttons
  const refreshBindings = [
    { btn: 'income-refresh', table: 'income-table' },
    { btn: 'expenses-refresh', table: 'expenses-table' },
    { btn: 'summary-refresh', table: 'summary-table' }
  ];
  refreshBindings.forEach(({ btn, table }) => {
    const el = document.getElementById(btn);
    if (el) {
      el.addEventListener('click', () => {
        const year = getSelectedYear();
        const account = getSelectedAccount();
        if (account) {
          engine.loadTable(table, year, account);
        }
      });
    }
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadTopNav('accounts');
  // Lokalen Jahres-Dropdown laden
  await loadYearDropdown();
  await loadAccountDropdown();
  initAccounts();
});
