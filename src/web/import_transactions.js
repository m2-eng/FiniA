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

async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/categories/`);
    const data = await response.json();
    allCategories = data.categories || [];
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
  const searchInput = document.getElementById('searchInput');
  searchTerm = searchInput ? searchInput.value : '';

  const loadingIndicator = document.getElementById('loadingIndicator');
  const transactionsTable = document.getElementById('transactionsTable');
  const errorMessage = document.getElementById('errorMessage');

  if (loadingIndicator) loadingIndicator.style.display = 'block';
  if (transactionsTable) transactionsTable.style.display = 'none';
  if (errorMessage) errorMessage.style.display = 'none';

  try {
    const params = new URLSearchParams({ page, page_size: 50 });
    if (searchTerm) params.append('search', searchTerm);
    if (currentFilter && currentFilter !== 'all') params.append('filter', currentFilter);

    const response = await fetch(`${API_BASE}/transactions/?${params}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const data = await response.json();
    displayTransactions(data.transactions, true);
    displayPagination(data.page, Math.ceil(data.total / data.page_size));

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
    row.innerHTML = `
      <td>${formatDate(transaction.dateValue)}</td>
      <td>${truncateText(transaction.description, 60)}</td>
      <td class="${amountClass}" style="text-align: right;">${formatCurrency(transaction.amount)}</td>
      <td>${transaction.account_name}</td>
      <td style="text-align: center;">${transaction.entries.length}</td>
    `;
    row.onclick = () => showTransactionDetails(transaction.id);
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
  if (detailsPanel) detailsPanel.style.display = 'none';
  const detailsBody = document.getElementById('detailsBody');
  const detailsInfo = document.getElementById('detailsInfo');
  if (detailsBody) detailsBody.innerHTML = '';
  if (detailsInfo) detailsInfo.innerHTML = '';
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
      if (tr.dataset.id === String(tx.id)) tr.classList.add('selected');
      else tr.classList.remove('selected');
    });

    const amountCls = tx.amount < 0 ? 'amount-negative' : 'amount-positive';
    const info = [
      { label: 'Transaktionsbetrag', value: `<span class="${amountCls}">${formatCurrency(tx.amount)}</span>` },
      { label: 'Konto', value: tx.account_name || '-' },
      { label: 'Datum', value: formatDate(tx.dateValue) },
      { label: 'Beschreibung', value: tx.description || '-' },
      { label: 'Empfänger', value: tx.recipientApplicant || '-' },
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

function renderEntries() {
  const tbody = document.getElementById('detailsBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  detailsEntries.forEach((entry, index) => {
    const tr = document.createElement('tr');
    const cls = (entry.amount || 0) < 0 ? 'amount-negative' : 'amount-positive';
    
    // Build category options
    const categoryOptions = [];
    
    // Add empty option
    categoryOptions.push(`<option value=""${!entry.category_name || entry.category_name === '' ? ' selected' : ''}>Kategorie wählen</option>`);
    
    // Add all categories
    allCategories.forEach(cat => {
      const isSelected = entry.category_name && entry.category_name === cat.fullname;
      categoryOptions.push(`<option value="${cat.fullname}"${isSelected ? ' selected' : ''}>${cat.fullname}</option>`);
    });

    const isFirstEntry = index === 0;
    const amountInput = isFirstEntry
      ? `<input class="input-sm ${cls}" type="number" step="0.01" value="${entry.amount}" readonly style="background-color: #f0f0f0; cursor: not-allowed;" title="Wird automatisch berechnet">`
      : `<input class="input-sm ${cls}" type="number" step="0.01" value="${entry.amount}" onchange="updateEntry(${index}, 'amount', parseFloat(this.value) || 0)">`;

    tr.innerHTML = `
      <td><input class="input-sm" type="date" value="${toDateInputValue(entry.dateImport)}" readonly style="background-color: #f0f0f0; cursor: not-allowed;" title="Importdatum kann nicht geändert werden"></td>
      <td>
        <select class="input-sm" onchange="updateEntry(${index}, 'category_name', this.value)">
          ${categoryOptions.join('')}
        </select>
      </td>
      <td>${amountInput}</td>
      <td class="checkbox-cell"><input type="checkbox" ${entry.accountingPlanned ? 'checked' : ''} onchange="updateEntry(${index}, 'accountingPlanned', this.checked)"></td>
      <td class="checkbox-cell"><input type="checkbox" ${entry.checked ? 'checked' : ''} onchange="updateEntry(${index}, 'checked', this.checked)"></td>
      <td class="actions-cell"><button class="btn-ghost" onclick="removeEntry(${index})">Entfernen</button></td>
    `;
    tbody.appendChild(tr);
  });
}

function updateEntry(index, field, value) {
  if (!detailsEntries[index]) return;
  detailsEntries[index][field] = value;
  if (field === 'amount' && index > 0 && detailsEntries.length > 1) {
    recalculateFirstEntry();
  }
}

function recalculateFirstEntry() {
  if (detailsEntries.length === 0) return;
  let sumOthers = 0;
  for (let i = 1; i < detailsEntries.length; i++) {
    sumOthers += parseFloat(detailsEntries[i].amount) || 0;
  }
  const firstEntryAmount = currentTransactionAmount - sumOthers;
  if (firstEntryAmount < 0) {
    alert(`Fehler: Der berechnete Betrag für die erste Buchung (${formatCurrency(firstEntryAmount)}) ist negativ. Die Summe der anderen Buchungseinträge (${formatCurrency(sumOthers)}) übersteigt den Transaktionsbetrag (${formatCurrency(currentTransactionAmount)}).`);
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
  const saveButton = document.getElementById('saveButton');
  const originalText = saveButton.textContent;
  saveButton.textContent = 'Speichert...';
  saveButton.disabled = true;
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
    alert('Buchungseinträge erfolgreich gespeichert!');
  } catch (error) {
    console.error('Error saving entries:', error);
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
    if (!select) return;
    
    select.innerHTML = '<option value="">-- Alle Konten --</option>';
    
    importAccounts.forEach(account => {
      const option = document.createElement('option');
      option.value = account.id;
      option.textContent = account.name;
      select.appendChild(option);
    });
  } catch (error) {
    console.error('Failed to load import accounts:', error);
    const select = document.getElementById('importAccountSelect');
    if (select) {
      select.innerHTML = '<option value="">Fehler beim Laden</option>';
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
    if (result.auto_categorized !== undefined) {
      message += `\n✓ Automatische Kategorisierung: ${result.auto_categorized} von ${result.auto_categorized_total} Einträgen`;
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
    statusDiv.textContent = `✓ ${result.message} (${result.categorized} von ${result.total_checked} Einträgen kategorisiert)`;
    
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
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') loadTransactions(1); });
  }
  loadTransactions(1);
});
