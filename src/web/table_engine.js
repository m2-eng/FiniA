// Zentrale Tabellen-Engine mit Retry-Logik und Fehlerbehandlung
class TableEngine {
  constructor(config) {
    this.config = config;
    this.retryAttempts = 2;
    this.retryDelay = 1000; // ms
  }

  /**
   * Fetch mit automatischem Retry bei 503-Fehlern oder Netzwerkproblemen
   */
  async fetchWithRetry(url, attempt = 0) {
    try {
      const res = await fetch(url);
      if (!res.ok) {
        // Bei 503 (Service Unavailable) retry
        if (res.status === 503 && attempt < this.retryAttempts) {
          console.warn(`Retry ${attempt + 1}/${this.retryAttempts} für ${url} nach 503`);
          await this.sleep(this.retryDelay * (attempt + 1));
          return this.fetchWithRetry(url, attempt + 1);
        }
        const body = await res.text();
        throw new Error(`HTTP ${res.status} - ${body}`);
      }
      return await res.json();
    } catch (err) {
      // Bei Netzwerkfehlern ebenfalls retry
      if (attempt < this.retryAttempts && (err.name === 'TypeError' || err.message.includes('fetch'))) {
        console.warn(`Retry ${attempt + 1}/${this.retryAttempts} nach Netzwerkfehler:`, err.message);
        await this.sleep(this.retryDelay * (attempt + 1));
        return this.fetchWithRetry(url, attempt + 1);
      }
      throw err;
    }
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Setzt Feedback-Nachricht für eine Tabelle
   */
  setFeedback(tableId, message, tone = 'muted') {
    const config = this.config[tableId];
    if (!config) return;
    const feedback = document.getElementById(config.feedbackId);
    if (!feedback) return;
    feedback.textContent = message || '';
    feedback.style.color = tone === 'error' ? '#c62828' : 'inherit';
  }

  /**
   * Setzt Jahr-Label für eine Tabelle
   */
  setYearLabel(tableId, year) {
    const config = this.config[tableId];
    if (!config) return;
    const label = document.getElementById(config.yearLabelId);
    if (label) label.textContent = `Aktuelles Jahr: ${year}`;
  }

  /**
   * Lädt eine einzelne Tabelle mit Daten
   */
  async loadTable(tableId, year, account = null) {
    const config = this.config[tableId];
    if (!config) {
      console.error(`Keine Konfiguration für Tabelle: ${tableId}`);
      return;
    }

    this.setFeedback(tableId, 'Lade Daten...');
    
    try {
      let url = `${API_BASE}${config.endpoint}?year=${year}`;
      if (config.requiresAccount && account) {
        url += `&account=${encodeURIComponent(account)}`;
      }
      
      const data = await this.fetchWithRetry(url);
      const rows = data.rows || [];
      
      this.setYearLabel(tableId, year);
      
      if (rows.length === 0) {
        this.setFeedback(tableId, 'Keine Daten für dieses Jahr gefunden.');
      } else {
        this.setFeedback(tableId, '');
      }
      
      // Render-Funktion muss global verfügbar sein
      if (typeof renderTableGeneric === 'function') {
        renderTableGeneric(tableId, rows);
      } else {
        console.error('renderTableGeneric ist nicht verfügbar');
      }
    } catch (err) {
      console.error(`Fehler beim Laden von ${config.title}:`, err);
      this.setFeedback(tableId, 'Fehler beim Laden der Daten.', 'error');
    }
  }

  /**
   * Lädt mehrere Tabellen parallel für bessere Performance
   */
  async loadAllTables(year, tableIds, account = null) {
    await Promise.all(
      tableIds.map(id => this.loadTable(id, year, account))
    );
  }

  /**
   * Lädt mehrere Tabellen nacheinander (sequentiell) für geringere Serverlast
   */
  async loadTablesSequential(year, tableIds, account = null) {
    for (const id of tableIds) {
      await this.loadTable(id, year, account);
    }
  }
}
