// Import transactions page logic
let currentPage = 1;
let searchTerm = '';
let currentFilter = 'unchecked';
let selectedTransactionId = null;
let detailsEntries = [];
let allCategories = [];
let importAccounts = [];
let currentTransactionAmount = 0;
let currentSortColumn = null;
let currentSortDirection = 'asc';
let cachedTransactions = [];
let lastDisplayedTransactions = [];
let selectedTransactionIds = new Set();

async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/categories/list`);
    const data = await response.json();
    allCategories = data.categories || [];
    console.log('Categories loaded:', allCategories.length, allCategories);
  } catch (error) {
    console.error('Failed to load categories:', error);
    allCategories = [];
  }
}

function setFilter(filter) {
  currentFilter = filter;
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filter);
  });
  loadTransactions(1);
}

function formatCurrency(amount) {
  const num = parseFloat(amount);
  return `€ ${num.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, ' ')}`;
}

function truncateText(text, maxLength = 50) {
  if (!text) return '-';
  return text.length > maxLength ? text.substring(0, maxLength - 3) + '...' : text;
}

function sortTransactions(column) {
  if (currentSortColumn === column) {
    currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    currentSortColumn = column;
    currentSortDirection = 'asc';
  }

  const sorted = [...cachedTransactions].sort((a, b) => {
    let valA, valB;
    
    switch(column) {
      case 'date':
        valA = new Date(a.dateValue);
        valB = new Date(b.dateValue);
        break;
      case 'description':
        valA = (a.description || '').toLowerCase();
        valB = (b.description || '').toLowerCase();
        break;
      case 'amount':
        valA = parseFloat(a.amount) || 0;
        valB = parseFloat(b.amount) || 0;
        break;
      case 'account':
        valA = (a.account_name || '').toLowerCase();
        valB = (b.account_name || '').toLowerCase();
        break;
      case 'entries':
        valA = a.entries.length;
        valB = b.entries.length;
        break;
      default:
        return 0;
    }

    if (valA < valB) return currentSortDirection === 'asc' ? -1 : 1;
    if (valA > valB) return currentSortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  displayTransactions(sorted);
  updateSortIndicators();
}

function updateSortIndicators() {
  document.querySelectorAll('.transactions-table th').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
  });
  
  if (currentSortColumn) {
    const columnMap = {
      'date': 0,
      'description': 1,
      'amount': 2,
      'account': 3,
      'entries': 4
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

function toDateInputValue(value) {
  const d = value ? new Date(value) : new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

async function loadTransactions(page = 1) {
  currentPage = page;
  // Get search term from input only if a new search is being made
  const searchInput = document.getElementById('searchInput');
  const inputSearchTerm = searchInput ? searchInput.value : '';
  
  // Only reset to page 1 if search term changed
  if (inputSearchTerm !== searchTerm) {
    searchTerm = inputSearchTerm;
    currentPage = page = 1;
  }

  const loadingIndicator = document.getElementById('loadingIndicator');
  const transactionsTable = document.getElementById('transactionsTable');
  const errorMessage = document.getElementById('errorMessage');

  if (loadingIndicator) loadingIndicator.style.display = 'block';
  if (transactionsTable) transactionsTable.style.display = 'none';
  if (errorMessage) errorMessage.style.display = 'none';

  try {
    const params = new URLSearchParams({ page, page_size: 20 });
    if (searchTerm) params.append('search', searchTerm);
    if (currentFilter && currentFilter !== 'all') params.append('filter', currentFilter);

    const response = await fetch(`${API_BASE}/transactions/?${params}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const data = await response.json();
    const totalPages = Math.ceil(data.total / data.page_size);
    console.log(`DEBUG PAGINATION: total=${data.total}, page_size=${data.page_size}, totalPages=${totalPages}, transactions.length=${data.transactions.length}, searchTerm="${searchTerm}", filter="${currentFilter}"`);
    displayTransactions(data.transactions, true);
    displayPagination(data.page, totalPages);

    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (transactionsTable) transactionsTable.style.display = 'table';

    const stillVisible = data.transactions.some(t => t.id === selectedTransactionId);
    if (!stillVisible) clearDetails();
  } catch (error) {
    console.error('Error loading transactions:', error);
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (errorMessage) {
      errorMessage.textContent = `Fehler beim Laden der Transaktionen: ${error.message}`;
      errorMessage.style.display = 'block';
    }
  }
}

function displayTransactions(transactions, isInitialLoad = false) {
  const tbody = document.getElementById('transactionsBody');
  if (!tbody) return;
  lastDisplayedTransactions = transactions || [];
  
  if (isInitialLoad) {
    cachedTransactions = transactions;
    if (currentSortColumn) {
      sortTransactions(currentSortColumn);
      return;
    }
  }
  
  tbody.innerHTML = '';

  transactions.forEach(transaction => {
    const row = document.createElement('tr');
    row.dataset.id = String(transaction.id);
    if (transaction.id === selectedTransactionId) row.classList.add('selected');
    const amountClass = transaction.amount < 0 ? 'amount-negative' : 'amount-positive';
    const isChecked = selectedTransactionIds.has(transaction.id);
    row.innerHTML = `
      <td style="text-align: center;" onclick="event.stopPropagation();">
        <input type="checkbox" class="transaction-checkbox" data-id="${transaction.id}" ${isChecked ? 'checked' : ''} onchange="toggleTransactionSelection(${transaction.id}, this.checked)">
      </td>
      <td>${formatDate(transaction.dateValue)}</td>
      <td>${truncateText(transaction.description, 60)}</td>
      <td class="${amountClass}" style="text-align: right;">${formatCurrency(transaction.amount)}</td>
      <td>${transaction.account_name}</td>
      <td style="text-align: center;">${transaction.entries.length}</td>
    `;
    row.onclick = () => showTransactionDetails(transaction.id);
    tbody.appendChild(row);
  });
  
  updateSelectAllCheckbox();
  updateSelectedCount();
}

function toggleTransactionSelection(id, checked) {
  if (checked) {
    selectedTransactionIds.add(id);
  } else {
    selectedTransactionIds.delete(id);
  }
  updateSelectAllCheckbox();
  updateSelectedCount();
}

function toggleSelectAll(checked) {
  selectedTransactionIds.clear();
  if (checked) {
    lastDisplayedTransactions.forEach(t => selectedTransactionIds.add(t.id));
  }
  document.querySelectorAll('.transaction-checkbox').forEach(cb => {
    cb.checked = checked;
  });
  updateSelectedCount();
}

function updateSelectAllCheckbox() {
  const selectAllCheckbox = document.getElementById('selectAllCheckbox');
  if (!selectAllCheckbox) return;
  
  const displayedIds = lastDisplayedTransactions.map(t => t.id);
  const allSelected = displayedIds.length > 0 && displayedIds.every(id => selectedTransactionIds.has(id));
  const someSelected = displayedIds.some(id => selectedTransactionIds.has(id));
  
  selectAllCheckbox.checked = allSelected;
  selectAllCheckbox.indeterminate = someSelected && !allSelected;
}

function updateSelectedCount() {
  const countSpan = document.getElementById('selectedCount');
  const button = document.getElementById('bulkCheckButton');
  const count = selectedTransactionIds.size;
  
  if (countSpan) countSpan.textContent = count;
  if (button) button.disabled = count === 0;
}

async function markSelectedChecked() {
  const button = document.getElementById('bulkCheckButton');
  const status = document.getElementById('bulkStatus');
  const ids = Array.from(selectedTransactionIds);

  if (!ids.length) {
    alert('Keine Transaktionen ausgewählt.');
    return;
  }

  if (button) {
    button.disabled = true;
  }
  if (status) {
    status.style.display = 'none';
    status.textContent = '';
  }

  try {
    const response = await fetch(`${API_BASE}/transactions/mark-checked`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transaction_ids: ids, checked: true })
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    const result = await response.json();
    if (status) {
      status.textContent = `✓ ${result.updated_entries} Einträge als geprüft markiert`;
      status.style.color = 'var(--color-amount-positive)';
      status.style.display = 'block';
    }
    selectedTransactionIds.clear();
    updateSelectedCount();
    await loadTransactions(currentPage);
  } catch (error) {
    console.error('Error marking selected transactions checked:', error);
    if (status) {
      status.textContent = `✗ Fehler beim Markieren: ${error.message}`;
      status.style.color = 'var(--color-amount-negative)';
      status.style.display = 'block';
    }
    alert(`Fehler beim Markieren: ${error.message}`);
  } finally {
    if (button) button.disabled = selectedTransactionIds.size === 0;
  }
}

function displayPagination(currentPageNum, totalPages) {
  const pagination = document.getElementById('pagination');
  if (!pagination) return;
  pagination.innerHTML = '';

  const prevBtn = document.createElement('button');
  prevBtn.textContent = '← Vorherige';
  prevBtn.disabled = currentPageNum === 1;
  prevBtn.onclick = () => loadTransactions(currentPageNum - 1);
  pagination.appendChild(prevBtn);

  const pageInfo = document.createElement('span');
  pageInfo.textContent = `Seite ${currentPageNum} von ${totalPages}`;
  pageInfo.style.padding = '8px 16px';
  pagination.appendChild(pageInfo);

  const nextBtn = document.createElement('button');
  nextBtn.textContent = 'Nächste →';
  nextBtn.disabled = currentPageNum === totalPages;
  nextBtn.onclick = () => loadTransactions(currentPageNum + 1);
  pagination.appendChild(nextBtn);
}

function clearDetails() {
  selectedTransactionId = null;
  currentTransactionAmount = 0;
  const detailsPanel = document.getElementById('detailsPanel');
  const statusBar = document.getElementById('detailsStatusBar');
  if (detailsPanel) detailsPanel.style.display = 'none';
  const detailsBody = document.getElementById('detailsBody');
  const detailsInfo = document.getElementById('detailsInfo');
  if (detailsBody) detailsBody.innerHTML = '';
  if (detailsInfo) detailsInfo.innerHTML = '';
  if (statusBar) {
    statusBar.style.display = 'none';
    statusBar.textContent = '';
  }
  document.querySelectorAll('#transactionsBody tr.selected').forEach(tr => tr.classList.remove('selected'));
  detailsEntries = [];
}

function resetSearch() {
  const input = document.getElementById('searchInput');
  if (input) input.value = '';
  setFilter('all');
  clearDetails();
}

async function showTransactionDetails(transactionId) {
  try {
    const response = await fetch(`${API_BASE}/transactions/${transactionId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const tx = await response.json();
    selectedTransactionId = tx.id;
    currentTransactionAmount = parseFloat(tx.amount) || 0;

    document.querySelectorAll('#transactionsBody tr').forEach(tr => {
      if (tr.dataset.id === String(tx.id)) {
        tr.classList.add('selected');
        // Scroll nur wenn nötig und ohne die ganze Seite zu bewegen
        tr.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
      }
      else tr.classList.remove('selected');
    });

    const amountCls = tx.amount < 0 ? 'amount-negative' : 'amount-positive';
    const info = [
      { label: 'Transaktionsbetrag', value: `<span class="${amountCls}">${formatCurrency(tx.amount)}</span>` },
      { label: 'Konto', value: tx.account_name || '-' },
      { label: 'Datum', value: formatDate(tx.dateValue) },
      { label: 'Beschreibung', value: tx.description || '-' },
      { label: 'Empfänger', value: tx.recipientApplicant || '-' },
      { label: 'IBAN (Empfänger)', value: tx.iban || '-' },
      { label: 'Import-ID', value: tx.id }
    ];
    const detailsInfo = document.getElementById('detailsInfo');
    detailsInfo.innerHTML = info.map(i => `
      <div class="info-row">
        <span class="info-label">${i.label}</span>
        <span>${i.value}</span>
      </div>
    `).join('');

    detailsEntries = (tx.entries || []).map(entry => ({
      id: entry.id,
      dateImport: entry.dateImport,
      category_name: entry.category_name || '',
      amount: entry.amount || 0,
      accountingPlanned: entry.accountingPlanned ?? false,
      checked: entry.checked ?? false
    }));
    
    // Debug: Log entries to console
    console.log('Loaded entries:', detailsEntries);
    
    renderEntries();
    const detailsPanel = document.getElementById('detailsPanel');
    detailsPanel.style.display = 'block';
  } catch (error) {
    console.error('Error loading transaction details:', error);
  }
}

function updateEntriesSumDisplay() {
  const sumDisplay = document.getElementById('entriesSumDisplay');
  if (!sumDisplay) return;

  let sumEntries = 0;
  for (let i = 0; i < detailsEntries.length; i++) {
    sumEntries += parseFloat(detailsEntries[i].amount) || 0;
  }
  
  const difference = Math.abs(currentTransactionAmount - sumEntries);
  const isMatching = difference < 0.01; // Allow for floating-point rounding errors
  
  if (isMatching) {
    sumDisplay.textContent = `✓ Summe: ${formatCurrency(sumEntries)} / Transaktion: ${formatCurrency(currentTransactionAmount)}`;
    sumDisplay.style.color = 'var(--color-amount-positive)';
  } else {
    sumDisplay.textContent = `✗ Summe: ${formatCurrency(sumEntries)} / Transaktion: ${formatCurrency(currentTransactionAmount)} (Differenz: ${formatCurrency(difference)})`;
    sumDisplay.style.color = 'var(--color-amount-negative)';
  }
}

function renderEntries() {
  const tbody = document.getElementById('detailsBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  console.log('renderEntries - All categories:', allCategories);
  console.log('renderEntries - Entries to render:', detailsEntries);

  // Sort entries by ID (ascending) - keeping original order if no ID
  const sortedEntries = [...detailsEntries].sort((a, b) => {
    if (a.id && b.id) return a.id - b.id;
    if (a.id) return -1;
    if (b.id) return 1;
    return 0;
  });

  sortedEntries.forEach((entry, displayIndex) => {
    // Find original index for updateEntry calls
    const originalIndex = detailsEntries.indexOf(entry);
    
    const tr = document.createElement('tr');
    const cls = (entry.amount || 0) < 0 ? 'amount-negative' : 'amount-positive';
    
    // Build category options
    const categoryOptions = [];
    
    // Add empty option
    categoryOptions.push(`<option value=""${!entry.category_name || entry.category_name === '' ? ' selected' : ''}>Kategorie wählen</option>`);
    
    // Add all categories
    allCategories.forEach(cat => {
      const isSelected = entry.category_name && entry.category_name === cat.fullname;
      if (isSelected) {
        console.log(`Entry ${displayIndex}: Matching category - entry.category_name="${entry.category_name}" === cat.fullname="${cat.fullname}"`);
      }
      categoryOptions.push(`<option value="${cat.fullname}"${isSelected ? ' selected' : ''}>${cat.fullname}</option>`);
    });

    const isFirstEntry = originalIndex === 0;
    const amountInput = isFirstEntry
      ? `<input class="input-sm ${cls}" type="number" step="0.01" value="${entry.amount}" readonly style="background-color: #f0f0f0; cursor: not-allowed;" title="Wird automatisch berechnet">`
      : `<input class="input-sm ${cls}" type="number" step="0.01" value="${entry.amount}" onchange="updateEntry(${originalIndex}, 'amount', parseFloat(this.value) || 0)">`;

    tr.innerHTML = `
      <td><input class="input-sm" type="date" value="${toDateInputValue(entry.dateImport)}" readonly style="background-color: #f0f0f0; cursor: not-allowed;" title="Importdatum kann nicht geändert werden"></td>
      <td>
        <select class="input-sm" onchange="updateEntry(${originalIndex}, 'category_name', this.value)">
          ${categoryOptions.join('')}
        </select>
      </td>
      <td>${amountInput}</td>
      <td class="checkbox-cell"><input type="checkbox" ${entry.accountingPlanned ? 'checked' : ''} onchange="updateEntry(${originalIndex}, 'accountingPlanned', this.checked)"></td>
      <td class="checkbox-cell"><input type="checkbox" ${entry.checked ? 'checked' : ''} onchange="updateEntry(${originalIndex}, 'checked', this.checked)"></td>
      <td class="actions-cell"><button class="btn-ghost" onclick="removeEntry(${originalIndex})">Entfernen</button></td>
    `;
    tbody.appendChild(tr);
  });
  updateEntriesSumDisplay();
}

function updateEntry(index, field, value) {
  if (!detailsEntries[index]) return;
  detailsEntries[index][field] = value;
  if (field === 'amount' && index > 0 && detailsEntries.length > 1) {
    recalculateFirstEntry();
  } else {
    updateEntriesSumDisplay();
  }
}

function recalculateFirstEntry() {
  if (detailsEntries.length === 0) return;
  let sumOthers = 0;
  for (let i = 1; i < detailsEntries.length; i++) {
    sumOthers += parseFloat(detailsEntries[i].amount) || 0;
  }
  const firstEntryAmount = currentTransactionAmount - sumOthers;
  // Log negative amounts silently - no alert popup
  if (firstEntryAmount < 0) {
    console.warn(`Negative amount for first entry: ${formatCurrency(firstEntryAmount)}, sum of others: ${formatCurrency(sumOthers)}, transaction amount: ${formatCurrency(currentTransactionAmount)}`);
  }
  detailsEntries[0].amount = firstEntryAmount;
  renderEntries();
}

function addEntry() {
  detailsEntries.push({ id: null, dateImport: new Date().toISOString(), category_name: '', amount: 0, accountingPlanned: false, checked: false });
  if (detailsEntries.length > 1) recalculateFirstEntry(); else renderEntries();
}

function removeEntry(index) {
  if (index === 0 && detailsEntries.length > 1) {
    alert('Der erste Buchungseintrag kann nicht gelöscht werden, solange weitere Einträge vorhanden sind.');
    return;
  }
  detailsEntries.splice(index, 1);
  if (detailsEntries.length > 0) recalculateFirstEntry(); else renderEntries();
}

async function saveEntries() {
  if (!selectedTransactionId) { alert('Keine Transaktion ausgewählt.'); return; }
  
  // Validate that the sum of entries equals the transaction amount
  let sumEntries = 0;
  for (let i = 0; i < detailsEntries.length; i++) {
    sumEntries += parseFloat(detailsEntries[i].amount) || 0;
  }
  
  const difference = Math.abs(currentTransactionAmount - sumEntries);
  if (difference > 0.01) { // Allow for floating-point rounding errors
    alert(`Validierungsfehler: Die Summe der Buchungseinträge (${formatCurrency(sumEntries)}) entspricht nicht dem Transaktionsbetrag (${formatCurrency(currentTransactionAmount)}).\n\nDifferenz: ${formatCurrency(difference)}\n\nBitte passen Sie die Einträge an, sodass die Summe genau dem Transaktionsbetrag entspricht.`);
    return;
  }
  const saveButton = document.getElementById('saveButton');
  const statusBar = document.getElementById('detailsStatusBar');
  const originalText = saveButton.textContent;
  saveButton.textContent = 'Speichert...';
  saveButton.disabled = true;
  if (statusBar) {
    statusBar.style.display = 'none';
    statusBar.textContent = '';
  }
  try {
    const entries = detailsEntries.map(entry => ({
      id: entry.id || null,
      dateImport: entry.dateImport,
      amount: parseFloat(entry.amount),
      checked: entry.checked,
      accountingPlanned: entry.accountingPlanned,
      category_name: entry.category_name || null
    }));
    const response = await fetch(`${API_BASE}/transactions/${selectedTransactionId}/entries`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ entries })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }
    const updatedTx = await response.json();
    detailsEntries = (updatedTx.entries || []).map(entry => ({
      id: entry.id, dateImport: entry.dateImport, category_name: entry.category_name || '', amount: entry.amount || 0,
      accountingPlanned: entry.accountingPlanned ?? false, checked: entry.checked ?? false
    }));
    renderEntries();
    await loadTransactions(currentPage);
    if (statusBar) {
      statusBar.textContent = '✓ Gespeichert';
      statusBar.style.color = 'var(--color-amount-positive)';
      statusBar.style.display = 'block';
    }
  } catch (error) {
    console.error('Error saving entries:', error);
    if (statusBar) {
      statusBar.textContent = '✗ Fehler';
      statusBar.style.color = 'var(--color-amount-negative)';
      statusBar.style.display = 'block';
    }
    alert(`Fehler beim Speichern: ${error.message}`);
  } finally {
    saveButton.textContent = originalText;
    saveButton.disabled = false;
  }
}

// Import functionality
async function loadImportAccounts() {
  try {
    const response = await fetch(`${API_BASE}/accounts/list?page_size=1000`);
    const data = await response.json();
    importAccounts = data.accounts || [];
    
    const select = document.getElementById('importAccountSelect');
    if (select) {
      select.innerHTML = '<option value="">-- Alle Konten --</option>';
      importAccounts.forEach(account => {
        const option = document.createElement('option');
        option.value = account.id;
        option.textContent = account.name;
        select.appendChild(option);
      });
    }
    
    // Populate CSV account select
    const csvSelect = document.getElementById('csvAccountSelect');
    if (csvSelect) {
      csvSelect.innerHTML = '<option value="">Konto auswählen...</option>';
      importAccounts.forEach(account => {
        const option = document.createElement('option');
        option.value = account.id;
        option.textContent = account.name;
        csvSelect.appendChild(option);
      });
    }
  } catch (error) {
    console.error('Failed to load import accounts:', error);
    const select = document.getElementById('importAccountSelect');
    if (select) {
      select.innerHTML = '<option value="">Fehler beim Laden</option>';
    }
    const csvSelect = document.getElementById('csvAccountSelect');
    if (csvSelect) {
      csvSelect.innerHTML = '<option value="">Fehler beim Laden</option>';
    }
  }
}

async function startImport() {
  const select = document.getElementById('importAccountSelect');
  const button = document.getElementById('importButton');
  const statusDiv = document.getElementById('importStatus');
  
  if (!select || !button || !statusDiv) return;
  
  const accountId = select.value ? parseInt(select.value) : null;
  const accountName = accountId 
    ? importAccounts.find(a => a.id === accountId)?.name || 'Unbekannt'
    : 'Alle Konten';
  
  // Confirm import
  const confirmMsg = accountId
    ? `Import für Konto "${accountName}" starten?`
    : 'Import für ALLE Konten starten? Dies kann mehrere Minuten dauern.';
  
  if (!confirm(confirmMsg)) return;
  
  // Disable button and show status
  button.disabled = true;
  button.textContent = 'Import läuft...';
  statusDiv.style.display = 'block';
  statusDiv.textContent = accountId 
    ? `Import für ${accountName} wird durchgeführt...`
    : 'Import für alle Konten wird durchgeführt...';
  statusDiv.style.color = 'var(--color-text-base)';
  
  try {
    const response = await fetch(`${API_BASE}/transactions/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_id: accountId })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unbekannter Fehler' }));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }
    
    const result = await response.json();
    
    // Show success message
    statusDiv.style.color = 'var(--color-amount-positive)';
    let message = `✓ ${result.message}`;
    
    if (result.files && result.files.length > 0) {
      const filesSummary = result.files.map(f => 
        `${f.file} (${f.account}): ${f.inserted}/${f.total}`
      ).join(', ');
      message += `. Dateien: ${filesSummary}`;
    }
    
    // Show warnings if any
    if (result.warnings && result.warnings.length > 0) {
      message += `\n⚠ Warnungen: ${result.warnings.join('; ')}`;
      statusDiv.style.color = 'var(--color-text-base)';
    }
    
    // Show auto-categorization results
    if (result.auto_categorized !== undefined && result.auto_categorized > 0) {
      message += `\n✓ Automatische Kategorisierung durchgeführt`;
    }
    
    statusDiv.textContent = message;
    statusDiv.style.whiteSpace = 'pre-wrap';
    
    // Reload transactions to show newly imported data
    setTimeout(() => {
      loadTransactions(1);
    }, 1000);
    
  } catch (error) {
    console.error('Import error:', error);
    statusDiv.style.color = 'var(--color-amount-negative)';
    statusDiv.textContent = `✗ Import fehlgeschlagen: ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = 'Import starten';
  }
}

async function startAutoCategorization() {
  const button = document.getElementById('autoCategorizeButton');
  const statusDiv = document.getElementById('importStatus');
  
  if (!button || !statusDiv) return;
  
  // Confirm action
  if (!confirm('Möchten Sie die automatische Kategorisierung für alle unkategorisierten Einträge durchführen?')) {
    return;
  }
  
  // Disable button and show status
  button.disabled = true;
  button.textContent = 'Kategorisiert...';
  statusDiv.style.display = 'block';
  statusDiv.textContent = 'Automatische Kategorisierung läuft...';
  statusDiv.style.color = 'var(--color-text-base)';
  
  try {
    const response = await fetch(`${API_BASE}/transactions/auto-categorize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_id: null })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unbekannter Fehler' }));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }
    
    const result = await response.json();
    
    // Show success message
    statusDiv.style.color = 'var(--color-amount-positive)';
    statusDiv.textContent = `✓ ${result.message}`;
    
    // Reload transactions to show updated data
    setTimeout(() => {
      loadTransactions(1);
    }, 1000);
    
  } catch (error) {
    console.error('Auto-categorization error:', error);
    statusDiv.style.color = 'var(--color-amount-negative)';
    statusDiv.textContent = `✗ Kategorisierung fehlgeschlagen: ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = 'Automatisch kategorisieren';
  }
}

// Page init
window.addEventListener('DOMContentLoaded', async () => {
  await loadCategories();
  await loadImportAccounts();
  await loadImportFormats();
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') loadTransactions(1); });
  }
  
  // Add keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault(); // Verhindert das Standard-Scroll-Verhalten
      handleTransactionNavigation(e.key === 'ArrowDown' ? 'next' : 'prev');
    }
  });
  
  loadTransactions(1);
});

function handleTransactionNavigation(direction) {
  if (!selectedTransactionId || lastDisplayedTransactions.length === 0) return;
  
  const currentIndex = lastDisplayedTransactions.findIndex(t => t.id === selectedTransactionId);
  if (currentIndex === -1) return;
  
  let nextIndex = currentIndex;
  
  if (direction === 'next') {
    // Nicht über Seiten hinweg springen - Limit auf aktuelle Seite
    if (currentIndex < lastDisplayedTransactions.length - 1) {
      nextIndex = currentIndex + 1;
    } else {
      return; // Am Ende der Seite angekommen
    }
  } else if (direction === 'prev') {
    // Nach oben navigieren
    if (currentIndex > 0) {
      nextIndex = currentIndex - 1;
    } else {
      return; // Am Anfang der Seite angekommen
    }
  }
  
  const nextTransaction = lastDisplayedTransactions[nextIndex];
  if (nextTransaction) {
    showTransactionDetails(nextTransaction.id);
  }
}

async function loadImportFormats() {
  try {
    // Formate sind im Backend definiert, wir laden sie über einen API-Endpunkt
    const response = await fetch(`${API_BASE}/transactions/import-formats`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    const formats = data.formats || [];
    
    const select = document.getElementById('csvFormatSelect');
    if (select) {
      select.innerHTML = '<option value="">Format auswählen...</option>';
      formats.forEach(format => {
        const option = document.createElement('option');
        option.value = format;
        option.textContent = format;
        select.appendChild(option);
      });
    }
  } catch (error) {
    console.error('Failed to load import formats:', error);
    // Fallback: Lade bekannte Formate statisch
    const select = document.getElementById('csvFormatSelect');
    if (select) {
      select.innerHTML = '<option value="">Format auswählen...</option>';
      ['csv-cb', 'csv-spk', 'csv-mintos', 'csv-loan'].forEach(format => {
        const option = document.createElement('option');
        option.value = format;
        option.textContent = format;
        select.appendChild(option);
      });
    }
  }
}

async function importSpecificCSV() {
  const fileInput = document.getElementById('csvFileInput');
  const formatSelect = document.getElementById('csvFormatSelect');
  const accountSelect = document.getElementById('csvAccountSelect');
  const button = document.getElementById('csvImportButton');
  const statusDiv = document.getElementById('importStatus');
  
  if (!fileInput || !formatSelect || !accountSelect || !button || !statusDiv) return;
  
  const file = fileInput.files[0];
  const format = formatSelect.value;
  const accountId = accountSelect.value ? parseInt(accountSelect.value) : null;
  
  if (!file) {
    alert('Bitte wählen Sie eine CSV-Datei aus.');
    return;
  }
  
  if (!format) {
    alert('Bitte wählen Sie ein Import-Format aus.');
    return;
  }
  
  // Account ist nur erforderlich, wenn das Format keine Account-Spalte hat
  // Für csv-loan ist es optional, da die Datei selbst Account-Informationen enthält
  
  // Confirm import
  const confirmMsg = accountId
    ? `CSV-Datei "${file.name}" mit Format "${format}" für Konto importieren?`
    : `CSV-Datei "${file.name}" mit Format "${format}" importieren?`;
  
  if (!confirm(confirmMsg)) return;
  
  // Disable button and show status
  button.disabled = true;
  button.textContent = 'Importiert...';
  statusDiv.style.display = 'block';
  statusDiv.textContent = `Importiere ${file.name}...`;
  statusDiv.style.color = 'var(--color-text-base)';
  
  try {
    // Create FormData for file upload
    const formData = new FormData();
    formData.append('file', file);
    formData.append('format', format);
    if (accountId) {
      formData.append('account_id', accountId.toString());
    }
    
    const response = await fetch(`${API_BASE}/transactions/import-csv`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unbekannter Fehler' }));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }
    
    const result = await response.json();
    
    // Show success message
    statusDiv.style.color = 'var(--color-amount-positive)';
    statusDiv.textContent = `✓ ${result.message || 'Import erfolgreich'}`;
    
    if (result.inserted !== undefined && result.total !== undefined) {
      statusDiv.textContent += ` (${result.inserted}/${result.total} Transaktionen)`;
    }
    
    // Show warnings if any
    if (result.warnings && result.warnings.length > 0) {
      statusDiv.textContent += `\n⚠ Warnungen: ${result.warnings.join('; ')}`;
      statusDiv.style.color = 'var(--color-text-base)';
    }
    
    statusDiv.style.whiteSpace = 'pre-wrap';
    
    // Clear file input
    fileInput.value = '';
    
    // Reload transactions to show newly imported data
    setTimeout(() => {
      loadTransactions(1);
    }, 1000);
    
  } catch (error) {
    console.error('CSV import error:', error);
    statusDiv.style.color = 'var(--color-amount-negative)';
    statusDiv.textContent = `✗ Import fehlgeschlagen: ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = 'CSV importieren';
  }
}
