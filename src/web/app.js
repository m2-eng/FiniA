// Shared app utilities
const API_BASE = '/api';

// Central auth guard for all protected pages (login.html does not load app.js)
requireAuth();

// Theme Management
function initTheme() {
  // Load saved theme or default to dark
  const savedTheme = localStorage.getItem('theme') || 'dark';
  applyTheme(savedTheme);
  updateThemeIcon(savedTheme);
}

function applyTheme(theme) {
  if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  localStorage.setItem('theme', theme);
}

function toggleTheme() {
  const currentTheme = localStorage.getItem('theme') || 'dark';
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
  if (!requireAuth()) return;
  const headerContainer = document.getElementById('header-container');
  if (!headerContainer) return;
  try {
    const headerRes = await fetch('top_nav.html', { cache: 'no-cache' });
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
  if (!requireAuth()) return;
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

// Migration flow after login
document.addEventListener('DOMContentLoaded', () => {
  window.migrationsReady = checkMigrations();
});

async function checkMigrations() {
  if (!requireAuth()) return false;

  try {
    const response = await fetch(`${API_BASE}/setup/migrations/status`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) return true;

    const status = await response.json();

    if (!status || status.pending_count === 0) return true;

    if (status.is_initial) {
      const proceed = await showMigrationDialog({
        title: 'Datenbankinitialisierung erforderlich',
        message: 'Die Datenbank ist noch nicht initialisiert. Das System wird sie jetzt initialisieren.',
        confirmText: 'Fortfahren',
        cancelText: 'Abbrechen'
      });

      if (!proceed) {
        await logout();
        return false;
      }

      await applyMigrations();
      return true;
    }

    if (status.needs_upgrade) {
      const proceed = await showMigrationDialog({
        title: 'Datenbankaktualisierung erforderlich',
        message: 'Eine neue Datenbankversion ist verfügbar. Erstellen Sie bitte ein Backup, bevor Sie fortfahren.',
        confirmText: 'Fortfahren',
        cancelText: 'Abbrechen'
      });

      if (!proceed) {
        await logout();
        return false;
      }

      const confirmed = await showMigrationDialog({
        title: 'Backup bestätigen',
        message: 'Bitte bestätigen Sie, dass Sie ein Backup der Datenbank erstellt haben.',
        confirmText: 'Ich habe ein Backup',
        cancelText: 'Abbrechen'
      });

      if (!confirmed) {
        await logout();
        return false;
      }

      await applyMigrations();
      return true;
    }
  } catch (error) {
    console.error('Migration status check failed:', error);
  }

  return true;
}

async function applyMigrations() {
  const progress = showMigrationProgressDialog();

  try {
    window._migrationBypass = true;
    const response = await authenticatedFetch(`${API_BASE}/setup/migrations/apply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ dry_run: false })
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Migration fehlgeschlagen');
    }

    // Handle Server-Sent Events (SSE) streaming response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      
      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.substring(6));
            progress.update(event);
            
            // If we got a completion or error, exit the loop
            if (event.phase === 'complete' || event.phase === 'error') {
              break;
            }
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  } catch (error) {
    console.error('Migration failed:', error);
    await showMigrationDialog({
      title: 'Migration fehlgeschlagen',
      message: 'Die Datenbankmigration ist fehlgeschlagen. Sie werden abgemeldet.',
      confirmText: 'OK',
      showCancel: false
    });
    await logout();
  } finally {
    window._migrationBypass = false;
    progress.close();
  }
}

function showMigrationDialog({ title, message, confirmText, cancelText, showCancel = true }) {
  return new Promise((resolve) => {
    const modal = createMigrationModal();

    modal.title.textContent = title;
    modal.message.textContent = message;

    modal.confirmButton.textContent = confirmText || 'Fortfahren';
    modal.cancelButton.textContent = cancelText || 'Abbrechen';
    modal.cancelButton.style.display = showCancel ? 'inline-block' : 'none';

    const cleanup = () => {
      modal.overlay.remove();
    };

    modal.confirmButton.onclick = () => {
      cleanup();
      resolve(true);
    };

    modal.cancelButton.onclick = () => {
      cleanup();
      resolve(false);
    };
  });
}

function showMigrationProgressDialog() {
  const existing = document.getElementById('migration-modal-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'migration-modal-overlay';
  overlay.style.position = 'fixed';
  overlay.style.top = '0';
  overlay.style.left = '0';
  overlay.style.width = '100%';
  overlay.style.height = '100%';
  overlay.style.background = 'rgba(0, 0, 0, 0.45)';
  overlay.style.display = 'flex';
  overlay.style.alignItems = 'center';
  overlay.style.justifyContent = 'center';
  overlay.style.zIndex = '9999';

  const modal = document.createElement('div');
  modal.style.background = 'var(--color-bg-detail)';
  modal.style.color = 'var(--color-text)';
  modal.style.padding = '24px';
  modal.style.borderRadius = '8px';
  modal.style.width = 'min(520px, 92vw)';
  modal.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.2)';
  modal.style.border = '1px solid var(--color-border)';

  const title = document.createElement('h2');
  title.textContent = 'Migrationen werden angewendet';
  title.style.margin = '0 0 16px 0';
  title.style.fontSize = '18px';
  title.style.fontWeight = '500';
  title.style.color = 'var(--color-text-selected)';

  // Progress bar container
  const progressContainer = document.createElement('div');
  progressContainer.style.marginBottom = '16px';

  const progressLabel = document.createElement('div');
  progressLabel.style.fontSize = '12px';
  progressLabel.style.color = 'var(--color-text)';
  progressLabel.style.marginBottom = '6px';
  progressLabel.style.display = 'flex';
  progressLabel.style.justifyContent = 'space-between';

  const progressLabelText = document.createElement('span');
  progressLabelText.textContent = 'Fortschritt:';

  const progressPercent = document.createElement('span');
  progressPercent.textContent = '0%';
  progressPercent.style.fontWeight = 'bold';

  progressLabel.appendChild(progressLabelText);
  progressLabel.appendChild(progressPercent);

  const progressBar = document.createElement('div');
  progressBar.style.width = '100%';
  progressBar.style.height = '8px';
  progressBar.style.background = 'var(--color-border)';
  progressBar.style.borderRadius = '4px';
  progressBar.style.overflow = 'hidden';
  progressBar.style.marginBottom = '8px';

  const progressFill = document.createElement('div');
  progressFill.style.width = '0%';
  progressFill.style.height = '100%';
  progressFill.style.background = 'var(--color-accent)';
  progressFill.style.transition = 'width 0.3s ease';

  progressBar.appendChild(progressFill);
  progressContainer.appendChild(progressLabel);
  progressContainer.appendChild(progressBar);

  // Info message about duration
  const infoMessage = document.createElement('p');
  infoMessage.style.margin = '12px 0 0 0';
  infoMessage.style.lineHeight = '1.4';
  infoMessage.style.color = 'var(--color-text)';
  infoMessage.style.fontSize = '12px';
  infoMessage.style.opacity = '0.8';
  infoMessage.textContent = 'Hinweis: Die Datenbankinitialisierung kann einige Sekunden dauern...';

  modal.appendChild(title);
  modal.appendChild(progressContainer);
  modal.appendChild(infoMessage);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  // Return object with update and close methods
  return {
    overlay,
    modal,
    update(event) {
      if (event.phase === 'executing' || event.phase === 'preparing') {
        // Update progress bar
        if (event.total > 0) {
          const percent = Math.round((event.current / event.total) * 100);
          progressFill.style.width = percent + '%';
          progressPercent.textContent = percent + '%';
        }
      } else if (event.phase === 'complete') {
        progressFill.style.width = '100%';
        progressPercent.textContent = '100%';
        title.textContent = '✓ Fertig!';
      } else if (event.phase === 'error') {
        progressFill.style.background = 'var(--color-danger)';
        title.textContent = '✗ Fehler';
      }
    },
    close() {
      overlay.remove();
    }
  };
}

function showMigrationProgress(title, message) {
  const modal = createMigrationModal();
  modal.title.textContent = title;
  modal.message.textContent = message;
  modal.confirmButton.style.display = 'none';
  modal.cancelButton.style.display = 'none';

  return () => {
    modal.overlay.remove();
  };
}

function createMigrationModal() {
  const existing = document.getElementById('migration-modal-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'migration-modal-overlay';
  overlay.style.position = 'fixed';
  overlay.style.top = '0';
  overlay.style.left = '0';
  overlay.style.width = '100%';
  overlay.style.height = '100%';
  overlay.style.background = 'rgba(0, 0, 0, 0.45)';
  overlay.style.display = 'flex';
  overlay.style.alignItems = 'center';
  overlay.style.justifyContent = 'center';
  overlay.style.zIndex = '9999';

  const modal = document.createElement('div');
  modal.style.background = 'var(--color-bg-detail)';
  modal.style.color = 'var(--color-text)';
  modal.style.padding = '24px';
  modal.style.borderRadius = '8px';
  modal.style.width = 'min(520px, 92vw)';
  modal.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.2)';
  modal.style.border = '1px solid var(--color-border)';

  const title = document.createElement('h2');
  title.style.margin = '0 0 12px 0';
  title.style.fontSize = '20px';
  title.style.fontWeight = '500';
  title.style.color = 'var(--color-text-selected)';

  const message = document.createElement('p');
  message.style.margin = '0 0 20px 0';
  message.style.lineHeight = '1.4';
  message.style.color = 'var(--color-text)';

  const actions = document.createElement('div');
  actions.style.display = 'flex';
  actions.style.justifyContent = 'flex-end';
  actions.style.gap = '12px';

  const cancelButton = document.createElement('button');
  cancelButton.textContent = 'Abbrechen';
  cancelButton.style.padding = '8px 16px';
  cancelButton.style.background = 'var(--color-bg-base)';
  cancelButton.style.color = 'var(--color-text)';
  cancelButton.style.border = '1px solid var(--color-border)';
  cancelButton.style.borderRadius = '4px';
  cancelButton.style.cursor = 'pointer';
  cancelButton.style.fontFamily = 'inherit';
  cancelButton.style.fontSize = '14px';
  cancelButton.style.transition = 'background-color 0.2s ease';
  cancelButton.onmouseover = () => {
    cancelButton.style.background = 'var(--color-border)';
  };
  cancelButton.onmouseout = () => {
    cancelButton.style.background = 'var(--color-bg-base)';
  };

  const confirmButton = document.createElement('button');
  confirmButton.textContent = 'Fortfahren';
  confirmButton.style.padding = '8px 16px';
  confirmButton.style.background = 'var(--color-accent)';
  confirmButton.style.color = 'var(--color-text-selected)';
  confirmButton.style.border = 'none';
  confirmButton.style.borderRadius = '4px';
  confirmButton.style.cursor = 'pointer';
  confirmButton.style.fontFamily = 'inherit';
  confirmButton.style.fontSize = '14px';
  confirmButton.style.fontWeight = '500';
  confirmButton.style.transition = 'background-color 0.2s ease';
  confirmButton.onmouseover = () => {
    confirmButton.style.background = 'var(--color-accent-hover)';
  };
  confirmButton.onmouseout = () => {
    confirmButton.style.background = 'var(--color-accent)';
  };

  actions.appendChild(cancelButton);
  actions.appendChild(confirmButton);

  modal.appendChild(title);
  modal.appendChild(message);
  modal.appendChild(actions);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  return { overlay, title, message, confirmButton, cancelButton };
}

