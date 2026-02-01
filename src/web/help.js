// Help Modal Handler with Markdown rendering and search functionality

// State
let helpDocuments = [];
let allDocs = [];
let currentDocId = null;
let docCache = {}; // Cache loaded documents

// Load and display help modal
async function openHelpModal() {
  const modal = document.getElementById('help-modal');
  if (!modal) {
    console.error('Help modal not found');
    return;
  }
  
  modal.style.display = 'block';
  
  // Initialize if not done yet
  if (helpDocuments.length === 0) {
    await initializeHelpModal();
  }
  
  // Set API Docs link
  const apiLink = document.getElementById('api-docs-link');
  if (apiLink) {
    apiLink.href = getApiDocsUrl();
  }
  
  // Prevent body scroll
  document.body.style.overflow = 'hidden';
}

// Close help modal
function closeHelpModal() {
  const modal = document.getElementById('help-modal');
  if (modal) {
    modal.style.display = 'none';
  }
  document.body.style.overflow = 'auto';
  document.getElementById('help-search').value = '';
}

// Initialize help modal on first open
async function initializeHelpModal() {
  // Use documents from help_documents.js
  if (typeof HELP_DOCUMENTS === 'undefined') {
    console.error('HELP_DOCUMENTS not found. Make sure help_documents.js is loaded.');
    return;
  }
  
  helpDocuments = HELP_DOCUMENTS;
  allDocs = [...helpDocuments];
  
  await renderDocumentList(helpDocuments);
  
  // Load first document by default
  if (helpDocuments.length > 0) {
    loadHelpDocument(helpDocuments[0].id);
  }
}

// Render document list in sidebar
async function renderDocumentList(docs) {
  const docList = document.getElementById('help-doc-list');
  if (!docList) return;
  
  docList.innerHTML = '';
  
  if (docs.length === 0) {
    docList.innerHTML = '<li class="help-no-results">Keine Dokumente gefunden</li>';
    return;
  }
  
  // Group documents by category
  const grouped = groupBy(docs, 'category');
  
  Object.keys(grouped).sort().forEach(category => {
    const categoryDocs = grouped[category];
    
    categoryDocs.forEach((doc, index) => {
      const li = document.createElement('li');
      li.className = 'help-doc-item';
      
      const link = document.createElement('a');
      link.className = 'help-doc-link';
      link.href = '#';
      link.textContent = doc.title;
      link.onclick = (e) => {
        e.preventDefault();
        loadHelpDocument(doc.id);
      };
      
      li.appendChild(link);
      docList.appendChild(li);
    });
  });
}

// Load and display a specific document
async function loadHelpDocument(docId) {
  currentDocId = docId;
  const doc = helpDocuments.find(d => d.id === docId);
  
  if (!doc) {
    console.error('Document not found:', docId);
    return;
  }
  
  // Update active link
  document.querySelectorAll('.help-doc-link').forEach(link => {
    link.classList.remove('active');
  });
  document.querySelectorAll('.help-doc-link').forEach(link => {
    if (link.textContent === doc.title) {
      link.classList.add('active');
    }
  });
  
  // Load content
  const contentDiv = document.getElementById('help-content');
  
  try {
    // Check cache first
    if (docCache[docId]) {
      contentDiv.innerHTML = docCache[docId];
      return;
    }
    
    contentDiv.innerHTML = '<p>Lädt...</p>';
    
    // Construct the API URL dynamically
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    let apiBaseUrl = `${protocol}//${hostname}`;
    if (port) {
      apiBaseUrl += `:${port}`;
    }
    
    const docUrl = `${apiBaseUrl}/api/docs/${doc.file}`;
    const response = await fetch(docUrl);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const markdown = await response.text();
    const html = markdownToHtml(markdown);
    
    // Cache the result
    docCache[docId] = html;
    
    contentDiv.innerHTML = html;
  } catch (error) {
    console.error('Error loading document:', error);
    contentDiv.innerHTML = `<p style="color: var(--color-danger);">Fehler beim Laden des Dokuments: ${error.message}</p>`;
  }
}

// Search help documents
function searchHelpDocs() {
  const searchTerm = document.getElementById('help-search').value.toLowerCase();
  
  if (!searchTerm) {
    renderDocumentList(allDocs);
    return;
  }
  
  const filtered = allDocs.filter(doc => 
    doc.title.toLowerCase().includes(searchTerm) ||
    doc.category.toLowerCase().includes(searchTerm)
  );
  
  renderDocumentList(filtered);
  
  // Load first result if search was successful
  if (filtered.length > 0 && currentDocId !== filtered[0].id) {
    loadHelpDocument(filtered[0].id);
  }
}

// Simple Markdown to HTML converter
function markdownToHtml(markdown) {
  let html = markdown;
  
  // Escape HTML
  html = html.replace(/&/g, '&amp;')
             .replace(/</g, '&lt;')
             .replace(/>/g, '&gt;');
  
  // Headers
  html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__( .*?)__/g, '<strong>$1</strong>');
  
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.*?)_/g, '<em>$1</em>');
  
  // Code blocks (preserve line breaks in code)
  html = html.replace(/```(.*?)```/gs, (match, code) => {
    const escaped = code.trim()
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    return `<pre><code>${escaped}</code></pre>`;
  });
  
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Links
  html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
  
  // Unordered lists
  html = html.replace(/^\s*[-*+] (.*?)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*?<\/li>)/s, (match) => {
    return '<ul>' + match + '</ul>';
  });
  
  // Ordered lists
  html = html.replace(/^\s*\d+\. (.*?)$/gm, '<li>$1</li>');
  
  // Paragraphs
  html = html.replace(/\n\n+/g, '</p><p>');
  html = '<p>' + html + '</p>';
  
  // Clean up empty paragraphs
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p><h/g, '<h');
  html = html.replace(/<\/h(.*?)><p>/g, '<\/h$1>');
  html = html.replace(/<p><ul>/g, '<ul>');
  html = html.replace(/<\/ul><p>/g, '<\/ul>');
  html = html.replace(/<p><pre>/g, '<pre>');
  html = html.replace(/<\/pre><p>/g, '<\/pre>');
  
  return html;
}

// Utility function to group array by property
function groupBy(array, property) {
  return array.reduce((groups, item) => {
    const key = item[property];
    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(item);
    return groups;
  }, {});
}

// Close modal when clicking outside
window.addEventListener('click', (event) => {
  const modal = document.getElementById('help-modal');
  if (event.target === modal) {
    closeHelpModal();
  }
});

// Close modal with Escape key
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    closeHelpModal();
  }
});
