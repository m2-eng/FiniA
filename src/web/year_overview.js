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

// Cache zuletzt gerenderter Tabellen (inkl. Summenzeile)
const LAST_ROWS = {};

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

  LAST_ROWS[tableId] = renderedRows;

  if (['balances-table', 'monthly-table', 'loans-table', 'securities-table'].includes(tableId)) {
    recomputeAssetsTable();
  }
}

// Rekombiniert die Vermögenstabelle aus vorhandenen Summenzeilen
function recomputeAssetsTable() {
  const balances = LAST_ROWS['balances-table'];
  const monthly = LAST_ROWS['monthly-table'];
  const loans = LAST_ROWS['loans-table'];
  const securities = LAST_ROWS['securities-table'];
  if (!balances || !monthly || !loans || !securities) return;

  const getSumRow = (rows) => rows.find(r => r[Object.keys(r)[0]] === 'Summe');
  const balSum = getSumRow(balances);
  const monSum = getSumRow(monthly);
  const loanSum = getSumRow(loans);
  const secSum = getSumRow(securities);
  if (!balSum || !monSum || !loanSum || !secSum) return;

  const kontostandRow = {
    'Vermögen Ende des Monats': 'Kontostand',
    'Januar': balSum['Februar'],
    'Februar': balSum['März'],
    'März': balSum['April'],
    'April': balSum['Mai'],
    'Mai': balSum['Juni'],
    'Juni': balSum['Juli'],
    'Juli': balSum['August'],
    'August': balSum['September'],
    'September': balSum['Oktober'],
    'Oktober': balSum['November'],
    'November': balSum['Dezember'],
    'Dezember': balSum['Jahresabschluss'],
    'Jahresbilanz': monSum['Jahresbilanz']
  };

  const darlehenRow = {
    'Vermögen Ende des Monats': 'Darlehen',
    'Januar': loanSum['Januar'],
    'Februar': loanSum['Februar'],
    'März': loanSum['März'],
    'April': loanSum['April'],
    'Mai': loanSum['Mai'],
    'Juni': loanSum['Juni'],
    'Juli': loanSum['Juli'],
    'August': loanSum['August'],
    'September': loanSum['September'],
    'Oktober': loanSum['Oktober'],
    'November': loanSum['November'],
    'Dezember': loanSum['Dezember'],
    'Jahresbilanz': 0  // Wird nachträglich korrigiert
  };

  const wertpapiereRow = {
    'Vermögen Ende des Monats': 'Wertpapiere',
    'Januar': secSum['Januar'],
    'Februar': secSum['Februar'],
    'März': secSum['März'],
    'April': secSum['April'],
    'Mai': secSum['Mai'],
    'Juni': secSum['Juni'],
    'Juli': secSum['Juli'],
    'August': secSum['August'],
    'September': secSum['September'],
    'Oktober': secSum['Oktober'],
    'November': secSum['November'],
    'Dezember': secSum['Dezember'],
    'Jahresbilanz': 0  // Wird nachträglich korrigiert
  };

  renderTableGeneric('assets-table', [kontostandRow, darlehenRow, wertpapiereRow], ASSETS_HEADERS);
  
  // Korrigiere die 2 Jahresbilanz-Zellen nach dem Rendering
  setTimeout(() => fixAssetsJahresbilanzCells(loanSum, secSum), 50);
}

// Korrigiert NUR die 2 Jahresbilanz-Zellen (Darlehen, Wertpapiere)
async function fixAssetsJahresbilanzCells(loanSum, secSum) {
  try {
    const table = document.getElementById('assets-table');
    if (!table) return;

    const year = getSelectedYear();
    const prevYear = Number(year) - 1;

    // Finde Jahresbilanz-Spaltenindex
    const headerCells = Array.from(table.querySelectorAll('thead tr th'));
    const jbIdx = headerCells.findIndex(th => th.textContent.trim() === 'Jahresbilanz');
    if (jbIdx < 0) return;

    // Finde Zeilen (ohne Summenzeile)
    const bodyRows = Array.from(table.querySelectorAll('tbody tr')).filter(tr => !tr.classList.contains('sum-row'));
    const findRow = (label) => bodyRows.find(tr => tr.children[0]?.textContent?.trim() === label);
    
    const loansRow = findRow('Darlehen');
    const secsRow = findRow('Wertpapiere');
    if (!loansRow && !secsRow) return;

    // Hole Vorjahres-Dezember-Werte aus den jeweiligen Quell-Tabellen
    let prevLoansDec = 0;
    let prevSecsDec = 0;
    
    // Darlehen: aus Darlehen-Tabelle Vorjahr Summenzeile
    const resLoans = await fetch(`${API_BASE}/year-overview/loans?year=${prevYear}`);
    if (resLoans.ok) {
      const dataLoans = await resLoans.json();
      const rowsLoans = dataLoans.rows || [];
      prevLoansDec = rowsLoans.reduce((acc, r) => acc + (typeof r['Dezember'] === 'number' ? r['Dezember'] : 0), 0);
    }
    
    // Wertpapiere: aus Wertpapiere-Tabelle Vorjahr Summenzeile
    const resSecs = await fetch(`${API_BASE}/year-overview/securities?year=${prevYear}`);
    if (resSecs.ok) {
      const dataSecs = await resSecs.json();
      const rowsSecs = dataSecs.rows || [];
      prevSecsDec = rowsSecs.reduce((acc, r) => acc + (typeof r['Dezember'] === 'number' ? r['Dezember'] : 0), 0);
    }
    
    const currentLoansDec = loanSum['Dezember'] ?? 0;
    const currentSecsDec = secSum['Dezember'] ?? 0;
    
    const formatDEAmount = (num) => {
      return Number(num).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };
    
    // Setze NUR die Jahresbilanz-Zellen
    if (loansRow) {
      const delta = currentLoansDec - prevLoansDec;
      const cell = loansRow.children[jbIdx];
      cell.textContent = formatDEAmount(delta);
      cell.classList.remove('amount-negative', 'amount-positive');
      if (delta < 0) cell.classList.add('amount-negative');
      if (delta > 0) cell.classList.add('amount-positive');
    }
    
    if (secsRow) {
      const delta = currentSecsDec - prevSecsDec;
      const cell = secsRow.children[jbIdx];
      cell.textContent = formatDEAmount(delta);
      cell.classList.remove('amount-negative', 'amount-positive');
      if (delta < 0) cell.classList.add('amount-negative');
      if (delta > 0) cell.classList.add('amount-positive');
    }
  } catch (e) {
    console.warn('fixAssetsJahresbilanzCells:', e);
  }
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
const PAGE_TABLES = ['assets-table', 'balances-table', 'monthly-table', 'investments-table', 'loans-table', 'securities-table'];

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

  const refreshBindings = [
    { btn: 'assets-refresh', table: 'assets-table' },
    { btn: 'balances-refresh', table: 'balances-table' },
    { btn: 'monthly-refresh', table: 'monthly-table' },
    { btn: 'investments-refresh', table: 'investments-table' },
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
  initYearOverview();
});
