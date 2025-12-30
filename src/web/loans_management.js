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
    document.getElementById('loadingIndicator').style.display = 'block';
    document.getElementById('errorMessage').style.display = 'none';
    
    const response = await fetch(`${API_BASE}/loans/list`);
    const data = await response.json();
    
    allLoans = data.loans || [];
    cachedLoans = allLoans;
    
    filterAndDisplayLoans();
    document.getElementById('loadingIndicator').style.display = 'none';
    document.getElementById('loansTable').style.display = 'table';
  } catch (error) {
    console.error('Failed to load loans:', error);
    document.getElementById('errorMessage').style.display = 'block';
    document.getElementById('errorMessage').textContent = 'Fehler beim Laden der Darlehen: ' + error.message;
    document.getElementById('loadingIndicator').style.display = 'none';
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
  const dropdown = document.getElementById('loanAccount');
  if (!dropdown) return;
  const currentValue = dropdown.value;
  dropdown.innerHTML = '<option value="">-- Konto wählen --</option>';
  allAccounts.forEach(account => {
    const option = document.createElement('option');
    option.value = account.id;
    option.textContent = account.name;
    dropdown.appendChild(option);
  });
  if (currentValue) dropdown.value = currentValue;
}

function populateCategoryDropdowns() {
  const dropdowns = ['loanCategoryRebooking', 'loanCategoryIntrest'];
  dropdowns.forEach(dropdownId => {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    const currentValue = dropdown.value;
    dropdown.innerHTML = '<option value="">-- Kategorie wählen --</option>';
    allCategories.forEach(category => {
      const option = document.createElement('option');
      option.value = category.id;
      option.textContent = category.fullname;
      dropdown.appendChild(option);
    });
    if (currentValue) dropdown.value = currentValue;
  });
}

function filterAndDisplayLoans() {
  let filtered = allLoans;
  
  if (searchTerm) {
    filtered = allLoans.filter(loan => {
      const accountName = (loan.accountName || '').toLowerCase();
      const intrestRate = (loan.intrestRate || '').toString().toLowerCase();
      const term = searchTerm.toLowerCase();
      return accountName.includes(term) || intrestRate.includes(term);
    });
  }
  
  if (currentSortColumn) {
    filtered.sort((a, b) => {
      let aVal = a[currentSortColumn];
      let bVal = b[currentSortColumn];
      
      if (aVal === null || aVal === undefined) aVal = '';
      if (bVal === null || bVal === undefined) bVal = '';
      
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      
      if (aVal < bVal) return currentSortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return currentSortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }
  
  cachedLoans = filtered;
  currentPage = 1;
  displayLoansPage();
}

function displayLoansPage() {
  const tbody = document.getElementById('loansBody');
  tbody.innerHTML = '';
  
  const start = (currentPage - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  const pageItems = cachedLoans.slice(start, end);
  
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
  
  displayPagination();
}

function displayPagination() {
  const totalPages = Math.ceil(cachedLoans.length / itemsPerPage);
  const paginationDiv = document.getElementById('pagination');
  paginationDiv.innerHTML = '';
  
  if (totalPages <= 1) return;
  
  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement('button');
    btn.textContent = i;
    btn.className = i === currentPage ? 'btn-active' : '';
    btn.onclick = () => {
      currentPage = i;
      displayLoansPage();
    };
    paginationDiv.appendChild(btn);
  }
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

document.getElementById('searchInput')?.addEventListener('keyup', (e) => {
  searchTerm = e.target.value;
  filterAndDisplayLoans();
});

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
  
  document.getElementById('errorMessage').style.display = 'none';
}

function showError(message) {
  const errorDiv = document.getElementById('errorMessage');
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
}

function showSuccess(message) {
  const errorDiv = document.getElementById('errorMessage');
  errorDiv.textContent = message;
  errorDiv.className = 'error';
  errorDiv.style.display = 'block';
  setTimeout(() => {
    errorDiv.style.display = 'none';
  }, 3000);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Load theme on page load
document.addEventListener('DOMContentLoaded', loadTheme);
