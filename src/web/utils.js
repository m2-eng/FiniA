/**
 * Shared utility functions for FiniA web pages
 */

// ============================================================================
// Authentication Utilities
// ============================================================================

/**
 * Prüft ob User eingeloggt ist. Wenn nicht → Weiterleitung zu login.html
 */
function requireAuth() {
  const token = localStorage.getItem('auth_token');
  
  if (!token) {
    window.location.href = '/login.html';
    return false;
  }
  
  return true;
}

/**
 * Gibt Auth-Header für API-Requests zurück
 */
function getAuthHeaders() {
  const token = localStorage.getItem('auth_token');
  
  if (!token) {
    return {};
  }
  
  return {
    'Authorization': `Bearer ${token}`
  };
}

/**
 * Fetch-Wrapper mit automatischer Auth und Error-Handling
 */
async function authenticatedFetch(url, options = {}) {
  const migrationsReady = window.migrationsReady;
  const urlString = typeof url === 'string' ? url : String(url);
  const shouldWait = migrationsReady && !window._migrationBypass && !urlString.includes('/setup/migrations/');

  if (shouldWait) {
    try {
      await migrationsReady;
    } catch (error) {
      console.error('Migration wait failed:', error);
    }
  }

  const token = localStorage.getItem('auth_token');
  
  if (!token) {
    window.location.href = '/login.html';
    throw new Error('Not authenticated');
  }
  
  // Merge auth headers
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`
  };
  
  const response = await fetch(url, { ...options, headers });
  
  // Bei 401 → Session abgelaufen → Login
  if (response.status === 401) {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('username');
    localStorage.removeItem('database');
    window.location.href = '/login.html';
    throw new Error('Session expired');
  }
  
  return response;
}

/**
 * Logout-Funktion für alle Seiten
 */
async function logout() {
  const token = localStorage.getItem('auth_token');
  
  if (token) {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
  }
  
  // Cleanup local storage
  localStorage.removeItem('auth_token');
  localStorage.removeItem('username');
  localStorage.removeItem('database');
  
  // Redirect to login
  window.location.href = '/login.html';
}

/**
 * Gibt aktuellen Username zurück
 */
function getCurrentUsername() {
  return localStorage.getItem('username') || 'Unbekannt';
}

/**
 * Gibt aktuelle Datenbank zurück
 */
function getCurrentDatabase() {
  return localStorage.getItem('database') || 'Unbekannt';
}

// ============================================================================
// String & Display
// ============================================================================

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function toDateInputValue(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatCurrency(value) {
  if (value === null || value === undefined) return '-';
  const number = parseFloat(value);
  if (isNaN(number)) return '-';
  return number.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
}

// Dropdown Population
function populateDropdown(dropdownId, items, displayProperty, placeholderText = '-- Auswählen --') {
  const dropdown = document.getElementById(dropdownId);
  if (!dropdown) return;
  const currentValue = dropdown.value;
  dropdown.innerHTML = `<option value="">${placeholderText}</option>`;
  items.forEach(item => {
    const option = document.createElement('option');
    option.value = item.id;
    option.textContent = item[displayProperty];
    dropdown.appendChild(option);
  });
  if (currentValue) dropdown.value = currentValue;
}

// Table Sorting
function sortTableData(data, column, direction = 'asc') {
  return [...data].sort((a, b) => {
    let aVal = a[column];
    let bVal = b[column];
    if (aVal === null || aVal === undefined) aVal = '';
    if (bVal === null || bVal === undefined) bVal = '';
    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }
    if (aVal < bVal) return direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return direction === 'asc' ? 1 : -1;
    return 0;
  });
}

// Pagination
function displayPagination(containerId, currentPage, totalItems, itemsPerPage, onPageChange) {
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  if (totalPages <= 1) return;
  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement('button');
    btn.textContent = i;
    btn.className = i === currentPage ? 'active' : '';
    btn.onclick = () => onPageChange(i);
    container.appendChild(btn);
  }
}

function getPaginatedData(data, page, itemsPerPage) {
  const start = (page - 1) * itemsPerPage;
  return data.slice(start, start + itemsPerPage);
}

// Messages
function showError(message, elementId = 'errorMessage') {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = message;
  el.className = 'error';
  el.style.display = 'block';
}

function showSuccess(message, elementId = 'errorMessage', duration = 3000) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = message;
  el.className = 'success';
  el.style.display = 'block';
  setTimeout(() => el.style.display = 'none', duration);
}

function hideMessage(elementId = 'errorMessage') {
  const el = document.getElementById(elementId);
  if (el) el.style.display = 'none';
}

// Loading
function showLoading(elementId = 'loadingIndicator') {
  const el = document.getElementById(elementId);
  if (el) el.style.display = 'block';
}

function hideLoading(elementId = 'loadingIndicator') {
  const el = document.getElementById(elementId);
  if (el) el.style.display = 'none';
}

// Search
function filterBySearch(data, searchTerm, searchFields) {
  if (!searchTerm) return data;
  const term = searchTerm.toLowerCase();
  return data.filter(item => searchFields.some(field => {
    const value = item[field];
    return value && value.toString().toLowerCase().includes(term);
  }));
}
