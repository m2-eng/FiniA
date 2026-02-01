// Shared app utilities
const API_BASE = '/api';

// Theme Management
function initTheme() {
  // Load saved theme or default to light
  const savedTheme = localStorage.getItem('theme') || 'light';
  applyTheme(savedTheme);
  updateThemeIcon(savedTheme);
}

function applyTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  localStorage.setItem('theme', theme);
}

function toggleTheme() {
  const currentTheme = localStorage.getItem('theme') || 'light';
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  applyTheme(newTheme);
  updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.textContent = theme === 'light' ? '🌙' : '☀️';
  }
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
});

async function loadTheme() {
  try {
    const response = await fetch(`${API_BASE}/theme/css`);
    const data = await response.json();
    const el = document.getElementById('dynamic-theme');
    if (el) el.textContent = data.css;
  } catch (error) {
    console.error('Failed to load theme:', error);
  }
}

function setActiveNav(currentRoute) {
  document.querySelectorAll('.top-nav .nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.route === currentRoute);
  });
}

// Load year dropdown options
async function loadYearDropdown() {
  try {
    const response = await authenticatedFetch(`${API_BASE}/years/`);
    const data = await response.json();
    const yearSelector = document.getElementById('year-selector');
    
    if (!yearSelector || !data.years || data.years.length === 0) return;
    
    // Clear existing options
    yearSelector.innerHTML = '';
    
    // Get currently selected year from localStorage or use first year (newest)
    const savedYear = localStorage.getItem('selectedYear');
    const defaultYear = savedYear || data.years[0].toString();
    
    // Add year options
    data.years.forEach(year => {
      const option = document.createElement('option');
      option.value = year;
      option.textContent = year;
      if (year.toString() === defaultYear) {
        option.selected = true;
      }
      yearSelector.appendChild(option);
    });
    
    // Save default year if none was saved before
    if (!savedYear && data.years.length > 0) {
      localStorage.setItem('selectedYear', data.years[0].toString());
    }
    
    // Add change event listener
    yearSelector.addEventListener('change', (e) => {
      const selectedYear = e.target.value;
      if (selectedYear) {
        localStorage.setItem('selectedYear', selectedYear);
        // Trigger custom event for year change
        window.dispatchEvent(new CustomEvent('yearChanged', { detail: { year: selectedYear } }));
      }
    });
    
  } catch (error) {
    console.error('Failed to load years:', error);
  }
}

// Load shared header into placeholder
async function loadTopNav(currentRoute) {
  const headerContainer = document.getElementById('header-container');
  if (!headerContainer) return;
  try {
    const headerRes = await fetch('header.html', { cache: 'no-cache' });
    if (!headerRes.ok) throw new Error(`HTTP ${headerRes.status}`);
    const headerHtml = await headerRes.text();
    headerContainer.innerHTML = headerHtml;
    setActiveNav(currentRoute);
    
    // Update user info display
    const usernameDisplay = document.getElementById('username-display');
    if (usernameDisplay) {
      const username = getCurrentUsername();
      const db = getCurrentDatabase();
      usernameDisplay.textContent = `${username} (${db})`;
    }
    
    // Add event listener to theme toggle button after nav is loaded
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', toggleTheme);
    }

    // Load year dropdown after nav is loaded
    await loadYearDropdown();
    
    // Load help modal
    await loadHelpModal();
  } catch (e) {
    console.error('Failed to load header:', e);
  }
}

// Load help modal HTML and initialize
async function loadHelpModal() {
  try {
    const res = await fetch('help_modal.html', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    
    // Create a container for the modal and inject it
    let modalContainer = document.getElementById('help-modal-container');
    if (!modalContainer) {
      modalContainer = document.createElement('div');
      modalContainer.id = 'help-modal-container';
      document.body.appendChild(modalContainer);
    }
    modalContainer.innerHTML = html;
  } catch (e) {
    console.error('Failed to load help modal:', e);
  }
}

// Initialize theme on all pages
document.addEventListener('DOMContentLoaded', () => { loadTheme(); });

