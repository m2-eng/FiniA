// Planning page logic
let allPlannings = [];
let filteredPlannings = [];
let allAccounts = [];
let allCategories = [];
let allCycles = [];
let currentEditId = null;
let selectedPlanningId = null;
let currentEntries = [];
let currentSortField = null;
let currentSortDirection = 'asc';

// Initialize page
async function initPlanning() {
  // Load master data first, then plannings to ensure detail dropdowns are populated before selection
  await Promise.all([
    loadAccounts(),
    loadCategories(),
    loadCycles()
  ]);
  await loadPlannings();
}

// Reload all tables and data from the server
async function refreshAll() {
  const btn = document.getElementById('reloadAllButton');
  const originalText = btn ? btn.textContent : null;
  if (btn) {
    btn.textContent = 'Lädt neu...';
    btn.disabled = true;
  }

  try {
    await initPlanning();
    // Nach dem Neu-Laden werden Details und Einträge durch loadPlannings/selectPlanning aktualisiert
    alert('Daten neu geladen.');
  } catch (error) {
    console.error('Fehler beim Neuladen:', error);
    alert(`Fehler beim Neuladen: ${error.message || error}`);
  } finally {
    if (btn) {
      btn.textContent = originalText;
      btn.disabled = false;
    }
  }
}

// Load all accounts
async function loadAccounts() {
  try {
    const response = await fetch(`${API_BASE}/accounts/list?page_size=1000`);
    const data = await response.json();
    allAccounts = data.accounts || [];
    populateAccountSelect();
  } catch (error) {
    console.error('Failed to load accounts:', error);
    allAccounts = [];
  }
}

// Load all categories
async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/categories/`);
    const data = await response.json();
    allCategories = data.categories || [];
    populateCategorySelect();
  } catch (error) {
    console.error('Failed to load categories:', error);
    allCategories = [];
  }
}

// Load all planning cycles
async function loadCycles() {
  try {
    const response = await fetch(`${API_BASE}/planning/cycles`);
    allCycles = await response.json();
    populateCycleSelect();
  } catch (error) {
    console.error('Failed to load cycles:', error);
    allCycles = [];
  }
}

// Load all plannings
async function loadPlannings() {
  const loadingIndicator = document.getElementById('loadingIndicator');
  const planningsTable = document.getElementById('planningsTable');
  const errorMessage = document.getElementById('errorMessage');

  if (loadingIndicator) loadingIndicator.style.display = 'block';
  if (planningsTable) planningsTable.style.display = 'none';
  if (errorMessage) errorMessage.style.display = 'none';

  try {
    const response = await fetch(`${API_BASE}/planning/`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const data = await response.json();
    allPlannings = data.plannings || [];
    filteredPlannings = [...allPlannings];
    const previousSelection = selectedPlanningId;
    const validIds = new Set(allPlannings.map(p => p.id));
    selectedPlanningId = validIds.has(previousSelection) ? previousSelection : (allPlannings[0]?.id ?? null);

    displayPlannings();
    if (selectedPlanningId) {
      await selectPlanning(selectedPlanningId, { skipDisplayUpdate: true });
    } else {
      clearPlanningDetails();
    }

    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (planningsTable) planningsTable.style.display = 'table';
  } catch (error) {
    console.error('Error loading plannings:', error);
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (errorMessage) {
      errorMessage.textContent = `Fehler beim Laden der Planungen: ${error.message}`;
      errorMessage.style.display = 'block';
    }
  }
}

// Display plannings in table
function displayPlannings() {
  const tbody = document.getElementById('planningsBody');
  if (!tbody) return;
  
  tbody.innerHTML = '';

  const planningsToShow = filteredPlannings.length > 0 || document.getElementById('planningSearch')?.value ? filteredPlannings : allPlannings;

  if (planningsToShow.length === 0) {
    const searchValue = document.getElementById('planningSearch')?.value;
    const message = searchValue ? 'Keine Planungen gefunden' : 'Keine Planungen vorhanden';
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 20px;">${message}</td></tr>`;
    return;
  }

  planningsToShow.forEach(planning => {
    const row = document.createElement('tr');
    row.classList.add('planning-row');
    if (planning.id === selectedPlanningId) {
      row.classList.add('selected');
    }
    row.onclick = () => selectPlanning(planning.id);
    const amountClass = planning.amount < 0 ? 'amount-negative' : 'amount-positive';
    const activeLabel = isPlanningActive(planning) ? 'Aktiv' : 'Inaktiv';
    const activeClass = isPlanningActive(planning) ? 'status-active' : 'status-inactive';
    
    row.innerHTML = `
      <td>${planning.account_name}</td>
      <td>${planning.category_name || '-'}</td>
      <td class="${amountClass}" style="text-align: right;">${formatCurrency(planning.amount)}</td>
      <td>${planning.cycle_name}</td>
      <td><span class="${activeClass}">${activeLabel}</span></td>
      <td>
        <div class="planning-actions">
          <button class="btn-small" onclick="editPlanning(${planning.id}); event.stopPropagation();">Bearbeiten</button>
          <button class="btn-small delete" onclick="deletePlanning(${planning.id}); event.stopPropagation();">Löschen</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

// Format currency
function formatCurrency(amount) {
  const num = parseFloat(amount);
  return `€ ${num.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, ' ')}`;
}

// Format date
function formatDate(dateString) {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function isPlanningActive(planning) {
  const now = new Date();
  const start = planning.dateStart ? new Date(planning.dateStart) : null;
  const end = planning.dateEnd ? new Date(planning.dateEnd) : null;

  if (start && start > now) return false;
  if (end && end < now) return false;
  return true;
}

// Filter plannings based on search input
function filterPlannings() {
  const searchInput = document.getElementById('planningSearch');
  const hideInactiveCheckbox = document.getElementById('hideInactive');
  if (!searchInput) return;
  
  const searchTerm = searchInput.value.toLowerCase().trim();
  const hideInactive = hideInactiveCheckbox ? hideInactiveCheckbox.checked : false;
  
  if (!searchTerm && !hideInactive) {
    filteredPlannings = [...allPlannings];
  } else {
    filteredPlannings = allPlannings.filter(planning => {
      // Filter by active status if checkbox is checked
      if (hideInactive && !isPlanningActive(planning)) {
        return false;
      }
      
      // Filter by search term if provided
      if (searchTerm) {
        const accountName = (planning.account_name || '').toLowerCase();
        const categoryName = (planning.category_name || '').toLowerCase();
        const description = (planning.description || '').toLowerCase();
        const cycleName = (planning.cycle_name || '').toLowerCase();
        const amount = String(planning.amount || '');
        
        return accountName.includes(searchTerm) ||
               categoryName.includes(searchTerm) ||
               description.includes(searchTerm) ||
               cycleName.includes(searchTerm) ||
               amount.includes(searchTerm);
      }
      
      return true;
    });
  }
  
  // Reapply current sort if active
  if (currentSortField) {
    applySorting();
  }
  
  displayPlannings();
}

// Sort plannings by field
function sortPlannings(field) {
  // Toggle direction if clicking same field
  if (currentSortField === field) {
    currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    currentSortField = field;
    currentSortDirection = 'asc';
  }
  
  applySorting();
  updateSortIndicators();
  displayPlannings();
}

function applySorting() {
  const dataToSort = filteredPlannings.length > 0 || document.getElementById('planningSearch')?.value ? filteredPlannings : allPlannings;
  
  dataToSort.sort((a, b) => {
    let aVal, bVal;
    
    if (currentSortField === 'status') {
      aVal = isPlanningActive(a) ? 1 : 0;
      bVal = isPlanningActive(b) ? 1 : 0;
    } else if (currentSortField === 'amount') {
      aVal = parseFloat(a.amount) || 0;
      bVal = parseFloat(b.amount) || 0;
    } else {
      aVal = (a[currentSortField] || '').toString().toLowerCase();
      bVal = (b[currentSortField] || '').toString().toLowerCase();
    }
    
    if (aVal < bVal) return currentSortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return currentSortDirection === 'asc' ? 1 : -1;
    return 0;
  });
}

function updateSortIndicators() {
  // Clear all indicators
  document.querySelectorAll('.sort-indicator').forEach(el => {
    el.textContent = '';
  });
  
  // Set current indicator
  if (currentSortField) {
    const indicator = document.getElementById(`sort-${currentSortField}`);
    if (indicator) {
      indicator.textContent = currentSortDirection === 'asc' ? '▲' : '▼';
    }
  }
}

// Convert date to input value
function toDateInputValue(value) {
  const d = value ? new Date(value) : new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// Populate account select
function populateAccountSelect() {
  const select = document.getElementById('accountSelect');
  if (!select) return;
  
  select.innerHTML = '<option value="">-- Konto wählen --</option>';
  allAccounts.forEach(account => {
    const option = document.createElement('option');
    option.value = String(account.id);
    option.textContent = account.name;
    select.appendChild(option);
  });

  // Populate detail account select
  const detailSelect = document.getElementById('detailAccount');
  if (detailSelect) {
    detailSelect.innerHTML = '<option value="">-</option>';
    allAccounts.forEach(account => {
      const option = document.createElement('option');
      option.value = String(account.id);
      option.textContent = account.name;
      detailSelect.appendChild(option);
    });
  }
}

// Populate category select
function populateCategorySelect() {
  const select = document.getElementById('categorySelect');
  if (!select) return;
  
  select.innerHTML = '<option value="">-- Kategorie wählen --</option>';
  allCategories.forEach(category => {
    const option = document.createElement('option');
    option.value = String(category.id);
    option.textContent = category.fullname;
    select.appendChild(option);
  });

  // Populate detail category select
  const detailSelect = document.getElementById('detailCategory');
  if (detailSelect) {
    detailSelect.innerHTML = '<option value="">-</option>';
    allCategories.forEach(category => {
      const option = document.createElement('option');
      option.value = String(category.id);
      option.textContent = category.fullname;
      detailSelect.appendChild(option);
    });
  }
}

// Populate cycle select
function populateCycleSelect() {
  const select = document.getElementById('cycleSelect');
  if (!select) return;
  
  select.innerHTML = '<option value="">-- Zyklus wählen --</option>';
  allCycles.forEach(cycle => {
    const option = document.createElement('option');
    option.value = String(cycle.id);
    option.textContent = cycle.cycle;
    select.appendChild(option);
  });

  // Populate detail cycle select
  const detailSelect = document.getElementById('detailCycle');
  if (detailSelect) {
    detailSelect.innerHTML = '<option value="">-</option>';
    allCycles.forEach(cycle => {
      const option = document.createElement('option');
      option.value = String(cycle.id);
      option.textContent = cycle.cycle;
      detailSelect.appendChild(option);
    });
  }
}

// Show create dialog
function showCreateDialog() {
  currentEditId = null;
  document.getElementById('dialogTitle').textContent = 'Neue Planung erstellen';
  document.getElementById('planningForm').reset();
  document.getElementById('planningId').value = '';
  document.getElementById('planningDialog').style.display = 'block';
}

// Show edit dialog
function editPlanning(planningId) {
  const planning = allPlannings.find(p => p.id === planningId);
  if (!planning) return;

  currentEditId = planningId;
  document.getElementById('dialogTitle').textContent = 'Planung bearbeiten';
  document.getElementById('planningId').value = planningId;
  document.getElementById('description').value = planning.description || '';
  document.getElementById('amount').value = planning.amount;
  document.getElementById('accountSelect').value = planning.account_id;
  document.getElementById('categorySelect').value = planning.category_id;
  document.getElementById('cycleSelect').value = planning.cycle_id;
  document.getElementById('dateStart').value = toDateInputValue(planning.dateStart);
  document.getElementById('dateEnd').value = planning.dateEnd ? toDateInputValue(planning.dateEnd) : '';
  document.getElementById('planningDialog').style.display = 'block';
}

// Close dialog
function closePlanningDialog() {
  document.getElementById('planningDialog').style.display = 'none';
  currentEditId = null;
}

// Save planning
async function savePlanning(event) {
  event.preventDefault();

  const saveButton = document.getElementById('saveButton');
  const originalText = saveButton.textContent;
  saveButton.textContent = 'Speichert...';
  saveButton.disabled = true;

  try {
    const formData = {
      description: document.getElementById('description').value || null,
      amount: parseFloat(document.getElementById('amount').value),
      account_id: parseInt(document.getElementById('accountSelect').value),
      category_id: parseInt(document.getElementById('categorySelect').value),
      cycle_id: parseInt(document.getElementById('cycleSelect').value),
      dateStart: new Date(document.getElementById('dateStart').value).toISOString(),
      dateEnd: document.getElementById('dateEnd').value ? new Date(document.getElementById('dateEnd').value).toISOString() : null
    };

    let response;
    let payload;
    if (currentEditId) {
      // Update existing planning
      response = await fetch(`${API_BASE}/planning/${currentEditId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
    } else {
      // Create new planning
      response = await fetch(`${API_BASE}/planning/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
    }

    payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP error! status: ${response.status}`);
    }

    selectedPlanningId = payload.id;
    closePlanningDialog();
    await loadPlannings();
    alert(currentEditId ? 'Planung erfolgreich aktualisiert!' : 'Planung erfolgreich erstellt!');
  } catch (error) {
    console.error('Error saving planning:', error);
    alert(`Fehler beim Speichern: ${error.message}`);
  } finally {
    saveButton.textContent = originalText;
    saveButton.disabled = false;
  }
}

// Delete planning
async function deletePlanning(planningId) {
  const planning = allPlannings.find(p => p.id === planningId);
  if (!planning) return;

  const confirmMsg = `Möchten Sie die Planung "${planning.description || planning.category_name}" wirklich löschen?`;
  if (!confirm(confirmMsg)) return;

  try {
    const response = await fetch(`${API_BASE}/planning/${planningId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    if (planningId === selectedPlanningId) {
      selectedPlanningId = null;
    }
    await loadPlannings();
    alert('Planung erfolgreich gelöscht!');
  } catch (error) {
    console.error('Error deleting planning:', error);
    alert(`Fehler beim Löschen: ${error.message}`);
  }
}

// Close modal when clicking outside
window.onclick = function(event) {
  const modal = document.getElementById('planningDialog');
  if (event.target === modal) {
    closePlanningDialog();
  }
};

function renderPlanningDetails(planning) {
  const detailCard = document.getElementById('planningDetails');
  if (!detailCard) return;
  const generateButton = document.getElementById('generateEntriesButton');
  const saveButton = document.getElementById('saveDetailsButton');

  const descriptionInput = document.getElementById('detailDescription');
  const amountInput = document.getElementById('detailAmount');
  const accountSelect = document.getElementById('detailAccount');
  const categorySelect = document.getElementById('detailCategory');
  const cycleSelect = document.getElementById('detailCycle');
  const startInput = document.getElementById('detailStart');
  const endInput = document.getElementById('detailEnd');

  if (!planning) {
    descriptionInput.value = '';
    amountInput.value = '';
    accountSelect.value = '';
    categorySelect.value = '';
    cycleSelect.value = '';
    startInput.value = '';
    endInput.value = '';

    descriptionInput.disabled = true;
    amountInput.disabled = true;
    accountSelect.disabled = true;
    categorySelect.disabled = true;
    cycleSelect.disabled = true;
    startInput.disabled = true;
    endInput.disabled = true;

    if (generateButton) generateButton.disabled = true;
    if (saveButton) saveButton.style.display = 'none';
    return;
  }

  // Fill dropdowns with current options (in case they're empty)
  populateAccountSelect();
  populateCategorySelect();
  populateCycleSelect();

  // Set values after dropdowns are populated
  descriptionInput.value = planning.description || '';
  amountInput.value = planning.amount;
  
  // Debug logging
  console.log('Planning account_id:', planning.account_id, 'Type:', typeof planning.account_id);
  console.log('Available accounts:', allAccounts.map(a => ({ id: a.id, name: a.name })));
  
  // Set select values with explicit type conversion
  setTimeout(() => {
    accountSelect.value = String(planning.account_id);
    categorySelect.value = String(planning.category_id);
    cycleSelect.value = String(planning.cycle_id);
    console.log('Account select value set to:', accountSelect.value, 'Actual value:', accountSelect.value);
  }, 50);
  
  startInput.value = toDateInputValue(planning.dateStart);
  endInput.value = planning.dateEnd ? toDateInputValue(planning.dateEnd) : '';

  descriptionInput.disabled = false;
  amountInput.disabled = false;
  accountSelect.disabled = false;
  categorySelect.disabled = false;
  cycleSelect.disabled = false;
  startInput.disabled = false;
  endInput.disabled = false;

  if (generateButton) generateButton.disabled = false;
  if (saveButton) saveButton.style.display = 'inline-block';
}

function clearPlanningDetails() {
  renderPlanningDetails(null);
  clearEntries();
}

async function selectPlanning(planningId, options = {}) {
  const planning = allPlannings.find(p => p.id === planningId);
  if (!planning) return;

  selectedPlanningId = planningId;
  if (!options.skipDisplayUpdate) {
    displayPlannings();
  }

  renderPlanningDetails(planning);
  await loadPlanningEntries(planningId);
}

async function loadPlanningEntries(planningId) {
  const loading = document.getElementById('entriesLoading');
  const errorBox = document.getElementById('entriesError');
  const table = document.getElementById('planningEntriesTable');

  if (loading) loading.style.display = 'block';
  if (errorBox) errorBox.style.display = 'none';
  if (table) table.style.display = 'none';

  try {
    const response = await fetch(`${API_BASE}/planning/${planningId}/entries`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `HTTP error! status: ${response.status}`);
    }

    currentEntries = data.entries || [];
    renderEntries();

    if (table) table.style.display = 'table';
  } catch (error) {
    console.error('Error loading planning entries:', error);
    if (errorBox) {
      errorBox.textContent = `Fehler beim Laden der Planungseinträge: ${error.message}`;
      errorBox.style.display = 'block';
    }
  } finally {
    if (loading) loading.style.display = 'none';
  }
}

function renderEntries() {
  const tbody = document.getElementById('planningEntriesBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (currentEntries.length === 0) {
    tbody.innerHTML = '<tr><td colspan="2" style="text-align:center; padding:12px;">Keine Planungseinträge vorhanden</td></tr>';
    return;
  }

  currentEntries.forEach(entry => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${formatDate(entry.dateValue)}</td>
      <td style="text-align:right;">${formatCurrency(findPlanningAmount(entry.planning_id))}</td>
    `;
    tbody.appendChild(row);
  });
}

function clearEntries() {
  currentEntries = [];
  const tbody = document.getElementById('planningEntriesBody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="2" style="text-align:center; padding:12px;">Keine Planung ausgewählt</td></tr>';
}

function findPlanningAmount(planningId) {
  const planning = allPlannings.find(p => p.id === planningId);
  return planning ? planning.amount : 0;
}

async function generatePlanningEntries() {
  if (!selectedPlanningId) return;
  const button = document.getElementById('generateEntriesButton');
  const original = button.textContent;
  button.textContent = 'Aktualisiere...';
  button.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/planning/${selectedPlanningId}/entries/generate`, {
      method: 'POST'
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP error! status: ${response.status}`);
    }

    currentEntries = data.entries || [];
    renderEntries();
    alert('Planungseinträge aktualisiert.');
  } catch (error) {
    console.error('Error generating planning entries:', error);
    alert(`Fehler beim Aktualisieren der Planungseinträge: ${error.message}`);
  } finally {
    button.textContent = original;
    button.disabled = false;
  }
}

// Save changes from detail view
async function saveDetailsChanges() {
  if (!selectedPlanningId) return;

  const saveButton = document.getElementById('saveDetailsButton');
  const originalText = saveButton.textContent;
  saveButton.textContent = 'Speichert...';
  saveButton.disabled = true;

  try {
    const formData = {
      description: document.getElementById('detailDescription').value || null,
      amount: parseFloat(document.getElementById('detailAmount').value),
      account_id: parseInt(document.getElementById('detailAccount').value),
      category_id: parseInt(document.getElementById('detailCategory').value),
      cycle_id: parseInt(document.getElementById('detailCycle').value),
      dateStart: new Date(document.getElementById('detailStart').value).toISOString(),
      dateEnd: document.getElementById('detailEnd').value ? new Date(document.getElementById('detailEnd').value).toISOString() : null
    };

    const response = await fetch(`${API_BASE}/planning/${selectedPlanningId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP error! status: ${response.status}`);
    }

    await loadPlannings();
    alert('Änderungen erfolgreich gespeichert!');
  } catch (error) {
    console.error('Error saving details:', error);
    alert(`Fehler beim Speichern: ${error.message}`);
  } finally {
    saveButton.textContent = originalText;
    saveButton.disabled = false;
  }
}
