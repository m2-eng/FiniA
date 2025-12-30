// Loan Management page logic
let currentPage = 1;
let searchTerm = '';
let selectedLoanId = null;
let allLoans = [];
let allAccounts = [];
let allCategories = [];
let currentSortColumn = null;
let currentSortDirection = 'asc';
let cachedLoans = [];
let currentLoanData = null;
const itemsPerPage = 10;

async function initLoansPage() {
  loadTheme();
  loadLoans();
  loadAccounts();
  loadCategories();
}

async function loadLoans() {
  try {
    showLoading();
    hideMessage();
    
    const response = await fetch(`${API_BASE}/loans/list`);
    const data = await response.json();
    
    allLoans = data.loans || [];
    cachedLoans = allLoans;
    
    filterAndDisplayLoans();
    hideLoading();
    document.getElementById('loansTable').style.display = 'table';
  } catch (error) {
    console.error('Failed to load loans:', error);
    showError('Fehler beim Laden der Darlehen: ' + error.message);
    hideLoading();
  }
}

async function loadAccounts() {
  try {
    const response = await fetch(`${API_BASE}/loans/accounts/list`);
    const data = await response.json();
    allAccounts = data.accounts || [];
    populateAccountDropdown();
  } catch (error) {
    console.error('Failed to load accounts:', error);
    allAccounts = [];
  }
}

async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/categories/list`);
    const data = await response.json();
    allCategories = data.categories || [];
    populateCategoryDropdowns();
  } catch (error) {
    console.error('Failed to load categories:', error);
    allCategories = [];
  }
}

function populateAccountDropdown() {
  populateDropdown('loanAccount', allAccounts, 'name', '-- Konto wählen --');
}

function populateCategoryDropdowns() {
  populateDropdown('loanCategoryRebooking', allCategories, 'fullname', '-- Kategorie wählen --');
  populateDropdown('loanCategoryIntrest', allCategories, 'fullname', '-- Kategorie wählen --');
}

function filterAndDisplayLoans() {
  // Apply search filter
  let filtered = filterBySearch(allLoans, searchTerm, ['accountName', 'intrestRate']);
  
  // Apply sorting
  if (currentSortColumn) {
    filtered = sortTableData(filtered, currentSortColumn, currentSortDirection);
  }
  
  cachedLoans = filtered;
  currentPage = 1;
  displayLoansPage();
}

function displayLoansPage() {
  const tbody = document.getElementById('loansBody');
  tbody.innerHTML = '';
  
  const pageItems = getPaginatedData(cachedLoans, currentPage, itemsPerPage);
  
  pageItems.forEach(loan => {
    const row = document.createElement('tr');
    row.style.cursor = 'pointer';
    row.onclick = () => selectLoan(loan.id);
    
    const accountName = loan.accountName || '-';
    const intrestRate = loan.intrestRate !== null && loan.intrestRate !== undefined ? 
      parseFloat(loan.intrestRate).toFixed(2) : '-';
    const categoryRebookingName = loan.categoryRebookingName || '-';
    const categoryIntrestName = loan.categoryIntrestName || '-';
    
    row.innerHTML = `
      <td>${escapeHtml(accountName)}</td>
      <td>${escapeHtml(intrestRate)}</td>
      <td>${escapeHtml(categoryRebookingName)}</td>
      <td>${escapeHtml(categoryIntrestName)}</td>
    `;
    
    tbody.appendChild(row);
  });
  
  displayPagination('pagination', currentPage, cachedLoans.length, itemsPerPage, (page) => {
    currentPage = page;
    displayLoansPage();
  });
}

async function selectLoan(loanId) {
  try {
    selectedLoanId = loanId;
    const response = await fetch(`${API_BASE}/loans/${loanId}`);
    const loanData = await response.json();
    currentLoanData = loanData;
    
    displayLoanDetails(loanData);
  } catch (error) {
    console.error('Failed to load loan details:', error);
    showError('Fehler beim Laden der Darlehensdaten');
  }
}

function displayLoanDetails(loan) {
  document.getElementById('detailsPanel').style.display = 'block';
  
  document.getElementById('loanId').value = loan.id || '';
  document.getElementById('loanAccount').value = loan.account || '';
  document.getElementById('loanIntrestRate').value = loan.intrestRate !== null && loan.intrestRate !== undefined ? loan.intrestRate : '';
  document.getElementById('loanCategoryRebooking').value = loan.categoryRebooking || '';
  document.getElementById('loanCategoryIntrest').value = loan.categoryIntrest || '';
  
  document.getElementById('saveButton').textContent = 'Speichern';
  document.getElementById('deleteButton').style.display = 'block';
}

function showNewLoanForm() {
  selectedLoanId = null;
  currentLoanData = null;
  document.getElementById('detailsPanel').style.display = 'block';
  
  document.getElementById('loanId').value = '';
  document.getElementById('loanAccount').value = '';
  document.getElementById('loanIntrestRate').value = '';
  document.getElementById('loanCategoryRebooking').value = '';
  document.getElementById('loanCategoryIntrest').value = '';
  
  document.getElementById('saveButton').textContent = 'Erstellen';
  document.getElementById('deleteButton').style.display = 'none';
}

async function saveLoan() {
  const account = document.getElementById('loanAccount').value;
  const intrestRate = document.getElementById('loanIntrestRate').value;
  const categoryRebooking = document.getElementById('loanCategoryRebooking').value;
  const categoryIntrest = document.getElementById('loanCategoryIntrest').value;
  
  if (!account) {
    showError('Bitte wählen Sie ein Konto');
    return;
  }
  
  const loanData = {
    intrestRate: intrestRate ? parseFloat(intrestRate) : null,
    account: parseInt(account),
    categoryRebooking: categoryRebooking ? parseInt(categoryRebooking) : null,
    categoryIntrest: categoryIntrest ? parseInt(categoryIntrest) : null
  };
  
  try {
    let response;
    if (selectedLoanId) {
      // Update existing loan
      response = await fetch(`${API_BASE}/loans/${selectedLoanId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(loanData)
      });
    } else {
      // Create new loan
      response = await fetch(`${API_BASE}/loans/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(loanData)
      });
    }
    
    if (response.ok) {
      const result = await response.json();
      showSuccess(selectedLoanId ? 'Darlehen aktualisiert' : 'Darlehen erstellt');
      resetForm();
      loadLoans();
    } else {
      const error = await response.json();
      showError('Fehler beim Speichern: ' + error.detail);
    }
  } catch (error) {
    console.error('Error saving loan:', error);
    showError('Fehler beim Speichern des Darlehens');
  }
}

async function deleteLoan() {
  if (!selectedLoanId) return;
  
  if (!confirm('Sind Sie sicher, dass Sie dieses Darlehen löschen möchten?')) {
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE}/loans/${selectedLoanId}`, {
      method: 'DELETE'
    });
    
    if (response.ok) {
      showSuccess('Darlehen gelöscht');
      resetForm();
      loadLoans();
    } else {
      const error = await response.json();
      showError('Fehler beim Löschen: ' + error.detail);
    }
  } catch (error) {
    console.error('Error deleting loan:', error);
    showError('Fehler beim Löschen des Darlehens');
  }
}

function resetForm() {
  selectedLoanId = null;
  currentLoanData = null;
  document.getElementById('detailsPanel').style.display = 'none';
  
  document.getElementById('loanId').value = '';
  document.getElementById('loanAccount').value = '';
  document.getElementById('loanIntrestRate').value = '';
  document.getElementById('loanCategoryRebooking').value = '';
  document.getElementById('loanCategoryIntrest').value = '';
  
  hideMessage();
}

function sortLoans(column) {
  if (currentSortColumn === column) {
    currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
  } else {
    currentSortColumn = column;
    currentSortDirection = 'asc';
  }
  filterAndDisplayLoans();
}

function resetSearch() {
  document.getElementById('searchInput').value = '';
  searchTerm = '';
  filterAndDisplayLoans();
}

// Setup event listeners after page init
function setupLoansEventListeners() {
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('keyup', (e) => {
      searchTerm = e.target.value;
      filterAndDisplayLoans();
    });
  }
}

// Initialize on page load - called from HTML
async function initLoansPageComplete() {
  await initLoansPage();
  setupLoansEventListeners();
}