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

// Kontostand Header-Definition (mit umbenannter letzter Spalte)
const BALANCES_HEADERS = [
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
  'Jahresabschluss'
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

// Vermögen Monatsende Header-Definition
const ASSETS_HEADERS = [
  'Vermögen Ende des Monats',
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

// Generische Tabellen-Render-Funktion (wiederverwendbar)
function renderTableGeneric(tableId, rows, headers = null) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const headersToUse = headers || (
    tableId === 'securities-table' ? SECURITIES_HEADERS :
    tableId === 'assets-table' ? ASSETS_HEADERS :
    tableId === 'balances-table' ? BALANCES_HEADERS :
    MONTH_HEADERS
  );

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

  // Render rows
  const renderedRows = renderTableRowsGeneric(rows, document, tbody, headersToUse);

  // Calculate and append sum row if applicable
  if ((tableId === 'monthly-table' || tableId === 'balances-table' || tableId === 'loans-table' || tableId === 'investments-table' || tableId === 'assets-table' || tableId === 'securities-table') && rows.length > 0) {
    const sumRow = document.createElement('tr');
    sumRow.className = 'sum-row';
    sumRow.style.fontWeight = 'bold';
    sumRow.style.borderTop = '2px solid #999';

    headersToUse.forEach((key, index) => {
      const td = document.createElement('td');
      if (index === 0) {
        td.textContent = 'Summe';
        td.style.fontWeight = 'bold';
      } else {
        const sum = rows.reduce((acc, row) => acc + (typeof row[key] === 'number' ? row[key] : 0), 0);
        td.textContent = sum.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (sum < 0) td.classList.add('amount-negative');
        if (sum > 0) td.classList.add('amount-positive');
        td.style.fontWeight = 'bold';
      }
      sumRow.appendChild(td);
    });
    tbody.appendChild(sumRow);

    const sumRecord = headersToUse.reduce((acc, key, idx) => {
      acc[key] = idx === 0 ? 'Summe' : rows.reduce((acc2, row) => acc2 + (typeof row[key] === 'number' ? row[key] : 0), 0);
      return acc;
    }, {});
    renderedRows.push(sumRecord);
  }
}

// Render rows - generic
function renderTableRowsGeneric(rows, document, tbody, headersToUse) {
  const renderedRows = [];
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
    renderedRows.push(row);
  });

  return renderedRows;
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
const PAGE_TABLES = ['balances-table', 'monthly-table', 'investments-table', 'loans-table', 'securities-table', 'assets-table']; // assets-table must be last

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

  const el = document.getElementById('year-overview-refresh');
  if (el) {
    el.addEventListener('click', () => {
      const year = getSelectedYear();
      PAGE_TABLES.forEach(table => {
        engine.loadTable(table, year);
      });
    });
  };
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadTopNav('year-overview');
  initYearOverview();
});
