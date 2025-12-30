// Jahresübersicht page logic - refaktoriert mit TableEngine

// Monatliche Header-Definition
const MONTH_HEADERS = [
  'Konto',
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
  'Jahresbilanz'
];

// Wertpapier Header-Definition
const SECURITIES_HEADERS = [
  'Wertpapier',
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
  'Dividende'
];

// Generische Tabellen-Render-Funktion (wiederverwendbar)
function renderTableGeneric(tableId, rows, headers = null) {
  const table = document.getElementById(tableId);
  if (!table) return;

  // Wähle Header basierend auf Tabellen-ID
  const headersToUse = headers || (tableId === 'securities-table' ? SECURITIES_HEADERS : MONTH_HEADERS);

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
}

// Hilfsfunktion: Aktuell ausgewähltes Jahr
function getSelectedYear() {
  const saved = localStorage.getItem('selectedYear');
  if (saved) return saved;
  const selector = document.getElementById('year-selector');
  return selector?.value || new Date().getFullYear().toString();
}

// TableEngine initialisieren
const engine = new TableEngine(TABLE_CONFIGS);

// Tabellen-IDs für diese Seite
const PAGE_TABLES = ['balances-table', 'monthly-table', 'loans-table', 'securities-table'];

// Initialisierung der Jahresübersicht
function initYearOverview() {
  const initialYear = getSelectedYear();
  engine.loadAllTables(initialYear, PAGE_TABLES);

  window.addEventListener('yearChanged', (e) => {
    const nextYear = e.detail?.year;
    if (nextYear) {
      engine.loadAllTables(nextYear, PAGE_TABLES);
    }
  });

  // Manuelle Aktualisieren-Buttons
  const refreshBindings = [
    { btn: 'balances-refresh', table: 'balances-table' },
    { btn: 'monthly-refresh', table: 'monthly-table' },
    { btn: 'loans-refresh', table: 'loans-table' },
    { btn: 'securities-refresh', table: 'securities-table' }
  ];
  refreshBindings.forEach(({ btn, table }) => {
    const el = document.getElementById(btn);
    if (el) {
      el.addEventListener('click', () => {
        const year = getSelectedYear();
        engine.loadTable(table, year);
      });
    }
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadTopNav('year-overview');
  // Lokalen Jahres-Dropdown laden
  await loadYearDropdown();
  initYearOverview();
});
