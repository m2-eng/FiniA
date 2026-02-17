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

// Globale Variable für synchronisierte Kategoriespalten-Breite
let globalCategoryWidth = 150; // Standardwert

// Globale Variablen für Konten-Filterung
let allAccounts = []; // Alle Konten mit allen Details
let isFilterActive = false; // Status des Filters

// Funktion zum Berechnen der optimalen Kategoriespalten-Breite über alle Tabellen
function calculateGlobalCategoryWidth(tableIds) {
  let maxCategoryLength = 0;
  
  tableIds.forEach(tableId => {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    // Durchsuche alle Zeilen und finde längsten Text in erster Spalte
    const rows = tbody.querySelectorAll('tr');
    rows.forEach(row => {
      const firstCell = row.querySelector('td:first-child');
      if (firstCell) {
        const text = firstCell.textContent.trim();
        maxCategoryLength = Math.max(maxCategoryLength, text.length);
      }
    });
  });
  
  // Berechne Breite: ~8px pro Zeichen + 16px Padding
  const width = Math.max(150, Math.min(400, maxCategoryLength * 8 + 16));
  return width;
}

// Funktion zum Anwenden der globalen Kategoriespalten-Breite auf alle Tabellen
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

// Generische Tabellen-Render-Funktion (wiederverwendbar)
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

  // Summenzeile für Bilanz- und Kontostands-Tabelle hinzufügen
  if ((tableId === 'monthly-table' || tableId === 'balances-table') && rows.length > 0) {
    const sumRow = document.createElement('tr');
    sumRow.className = 'sum-row';
    sumRow.style.fontWeight = 'bold';
    sumRow.style.borderTop = '2px solid #999';

    headersToUse.forEach((key, index) => {
      const td = document.createElement('td');
      
      // Erste Spalte: Label "Summe"
      if (index === 0) {
        td.textContent = 'Summe';
        td.style.fontWeight = 'bold';
      } else {
        // Numerische Spalten: Summe berechnen
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

// Hilfsfunktion: Aktuell ausgewähltes Jahr
function getSelectedYear() {
  const saved = localStorage.getItem('selectedYear');
  if (saved) return saved;
  const selector = document.getElementById('year-selector');
  return selector?.value || new Date().getFullYear().toString();
}

// Hilfsfunktion: Aktuell ausgewähltes Konto
function getSelectedAccount() {
  const selector = document.getElementById('account-selector');
  if (selector && selector.value) {
    return selector.value;
  }
  // Fallback auf localStorage
  return localStorage.getItem('selectedAccount') || '';
}

// Account-Dropdown laden
async function loadAccountDropdown() {
  try {
    const response = await authenticatedFetch(`${API_BASE}/accounts/list`);
    const data = await response.json();
    const accountSelector = document.getElementById('account-selector');

    if (!accountSelector || !data.accounts || data.accounts.length === 0) return;

    // Speichere alle Konten für Filterung
    allAccounts = data.accounts;

    // Render Dropdown initial
    renderAccountDropdown(allAccounts);
    
  } catch (error) {
    console.error('Failed to load accounts:', error);
  }
}

// Hilfsfunktion: Prüft, ob ein Konto im gegebenen Jahr aktiv war
function isAccountActiveInYear(account, year) {
  if (!account.dateStart) return true; // Kein Start-Datum = immer aktiv
  
  const yearNum = parseInt(year);
  const startDate = new Date(account.dateStart);
  const startYear = startDate.getFullYear();
  
  // Konto muss vor oder im Jahr starten
  if (startYear > yearNum) return false;
  
  // Wenn kein End-Datum, ist Konto noch aktiv
  if (!account.dateEnd) return true;
  
  const endDate = new Date(account.dateEnd);
  const endYear = endDate.getFullYear();
  
  // Konto muss nach oder im Jahr enden
  return endYear >= yearNum;
}

// Account-Dropdown rendern (mit optionaler Filterung)
function renderAccountDropdown(accounts, filterYear = null) {
  const accountSelector = document.getElementById('account-selector');
  if (!accountSelector) return;
  
  // Aktuell ausgewähltes Konto merken
  const currentSelection = accountSelector.value;
  
  // Filter anwenden, falls aktiv
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

  // Neue Auswahl nach dem Rendern
  const newSelection = accountSelector.value;
  
  // Wenn sich die Auswahl geändert hat (z.B. weil vorheriges Konto gefiltert wurde)
  if (currentSelection && currentSelection !== newSelection) {
    // localStorage aktualisieren
    localStorage.setItem('selectedAccount', newSelection);
    // Tabellen aktualisieren
    const currentYear = getSelectedYear();
    if (currentYear) {
      engine.loadAllTables(currentYear, PAGE_TABLES, newSelection);
    }
  }

  // Save default account name if none was saved before
  if (!savedAccount && accountNames.length > 0) {
    localStorage.setItem('selectedAccount', accountNames[0]);
  }
  
  // Add change event listener (nur einmalig)
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

// Filter-Button Toggle
function toggleFilter() {
  isFilterActive = !isFilterActive;
  const filterBtn = document.getElementById('filter-toggle-btn');
  const filterIcon = document.getElementById('filter-icon');
  
  if (isFilterActive) {
    filterBtn.classList.add('active');
    filterIcon.textContent = '✓';
    filterBtn.title = 'Filter aktiv - Nur Konten für ausgewähltes Jahr';
    // Filter anwenden
    const selectedYear = getSelectedYear();
    renderAccountDropdown(allAccounts, selectedYear);
  } else {
    filterBtn.classList.remove('active');
    filterIcon.textContent = '✗';
    filterBtn.title = 'Filter für aktive Konten im ausgewählten Jahr';
    // Alle Konten anzeigen
    renderAccountDropdown(allAccounts, null);
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
    // Bei aktivem Filter: Dropdown neu rendern
    if (isFilterActive && nextYear) {
      renderAccountDropdown(allAccounts, nextYear);
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

  // Aktualisieren-Button für alle Tabellen
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
  
  // Filter-Button Event-Listener
  const filterToggleBtn = document.getElementById('filter-toggle-btn');
  if (filterToggleBtn) {
    filterToggleBtn.addEventListener('click', toggleFilter);
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadTopNav('accounts');
  await loadAccountDropdown();
  initAccounts();
});
