// Shares page logic

const PAGE_SIZE = 20;
let sharesOptions = [];
let sharesFilter = 'in_stock';
const sharesSort = { by: 'name', dir: 'asc' };
const transactionsSort = { by: 'dateTransaction', dir: 'desc' };
const historySort = { by: 'date', dir: 'desc' };
let historyFilter = 'unchecked';
let currentTransactionsPage = 1;

// Local formatDate as fallback (also defined in utils.js)

function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatDateTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) + ' ' +
         date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
}
// Initialize shares page
async function initSharesPage() {
  console.log('Initializing shares page...');
  
  try {
    // Wait for app.js functions
    let retries = 0;
    while (retries < 50 && (typeof loadTopNav !== 'function' || typeof loadTheme !== 'function')) {
      await new Promise(resolve => setTimeout(resolve, 100));
      retries++;
    }
    
    if (typeof loadTopNav !== 'function' || typeof loadTheme !== 'function') {
      throw new Error('Required app.js functions not loaded');
    }
    
    // Load UI components
    await loadTopNav('shares');
    await loadTheme();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load initial data
    await Promise.all([
      loadShares(),
      loadTransactions(),
      loadHistory()
    ]);
    
    console.log('Shares page ready');
  } catch (error) {
    console.error('Failed to initialize shares page:', error);
  }
}

// Setup all event listeners
function setupEventListeners() {
  // Import buttons from top section
  const importTransactionsBtn = document.getElementById('importTransactionsBtn');
  const importHistoryBtn = document.getElementById('importHistoryBtn');
  const transactionsFileInput = document.getElementById('transactionsFileInput');
  const historyFileInput = document.getElementById('historyFileInput');

  if (importTransactionsBtn) {
    importTransactionsBtn.addEventListener('click', () => {
      if (transactionsFileInput) transactionsFileInput.click();
    });
  }

  if (importHistoryBtn) {
    importHistoryBtn.addEventListener('click', () => {
      if (historyFileInput) historyFileInput.click();
    });
  }

  if (transactionsFileInput) {
    transactionsFileInput.addEventListener('change', (e) => {
      handleImport(e, 'transactions');
    });
  }

  if (historyFileInput) {
    historyFileInput.addEventListener('change', (e) => {
      handleImport(e, 'history');
    });
  }
  
  // Shares table buttons
  const refreshSharesBtn = document.getElementById('refreshSharesBtn');
  const addShareBtn = document.getElementById('addShareBtn');
  const sharesSearchInput = document.getElementById('sharesSearchInput');
  const sharesFilterButtons = document.querySelectorAll('[data-shares-filter]');
  
  if (refreshSharesBtn) {
    refreshSharesBtn.addEventListener('click', () => {
      loadShares(1);
    });
  }
  
  if (addShareBtn) {
    addShareBtn.addEventListener('click', showAddShareDialog);
  }

  if (sharesSearchInput) {
    sharesSearchInput.addEventListener('input', () => {
      loadShares(1);
    });
  }

  if (sharesFilterButtons && sharesFilterButtons.length) {
    sharesFilterButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.getAttribute('data-shares-filter');
        setSharesFilter(filter);
      });
    });
  }
  
  // Transactions table buttons
  const refreshTransactionsBtn = document.getElementById('refreshTransactionsBtn');
  const addTransactionBtn = document.getElementById('addTransactionBtn');
  const importTransactionsTableBtn = document.getElementById('importTransactionsTableBtn');
  const transactionsSearchInput = document.getElementById('transactionsSearchInput');
  const historySearchInput = document.getElementById('historySearchInput');
  const historyFilterButtons = document.querySelectorAll('[data-history-filter]');
  const autoFillHistoryBtn = document.getElementById('autoFillHistoryBtn');
  
  if (refreshTransactionsBtn) {
    refreshTransactionsBtn.addEventListener('click', () => {
      loadTransactions(1);
    });
  }
  
  if (addTransactionBtn) {
    addTransactionBtn.addEventListener('click', showAddTransactionDialog);
  }
  
  if (importTransactionsTableBtn) {
    importTransactionsTableBtn.addEventListener('click', () => {
      if (transactionsFileInput) transactionsFileInput.click();
    });
  }

  if (transactionsSearchInput) {
    transactionsSearchInput.addEventListener('input', () => {
      loadTransactions(1);
    });
  }
  
  // History table buttons
  const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');
  const addHistoryBtn = document.getElementById('addHistoryBtn');
  const importHistoryTableBtn = document.getElementById('importHistoryTableBtn');
  
  if (refreshHistoryBtn) {
    refreshHistoryBtn.addEventListener('click', () => {
      loadHistory(1);
    });
  }
  
  if (addHistoryBtn) {
    addHistoryBtn.addEventListener('click', showAddHistoryDialog);
  }
  
  if (importHistoryTableBtn) {
    importHistoryTableBtn.addEventListener('click', () => {
      if (historyFileInput) historyFileInput.click();
    });
  }

  if (historySearchInput) {
    historySearchInput.addEventListener('input', () => {
      loadHistory(1);
    });
  }

  if (historyFilterButtons && historyFilterButtons.length) {
    historyFilterButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.getAttribute('data-history-filter');
        setHistoryFilter(filter);
      });
    });
  }

  if (autoFillHistoryBtn) {
    autoFillHistoryBtn.addEventListener('click', autoFillHistory);
  }

  // Sort controls for all tables
  setupSortControls();
}

function setupSortControls() {
  setupTableSort('sharesTable', sharesSort, () => loadShares(1));
  setupTableSort('transactionsTable', transactionsSort, () => loadTransactions(1));
  setupTableSort('historyTable', historySort, () => loadHistory(1));
}

function setupTableSort(tableId, sortState, reloadFn) {
  const headers = document.querySelectorAll(`#${tableId} thead th[data-sort]`);
  headers.forEach((th) => {
    th.classList.add('sortable');
    th.addEventListener('click', () => {
      const key = th.getAttribute('data-sort');
      if (!key) return;
      if (sortState.by === key) {
        sortState.dir = sortState.dir === 'asc' ? 'desc' : 'asc';
      } else {
        sortState.by = key;
        sortState.dir = 'asc';
      }
      applySortIndicators(tableId, sortState);
      reloadFn();
    });
  });

  applySortIndicators(tableId, sortState);
}

function applySortIndicators(tableId, sortState) {
  const headers = document.querySelectorAll(`#${tableId} thead th[data-sort]`);
  headers.forEach((th) => {
    th.classList.remove('sorted-asc', 'sorted-desc');
    const key = th.getAttribute('data-sort');
    if (key === sortState.by) {
      th.classList.add(sortState.dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
    }
  });
}

function setHistoryFilter(filter) {
  historyFilter = filter;
  document.querySelectorAll('[data-history-filter]').forEach(btn => {
    if (btn.getAttribute('data-history-filter') === filter) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  loadHistory(1);
}

// Load shares
async function loadShares(page = 1) {
  try {
    const searchInput = document.getElementById('sharesSearchInput');
    const searchParam = searchInput ? encodeURIComponent(searchInput.value.trim()) : '';
    const searchQuery = searchParam ? `&search=${searchParam}` : '';
    const filterQuery = sharesFilter ? `&filter=${encodeURIComponent(sharesFilter)}` : '';
    const sortQuery = sharesSort.by ? `&sort_by=${encodeURIComponent(sharesSort.by)}&sort_dir=${encodeURIComponent(sharesSort.dir)}` : '';
    const response = await authenticatedFetch(`${API_BASE}/shares/?page=${page}&page_size=${PAGE_SIZE}${searchQuery}${filterQuery}${sortQuery}`);
    const data = await response.json();
    
    const tbody = document.getElementById('sharesTbody');
    tbody.innerHTML = '';
    
    if (data.shares && data.shares.length > 0) {
      // Summen berechnen
      let sumPortfolioValue = 0;
      let sumInvestments = 0;
      let sumProceeds = 0;
      let sumNet = 0;
      let sumDividends = 0;
      
      data.shares.forEach(share => {
        sumPortfolioValue += share.portfolioValue || 0;
        sumInvestments += share.investments || 0;
        sumProceeds += share.proceeds || 0;
        sumNet += share.net || 0;
        sumDividends += share.dividends || 0;
        
        const row = document.createElement('tr');
        const saldoClass = share.net < 0 ? 'amount-negative' : (share.net > 0 ? 'amount-positive' : '');
        row.innerHTML = `
          <td>${share.name || ''}</td>
          <td>${share.wkn || ''}</td>
          <td>${share.isin || ''}</td>
          <td class="number">${formatShares(share.currentVolume)}</td>
          <td class="number">${formatCurrency(share.currentPrice)}</td>
          <td class="number" style="font-weight: bold;">${formatCurrency(share.portfolioValue)}</td>
          <td class="number">${formatCurrency(share.investments)}</td>
          <td class="number">${formatCurrency(share.proceeds)}</td>
          <td class="number ${saldoClass}" style="font-weight: bold;">${formatCurrency(share.net)}</td>
          <td class="number">${formatCurrency(share.dividends || 0)}</td>
          <td class="actions-cell">
            <div class="action-buttons">
              <button class="action-btn" data-action="edit-share" data-id="${share.id}">Bearbeiten</button>
              <button class="action-btn delete" data-action="delete-share" data-id="${share.id}">Löschen</button>
            </div>
          </td>
        `;
        tbody.appendChild(row);
      });
      
      // Summen-Zeile hinzufügen
      const sumRow = document.createElement('tr');
      const sumSaldoClass = sumNet < 0 ? 'amount-negative' : (sumNet > 0 ? 'amount-positive' : '');
      sumRow.style.borderTop = '2px solid var(--border-color)';
      sumRow.style.fontWeight = 'bold';
      sumRow.innerHTML = `
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td class="number">${formatCurrency(sumPortfolioValue)}</td>
        <td class="number">${formatCurrency(sumInvestments)}</td>
        <td class="number">${formatCurrency(sumProceeds)}</td>
        <td class="number ${sumSaldoClass}">${formatCurrency(sumNet)}</td>
        <td class="number">${formatCurrency(sumDividends)}</td>
        <td></td>
      `;
      tbody.appendChild(sumRow);
    } else {
      tbody.innerHTML = '<tr><td colspan="11" style="text-align: center;">Keine Wertpapiere gefunden</td></tr>';
    }
    
    updatePagination('sharesPagination', data.page, data.page_size, data.total, 'loadShares');

    // Attach actions
    tbody.querySelectorAll('button[data-action="edit-share"]').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-id');
        const share = data.shares.find(s => String(s.id) === String(id));
        if (share) {
          openEditShare(share);
        }
      };
    });
    tbody.querySelectorAll('button[data-action="delete-share"]').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-id');
        deleteShare(id);
      };
    });
    
  } catch (error) {
    console.error('Error loading shares:', error);
    showStatus('Fehler beim Laden der Wertpapiere', 'error');
  }
}

function setSharesFilter(filter) {
  sharesFilter = filter;
  document.querySelectorAll('[data-shares-filter]').forEach(btn => {
    if (btn.getAttribute('data-shares-filter') === filter) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  loadShares(1);
}

function formatShares(value) {
  if (value === null || value === undefined) return '';
  const num = Number(value);
  if (Number.isNaN(num)) return '';
  return num.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

// Load transactions
async function loadTransactions(page = 1) {
  try {
    const searchInput = document.getElementById('transactionsSearchInput');
    const searchParam = searchInput ? encodeURIComponent(searchInput.value.trim()) : '';
    const searchQuery = searchParam ? `&search=${searchParam}` : '';
    const sortQuery = transactionsSort.by ? `&sort_by=${encodeURIComponent(transactionsSort.by)}&sort_dir=${encodeURIComponent(transactionsSort.dir)}` : '';
    const response = await authenticatedFetch(`${API_BASE}/shares/transactions?page=${page}&page_size=${PAGE_SIZE}${searchQuery}${sortQuery}`);
    const data = await response.json();

    currentTransactionsPage = data.page || page || 1;
    const totalPages = data.page_size && data.total ? Math.max(1, Math.ceil(data.total / data.page_size)) : null;
    if (totalPages && currentTransactionsPage > totalPages) {
      return loadTransactions(totalPages);
    }
    
    const tbody = document.getElementById('transactionsTbody');
    tbody.innerHTML = '';
    
    if (data.transactions && data.transactions.length > 0) {
      data.transactions.forEach(tx => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td class="col-datum">${formatDateTime(tx.dateTransaction)}</td>
          <td class="col-isin">${tx.isin || ''}</td>
          <td class="col-wertpapier">${tx.share_name || ''}</td>
          <td class="col-betrag" style="text-align: right;">${tx.accountingEntry_amount ? formatCurrency(tx.accountingEntry_amount) : '-'}</td>
          <td class="col-anteile" style="text-align: right;">${parseFloat(tx.tradingVolume).toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
          <td class="col-aktionen actions-cell" style="text-align: center;">
            <div class="action-buttons">
              <button class="action-btn" data-action="edit-transaction" data-id="${tx.id}">Bearbeiten</button>
              <button class="action-btn delete" data-action="delete-transaction" data-id="${tx.id}">Löschen</button>
            </div>
          </td>
        `;
        tbody.appendChild(row);
      });
    } else {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Keine Transaktionen gefunden</td></tr>';
    }
    
    updatePagination('transactionsPagination', data.page, data.page_size, data.total, 'loadTransactions');

    tbody.querySelectorAll('button[data-action="edit-transaction"]').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-id');
        const tx = data.transactions.find(t => String(t.id) === String(id));
        if (tx) openEditTransaction(tx);
      };
    });
    tbody.querySelectorAll('button[data-action="delete-transaction"]').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-id');
        deleteTransaction(id);
      };
    });
    
  } catch (error) {
    console.error('Error loading transactions:', error);
    showStatus('Fehler beim Laden der Transaktionen', 'error');
  }
}

// Load history
async function loadHistory(page = 1) {
  try {
    const sortQuery = historySort.by ? `&sort_by=${encodeURIComponent(historySort.by)}&sort_dir=${encodeURIComponent(historySort.dir)}` : '';
    const searchInput = document.getElementById('historySearchInput');
    const searchParam = searchInput ? encodeURIComponent(searchInput.value.trim()) : '';
    const searchQuery = searchParam ? `&search=${searchParam}` : '';
    const filterQuery = historyFilter ? `&checked=${encodeURIComponent(historyFilter)}` : '';
    const response = await authenticatedFetch(`${API_BASE}/shares/history?page=${page}&page_size=${PAGE_SIZE}${sortQuery}${searchQuery}${filterQuery}`);
    const data = await response.json();
    
    const tbody = document.getElementById('historyTbody');
    tbody.innerHTML = '';
    
    if (data.history && data.history.length > 0) {
      data.history.forEach(item => {
        const row = document.createElement('tr');
          row.innerHTML = `
            <td class="col-datum">${formatDate(item.date)}</td>
            <td class="col-wertpapier">${item.share_name || ''}</td>
            <td class="col-betrag" style="text-align: right;">${formatCurrency(item.amount)}</td>
            <td class="col-geprueft" style="text-align: center;">${formatCheckedBadge(item.checked)}</td>
            <td class="col-aktionen actions-cell" style="text-align: center;">
              <div class="action-buttons">
                <button class="action-btn success" data-action="check-history" data-id="${item.id}">Geprüft</button>
                <button class="action-btn" data-action="edit-history" data-id="${item.id}">Bearbeiten</button>
                <button class="action-btn delete" data-action="delete-history" data-id="${item.id}">Löschen</button>
              </div>
            </td>
          `;
        tbody.appendChild(row);
      });
    } else {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Keine Historien gefunden</td></tr>';
    }
    
    updatePagination('historyPagination', data.page, data.page_size, data.total, 'loadHistory');

    tbody.querySelectorAll('button[data-action="edit-history"]').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-id');
        const entry = data.history.find(h => String(h.id) === String(id));
        if (entry) openEditHistory(entry);
      };
    });
    tbody.querySelectorAll('button[data-action="delete-history"]').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-id');
        deleteHistory(id);
      };
    });

    tbody.querySelectorAll('button[data-action="check-history"]').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-id');
        markHistoryChecked(id);
      };
    });
    
  } catch (error) {
    console.error('Error loading history:', error);
    showStatus('Fehler beim Laden der Historie', 'error');
  }
}

// Handle CSV import
async function handleImport(event, type) {
  const file = event.target.files[0];
  if (!file) return;
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    showStatus(`${type === 'transactions' ? 'Transaktionen' : 'Historische Daten'} werden importiert...`, 'info');
    
    const endpoint = type === 'transactions' 
      ? `${API_BASE}/shares/import/transactions`
      : `${API_BASE}/shares/import/history`;
    
    const response = await authenticatedFetch(endpoint, {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    if (response.ok && result.status === 'success') {
      const message = `${result.imported} Datensätze importiert, ${result.skipped} übersprungen${result.total_errors > 0 ? `, ${result.total_errors} Fehler` : ''}`;
      showStatus(message, 'success');
      
      // Show errors if any
      if (result.errors && result.errors.length > 0) {
        console.warn('Import errors:', result.errors);
        const errorList = result.errors.slice(0, 5).join('\n');
        alert(`Fehler beim Import (erste 5):\n${errorList}${result.total_errors > 5 ? '\n...' : ''}`);
      }
      
      // Reload data
      await loadShares(1);
      await loadTransactions(1);
      await loadHistory(1);
    } else {
      showStatus(`Import fehlgeschlagen: ${result.message || 'Unbekannter Fehler'}`, 'error');
    }
    
  } catch (error) {
    console.error('Import error:', error);
    showStatus('Fehler beim Import der Datei', 'error');
  }
  
  event.target.value = '';
}

function closeModal() {
  const modal = document.getElementById('formModal');
  if (modal) {
    modal.style.display = 'none';
  }
}

function showFormModal({ title, fields, onSubmit }) {
  const modal = document.getElementById('formModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const modalSaveBtn = document.getElementById('modalSaveBtn');
  const modalCancelBtn = document.getElementById('modalCancelBtn');
  const modalCloseBtn = document.getElementById('modalCloseBtn');

  if (!modal || !modalTitle || !modalBody || !modalSaveBtn) {
    console.error('Modal elements missing');
    return;
  }

  modalTitle.textContent = title;
  modalBody.innerHTML = '';

  fields.forEach((field) => {
    const group = document.createElement('div');
    group.className = 'form-group';

    const label = document.createElement('label');
    label.textContent = field.label;
    label.setAttribute('for', `modal-input-${field.id}`);

    let control;
    if (field.type === 'select') {
      control = document.createElement('select');
      control.className = 'input-sm';
      control.id = `modal-input-${field.id}`;
      if (field.options && Array.isArray(field.options)) {
        field.options.forEach(opt => {
          const optionEl = document.createElement('option');
          optionEl.value = opt.value;
          optionEl.textContent = opt.label;
          if (String(opt.value) === String(field.value || '')) {
            optionEl.selected = true;
          }
          control.appendChild(optionEl);
        });
      }
    } else if (field.type === 'checkbox') {
      control = document.createElement('input');
      control.id = `modal-input-${field.id}`;
      control.type = 'checkbox';
      control.className = 'input-sm';
      if (field.value) {
        control.checked = true;
      }
    } else {
      control = document.createElement('input');
      control.id = `modal-input-${field.id}`;
      control.type = field.type || 'text';
      control.className = 'input-sm';
      control.placeholder = field.placeholder || '';
      if (field.step) {
        control.step = field.step;
      }
      if (field.value !== undefined && field.value !== null) {
        control.value = field.value;
      }
    }

    if (field.required) {
      control.required = true;
    }

    group.appendChild(label);
    group.appendChild(control);
    modalBody.appendChild(group);
  });

  modalSaveBtn.onclick = async () => {
    const values = {};
    for (const field of fields) {
      const input = document.getElementById(`modal-input-${field.id}`);
      if (!input) continue;
      if (input.type === 'checkbox') {
        values[field.id] = input.checked;
      } else {
        values[field.id] = input.value.trim();
      }
      if (field.required && !values[field.id]) {
        input.focus();
        return;
      }
    }

    const shouldClose = await onSubmit(values);
    if (shouldClose !== false) {
      closeModal();
    }
  };

  if (modalCancelBtn) {
    modalCancelBtn.onclick = closeModal;
  }

  if (modalCloseBtn) {
    modalCloseBtn.onclick = closeModal;
  }

  modal.onclick = (event) => {
    if (event.target === modal) {
      closeModal();
    }
  };

  modal.style.display = 'block';
}

function normalizeDateInput(dateStr) {
  if (!dateStr) return null;
  const trimmed = dateStr.trim();
  if (trimmed.includes('-')) {
    return trimmed;
  }
  const parts = trimmed.split('.');
  if (parts.length !== 3) {
    return null;
  }
  const [day, month, year] = parts;
  return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
}

function parseNumberInput(valueStr) {
  const normalized = String(valueStr).replace(',', '.');
  const parsed = parseFloat(normalized);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatCurrency(value) {
  const num = parseFloat(value);
  if (Number.isNaN(num)) return '';
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(num);
}

function formatCheckedBadge(checked) {
  const isChecked = Boolean(checked);
  const cls = isChecked ? 'status-active' : 'status-inactive';
  const label = isChecked ? 'Ja' : 'Nein';
  return `<span class="${cls}">${label}</span>`;
}

async function ensureSharesOptions() {
  if (sharesOptions.length > 0) return sharesOptions;
  try {
    const response = await authenticatedFetch(`${API_BASE}/shares/?page=1&page_size=2000`);
    const data = await response.json();
    if (data && data.shares) {
      sharesOptions = data.shares.map(s => ({
        value: s.isin,
        label: `${s.name || s.isin} (${s.isin})`,
        wkn: s.wkn,
        id: s.id
      }));
    }
  } catch (error) {
    console.error('Failed to load share options', error);
  }
  return sharesOptions;
}

// (definitions moved further down to avoid duplication)

// Show add share dialog
function showAddShareDialog() {
  showFormModal({
    title: 'Wertpapier hinzufügen',
    fields: [
      { id: 'isin', label: 'ISIN (verpflichtend)', type: 'text', placeholder: 'z.B. DE000ETFL235', required: true },
      { id: 'name', label: 'Name (optional)', type: 'text', placeholder: 'z.B. ETF Musterfonds', required: false },
      { id: 'wkn', label: 'WKN (optional)', type: 'text', placeholder: 'z.B. ETFL23', required: false }
    ],
    onSubmit: async (values) => {
      if (!values.isin || values.isin.trim() === '') {
        alert('ISIN ist verpflichtend');
        return false;
      }
      return await addShare(values.name, values.wkn, values.isin);
    }
  });
}

// Show add transaction dialog
async function showAddTransactionDialog() {
  const options = await ensureSharesOptions();
  showFormModal({
    title: 'Wertpapiertransaktion hinzufügen',
    fields: [
      { id: 'isin', label: 'Wertpapier', type: 'select', required: true, options: options },
      { id: 'date', label: 'Datum', type: 'date', required: true },
      { id: 'time', label: 'Uhrzeit', type: 'time', required: false },
      { id: 'volume', label: 'Anteile (negativ = Verkauf)', type: 'number', step: 'any', required: true },
      { id: 'accountingEntry', label: 'Buchungseintrag', type: 'select', required: false, options: [{ label: 'Lade...', value: '' }] },
      { id: 'accountingDateFilter', label: 'Buchungen nach Datum (±7 Tage) filtern', type: 'checkbox', value: true }
    ],
    onSubmit: async (values) => {
      return await addTransaction(values.isin, values.date, values.time, values.volume, values.accountingEntry);
    }
  });

  const volumeInput = document.getElementById('modal-input-volume');
  const accountingSelect = document.getElementById('modal-input-accountingEntry');
  const dateInput = document.getElementById('modal-input-date');
  const dateFilterCheckbox = document.getElementById('modal-input-accountingDateFilter');

  const refreshEntries = async () => {
    const txType = deriveTxType(volumeInput.value);
    const txDate = dateInput?.value;
    const useDateFilter = dateFilterCheckbox ? dateFilterCheckbox.checked : false;
    const entries = await fetchAccountingEntries({ type: txType || undefined, date: txDate, useDateFilter });
    setAccountingSelectOptions(accountingSelect, entries, null);
  };

  if (volumeInput) {
    volumeInput.addEventListener('input', refreshEntries);
  }
  if (dateInput) {
    dateInput.addEventListener('change', refreshEntries);
  }
  if (dateFilterCheckbox) {
    dateFilterCheckbox.addEventListener('change', refreshEntries);
  }

  await refreshEntries();
}

// Show add history dialog
async function showAddHistoryDialog() {
  const options = await ensureSharesOptions();
  showFormModal({
    title: 'Historischen Kurs hinzufügen',
    fields: [
      { id: 'isin', label: 'Wertpapier', type: 'select', required: true, options: options },
      { id: 'date', label: 'Datum', type: 'date', required: true },
      { id: 'amount', label: 'Kurs/Betrag', type: 'number', step: 'any', required: true }
    ],
    onSubmit: async (values) => {
      return await addHistory(values.isin, values.date, values.amount);
    }
  });
}

// Add new share via API
async function addShare(name, wkn, isin) {
  try {
    const response = await authenticatedFetch(`${API_BASE}/shares/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        isin: isin || '',
        name: name || '',
        wkn: wkn || ''
      })
    });
    
    const result = await response.json();
    
    if (response.ok && result.status === 'success') {
      showStatus('Wertpapier erfolgreich hinzugefügt', 'success');
      await loadShares(1);
      sharesOptions = []; // force reload for dropdowns
      return true;
    } else {
      showStatus(`Fehler: ${result.message || 'Konnte Wertpapier nicht hinzufügen'}`, 'error');
      return false;
    }
  } catch (error) {
    console.error('Error adding share:', error);
    showStatus('Fehler beim Hinzufügen des Wertpapiers', 'error');
    return false;
  }
}

async function updateShare(id, name, wkn, isin) {
  try {
    const response = await authenticatedFetch(`${API_BASE}/shares/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({ isin: isin || '', name: name || '', wkn: wkn || '' })
    });
    const result = await response.json();
    if (response.ok && result.status === 'success') {
      showStatus('Wertpapier aktualisiert', 'success');
      sharesOptions = [];
      await loadShares(1);
      return true;
    }
    showStatus(`Fehler: ${result.message || 'Konnte Wertpapier nicht aktualisieren'}`, 'error');
    return false;
  } catch (error) {
    console.error('Error updating share:', error);
    showStatus('Fehler beim Aktualisieren des Wertpapiers', 'error');
    return false;
  }
}

async function deleteShare(id) {
  const confirmed = confirm('Wertpapier wirklich löschen?');
  if (!confirmed) return;
  try {
    const response = await authenticatedFetch(`${API_BASE}/shares/${id}`, { method: 'DELETE' });
    const result = await response.json();
    if (response.ok && result.status === 'success') {
      showStatus('Wertpapier gelöscht', 'success');
      sharesOptions = [];
      await loadShares(1);
      return true;
    }
    showStatus(`Fehler: ${result.message || 'Konnte Wertpapier nicht löschen'}`, 'error');
  } catch (error) {
    console.error('Error deleting share:', error);
    showStatus('Fehler beim Löschen des Wertpapiers', 'error');
  }
  return false;
}

// Add new transaction via API
async function addTransaction(isin, dateStr, timeStr, volumeStr, accountingEntryId = null) {
  try {
    const dateISO = normalizeDateInput(dateStr);
    if (!dateISO) {
      showStatus('Ungültiges Datumsformat. Verwenden Sie DD.MM.YYYY oder wählen Sie ein Datum aus.', 'error');
      return false;
    }

    // Combine date and time into ISO datetime string
    let dateTimeISO = dateISO;
    if (timeStr && timeStr.trim() !== '') {
      // timeStr is in format HH:MM from time input
      dateTimeISO = `${dateISO}T${timeStr}:00`;
    } else {
      // Default time to 00:00:00 if no time provided
      dateTimeISO = `${dateISO}T00:00:00`;
    }

    const volume = parseNumberInput(volumeStr);
    if (volume === null) {
      showStatus('Ungültige Anzahl Anteile', 'error');
      return false;
    }
    
    const params = new URLSearchParams({
      isin: isin,
      dateTransaction: dateTimeISO,
      tradingVolume: volume
    });
    
    if (accountingEntryId) {
      params.append('accountingEntryId', accountingEntryId);
    }
    
    const response = await authenticatedFetch(`${API_BASE}/shares/transactions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params
    });
    
    const result = await response.json();
    
    if (response.ok && result.status === 'success') {
      showStatus('Transaktion erfolgreich hinzugefügt', 'success');
      await loadTransactions(currentTransactionsPage);
      return true;
    } else {
      showStatus(`Fehler: ${result.message || 'Konnte Transaktion nicht hinzufügen'}`, 'error');
      return false;
    }
  } catch (error) {
    console.error('Error adding transaction:', error);
    showStatus('Fehler beim Hinzufügen der Transaktion', 'error');
    return false;
  }
}

async function updateTransaction(id, isin, dateStr, timeStr, volumeStr, accountingEntryId = null) {
  try {
    const dateISO = normalizeDateInput(dateStr);
    if (!dateISO) {
      showStatus('Ungültiges Datumsformat. Verwenden Sie DD.MM.YYYY oder wählen Sie ein Datum aus.', 'error');
      return false;
    }
    
    // Combine date and time into ISO datetime string
    let dateTimeISO = dateISO;
    if (timeStr && timeStr.trim() !== '') {
      // timeStr is in format HH:MM from time input
      dateTimeISO = `${dateISO}T${timeStr}:00`;
    } else {
      // Default time to 00:00:00 if no time provided
      dateTimeISO = `${dateISO}T00:00:00`;
    }
    
    const volume = parseNumberInput(volumeStr);
    if (volume === null) {
      showStatus('Ungültige Anzahl Anteile', 'error');
      return false;
    }

    const params = new URLSearchParams({
      isin,
      dateTransaction: dateTimeISO,
      tradingVolume: volume
    });
    
    if (accountingEntryId) {
      params.append('accountingEntryId', accountingEntryId);
    }

    const response = await authenticatedFetch(`${API_BASE}/shares/transactions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params
    });
    const result = await response.json();
    if (response.ok && result.status === 'success') {
      showStatus('Transaktion aktualisiert', 'success');
      await loadTransactions(currentTransactionsPage);
      return true;
    }
    showStatus(`Fehler: ${result.message || 'Konnte Transaktion nicht aktualisieren'}`, 'error');
    return false;
  } catch (error) {
    console.error('Error updating transaction:', error);
    showStatus('Fehler beim Aktualisieren der Transaktion', 'error');
    return false;
  }
}

async function deleteTransaction(id) {
  if (!confirm('Transaktion wirklich löschen?')) return false;
  try {
    const response = await authenticatedFetch(`${API_BASE}/shares/transactions/${id}`, { method: 'DELETE' });
    const result = await response.json();
    if (response.ok && result.status === 'success') {
      showStatus('Transaktion gelöscht', 'success');
      await loadTransactions(currentTransactionsPage);
      return true;
    }
    showStatus(`Fehler: ${result.message || 'Konnte Transaktion nicht löschen'}`, 'error');
  } catch (error) {
    console.error('Error deleting transaction:', error);
    showStatus('Fehler beim Löschen der Transaktion', 'error');
  }
  return false;
}

// Add new history entry via API
async function addHistory(isin, dateStr, amountStr) {
  try {
    const dateISO = normalizeDateInput(dateStr);
    if (!dateISO) {
      showStatus('Ungültiges Datumsformat. Verwenden Sie DD.MM.YYYY oder wählen Sie ein Datum aus.', 'error');
      return false;
    }

    const amount = parseNumberInput(amountStr);
    if (amount === null) {
      showStatus('Ungültiger Betrag', 'error');
      return false;
    }
    
    const response = await authenticatedFetch(`${API_BASE}/shares/history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        isin: isin,
        date: dateISO,
        amount: amount
      })
    });
    
    const result = await response.json();
    
    if (response.ok && result.status === 'success') {
      showStatus('Historischer Datensatz erfolgreich hinzugefügt', 'success');
      await loadHistory(1);
      return true;
    } else {
      showStatus(`Fehler: ${result.message || 'Konnte Datensatz nicht hinzufügen'}`, 'error');
      return false;
    }
  } catch (error) {
    console.error('Error adding history:', error);
    showStatus('Fehler beim Hinzufügen des historischen Datensatzes', 'error');
    return false;
  }
}

async function updateHistory(id, isin, dateStr, amountStr, checkedVal) {
  try {
    const dateISO = normalizeDateInput(dateStr);
    if (!dateISO) {
      showStatus('Ungültiges Datumsformat. Verwenden Sie DD.MM.YYYY oder wählen Sie ein Datum aus.', 'error');
      return false;
    }
    const amount = parseNumberInput(amountStr);
    if (amount === null) {
      showStatus('Ungültiger Betrag', 'error');
      return false;
    }

    const response = await authenticatedFetch(`${API_BASE}/shares/history/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        isin,
        date: dateISO,
        amount,
        checked: checkedVal ? 'true' : 'false'
      })
    });
    const result = await response.json();
    if (response.ok && result.status === 'success') {
      showStatus('Historischer Datensatz aktualisiert', 'success');
      await loadHistory(1);
      return true;
    }
    showStatus(`Fehler: ${result.message || 'Konnte Datensatz nicht aktualisieren'}`, 'error');
    return false;
  } catch (error) {
    console.error('Error updating history:', error);
    showStatus('Fehler beim Aktualisieren des Datensatzes', 'error');
    return false;
  }
}

function openEditShare(share) {
  showFormModal({
    title: 'Wertpapier bearbeiten',
    fields: [
      { id: 'name', label: 'Name', type: 'text', required: false, value: share.name || '' },
      { id: 'isin', label: 'ISIN (verpflichtend)', type: 'text', required: true, value: share.isin || '' },
      { id: 'wkn', label: 'WKN (optional)', type: 'text', required: false, value: share.wkn || '' }
    ],
    onSubmit: async (values) => {
      if (!values.isin || values.isin.trim() === '') {
        alert('ISIN ist verpflichtend');
        return false;
      }
      return await updateShare(share.id, values.name, values.wkn, values.isin);
    }
  });
}

async function openEditTransaction(tx) {
  const options = await ensureSharesOptions();
  
  // Extract date and time from dateTransaction (format: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS)
  let dateValue = '';
  let timeValue = '';
  if (tx.dateTransaction) {
    // Handle both formats: ISO 8601 (T separator) and MySQL format (space separator)
    const dateTimeStr = tx.dateTransaction.replace(' ', 'T');
    const parts = dateTimeStr.split('T');
    dateValue = parts[0];
    if (parts[1]) {
      timeValue = parts[1].substring(0, 5); // HH:MM format
    }
  }
  
  showFormModal({
    title: 'Transaktion bearbeiten',
    fields: [
      { id: 'isin', label: 'Wertpapier', type: 'select', required: true, options: options, value: tx.isin },
      { id: 'date', label: 'Datum', type: 'date', required: true, value: dateValue },
      { id: 'time', label: 'Uhrzeit', type: 'time', required: false, value: timeValue },
      { id: 'volume', label: 'Anteile (negativ = Verkauf)', type: 'number', step: 'any', required: true, value: tx.tradingVolume },
      { id: 'accountingEntry', label: 'Buchungseintrag', type: 'select', required: false, options: [{ label: 'Lade...', value: '' }], value: tx.accountingEntry || '' },
      { id: 'accountingDateFilter', label: 'Buchungen nach Datum (±7 Tage) filtern', type: 'checkbox', value: true }
    ],
    onSubmit: async (values) => {
      return await updateTransaction(tx.id, values.isin, values.date, values.time, values.volume, values.accountingEntry);
    }
  });

  const volumeInput = document.getElementById('modal-input-volume');
  const accountingSelect = document.getElementById('modal-input-accountingEntry');
  const dateInput = document.getElementById('modal-input-date');
  const dateFilterCheckbox = document.getElementById('modal-input-accountingDateFilter');

  const refreshEntries = async () => {
    const txType = deriveTxType(volumeInput.value);
    const txDate = dateInput?.value;
    const useDateFilter = dateFilterCheckbox ? dateFilterCheckbox.checked : false;
    let entries = await fetchAccountingEntries({ type: txType || undefined, date: txDate, useDateFilter });
    
    // Add current accounting entry to the list if it exists and is not already in the list
    if (tx.accountingEntry && !entries.some(e => e.id === tx.accountingEntry)) {
      // Fetch the current accounting entry details
      try {
        const res = await authenticatedFetch(`${API_BASE}/shares/accounting-entries/${tx.accountingEntry}`);
        const data = await res.json();
        if (data.entry) {
          entries.unshift(data.entry);
        }
      } catch (error) {
        console.error('Error fetching current accounting entry:', error);
      }
    }
    setAccountingSelectOptions(accountingSelect, entries, tx.accountingEntry || null);
  };

  if (volumeInput) {
    volumeInput.addEventListener('input', refreshEntries);
  }
  if (dateInput) {
    dateInput.addEventListener('change', refreshEntries);
  }
  if (dateFilterCheckbox) {
    dateFilterCheckbox.addEventListener('change', refreshEntries);
  }

  await refreshEntries();
}

async function openEditHistory(entry) {
  const options = await ensureSharesOptions();
  showFormModal({
    title: 'Historischen Kurs bearbeiten',
    fields: [
      { id: 'isin', label: 'Wertpapier', type: 'select', required: true, options: options, value: entry.isin },
      { id: 'date', label: 'Datum', type: 'date', required: true, value: entry.date?.slice(0, 10) },
      { id: 'amount', label: 'Kurs/Betrag', type: 'number', step: 'any', required: true, value: entry.amount },
      { id: 'checked', label: 'Geprüft', type: 'checkbox', value: entry.checked }
    ],
    onSubmit: async (values) => {
      return await updateHistory(entry.id, values.isin, values.date, values.amount, Boolean(values.checked));
    }
  });
}

// Helper functions for accounting entries
function deriveTxType(volumeValue) {
  const volume = parseFloat(volumeValue);
  if (Number.isNaN(volume)) return null;
  if (volume > 0) return 'buy';
  if (volume < 0) return 'sell';
  return 'dividend';  // volume === 0
}

async function fetchAccountingEntries({ type = null, date = null, useDateFilter = false } = {}) {
  try {
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (useDateFilter && date) params.append('date', date);
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await authenticatedFetch(`${API_BASE}/shares/accounting-entries${query}`);
    const data = await res.json();
    return data.entries || [];
  } catch (error) {
    console.error('Error fetching accounting entries:', error);
    return [];
  }
}

function setAccountingSelectOptions(selectEl, entries, selectedId = null) {
  if (!selectEl) return;
  selectEl.innerHTML = '<option value="">-- Keine Buchung --</option>';
  
  entries.forEach(entry => {
    const opt = document.createElement('option');
    opt.value = entry.id;
    opt.textContent = entry.display || `${entry.id}: ${entry.amount}€`;
    if (selectedId && String(entry.id) === String(selectedId)) {
      opt.selected = true;
    }
    selectEl.appendChild(opt);
  });
}

async function deleteHistory(id) {
  if (!confirm('Historischen Datensatz wirklich löschen?')) return false;
  try {
    const response = await authenticatedFetch(`${API_BASE}/shares/history/${id}`, { method: 'DELETE' });
    const result = await response.json();
    if (response.ok && result.status === 'success') {
      showStatus('Historischer Datensatz gelöscht', 'success');
      await loadHistory(1);
      return true;
    }
    showStatus(`Fehler: ${result.message || 'Konnte Datensatz nicht löschen'}`, 'error');
  } catch (error) {
    console.error('Error deleting history:', error);
    showStatus('Fehler beim Löschen des Datensatzes', 'error');
  }
  return false;
}

async function autoFillHistory() {
  try {
    showStatus('Fehlende Monatsendstände werden ergänzt...', 'info');
    const response = await authenticatedFetch(`${API_BASE}/shares/history/auto-fill`, { method: 'POST' });
    const result = await response.json();
    if (response.ok && result.status === 'success') {
      showStatus(`Erstellt: ${result.created}, Übersprungen: ${result.skipped}`, 'success');
      await loadHistory(1);
      return true;
    }
    showStatus(`Fehler: ${result.message || 'Automatisches Ergänzen fehlgeschlagen'}`, 'error');
  } catch (error) {
    console.error('Error auto-filling history:', error);
    showStatus('Fehler beim automatischen Ergänzen der Historie', 'error');
  }
  return false;
}

async function markHistoryChecked(id) {
  try {
    const response = await authenticatedFetch(`${API_BASE}/shares/history/${id}/checked`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ checked: 'true' })
    });
    const result = await response.json();
    if (response.ok && result.status === 'success') {
      showStatus('Eintrag als geprüft markiert', 'success');
      await loadHistory(1);
      return true;
    }
    showStatus(`Fehler: ${result.message || 'Konnte Eintrag nicht markieren'}`, 'error');
  } catch (error) {
    console.error('Error marking history checked:', error);
    showStatus('Fehler beim Markieren des Eintrags', 'error');
  }
  return false;
}

// Update pagination buttons
function updatePagination(elementId, currentPage, pageSize, total, loadFunctionName) {
  const totalPages = Math.ceil(total / pageSize);
  const paginationDiv = document.getElementById(elementId);
  paginationDiv.innerHTML = '';
  
  if (totalPages <= 1) {
    paginationDiv.innerHTML = `<span class="pagination-info">Total: ${total} Einträge</span>`;
    return;
  }
  
  if (currentPage > 1) {
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '← Vorherige';
    prevBtn.className = 'pagination-btn';
    prevBtn.onclick = () => window[loadFunctionName](currentPage - 1);
    paginationDiv.appendChild(prevBtn);
  }
  
  const info = document.createElement('span');
  info.className = 'pagination-info';
  info.textContent = `Seite ${currentPage} von ${totalPages} (${total} Einträge)`;
  paginationDiv.appendChild(info);
  
  if (currentPage < totalPages) {
    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Nächste →';
    nextBtn.className = 'pagination-btn';
    nextBtn.onclick = () => window[loadFunctionName](currentPage + 1);
    paginationDiv.appendChild(nextBtn);
  }
}

// Show status message
function showStatus(message, type = 'info') {
  const statusDiv = document.getElementById('importStatus');
  if (!statusDiv) return;
  
  statusDiv.textContent = message;
  statusDiv.className = `status-message status-${type}`;
  statusDiv.style.display = 'block';
  
  if (type === 'success') {
    setTimeout(() => {
      statusDiv.style.display = 'none';
    }, 5000);
  }
}

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSharesPage);
} else {
  setTimeout(initSharesPage, 100);
}
