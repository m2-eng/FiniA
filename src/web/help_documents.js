// Help Documentation Index
// Maps display names to document files and metadata
const HELP_DOCUMENTS = [
  {
    id: 'getting-started',
    title: 'Erste Schritte',
    file: 'tutorials/getting_started.md',
    category: 'Tutorials'
  },
  {
    id: 'setup',
    title: 'Installation & Setup',
    file: 'development/setup.md',
    category: 'Development'
  },
  {
    id: 'authentication',
    title: 'Authentifizierung',
    file: 'authentication.md',
    category: 'Features'
  },
  {
    id: 'config',
    title: 'Konfiguration',
    file: 'cfg/config.md',
    category: 'Konfiguration'
  },
  {
    id: 'data-import',
    title: 'Datenimport Formate',
    file: 'cfg/import_formats.md',
    category: 'Konfiguration'
  },
  {
    id: 'database-schema',
    title: 'Datenbank Schema',
    file: 'database/schema.md',
    category: 'Architektur'
  },
  {
    id: 'repositories',
    title: 'Repositories',
    file: 'architecture/repositories.md',
    category: 'Architektur'
  },
  {
    id: 'services',
    title: 'Services',
    file: 'architecture/services.md',
    category: 'Architektur'
  },
  {
    id: 'category-automation',
    title: 'Kategorie-Automation',
    file: 'features/category_automation.md',
    category: 'Features'
  },
  {
    id: 'category-automation-rules',
    title: 'Kategorie-Automations-Regeln',
    file: 'features/category-automation-rules.md',
    category: 'Features'
  },
  {
    id: 'planning',
    title: 'Finanzielle Planung',
    file: 'features/planning.md',
    category: 'Features'
  },
  {
    id: 'shares',
    title: 'Aktien & Wertpapiere',
    file: 'features/shares.md',
    category: 'Features'
  },
  {
    id: 'csv-import',
    title: 'CSV Import',
    file: 'import/csv_import.md',
    category: 'Import'
  },
  {
    id: 'backup',
    title: 'Sicherung & Backup',
    file: 'backup.md',
    category: 'Betrieb'
  },
  {
    id: 'docker',
    title: 'Docker',
    file: 'docker/docker.md',
    category: 'Deployment'
  },
  {
    id: 'docker-getting-started',
    title: 'Docker - Erste Schritte',
    file: 'docker/getting_started.md',
    category: 'Deployment'
  },
  {
    id: 'production',
    title: 'Produktion Setup',
    file: 'deployment/production.md',
    category: 'Deployment'
  },
  {
    id: 'troubleshooting',
    title: 'Fehlerbehebung',
    file: 'troubleshooting.md',
    category: 'Support'
  },
  {
    id: 'review',
    title: 'Code Review Richtlinien',
    file: 'review.md',
    category: 'Development'
  }
];

// Get the current API base URL dynamically
function getApiDocsUrl() {
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = window.location.port;
  
  // Reconstruct the API URL based on current location
  let apiUrl = `${protocol}//${hostname}`;
  if (port) {
    apiUrl += `:${port}`;
  }
  
  return `${apiUrl}/api/docs`;
}
