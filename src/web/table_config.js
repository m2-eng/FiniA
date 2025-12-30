// Zentrale Tabellen-Konfiguration - wiederverwendbar für alle Seiten
const TABLE_CONFIGS = {
  'balances-table': {
    endpoint: '/year-overview/account-balances',
    yearLabelId: 'balances-year-label',
    feedbackId: 'balances-feedback',
    title: 'Kontostand'
  },
  'monthly-table': {
    endpoint: '/year-overview/account-balances-monthly',
    yearLabelId: 'monthly-year-label',
    feedbackId: 'monthly-feedback',
    title: 'Bilanz'
  },
  'loans-table': {
    endpoint: '/year-overview/loans',
    yearLabelId: 'loans-year-label',
    feedbackId: 'loans-feedback',
    title: 'Darlehen'
  },
  'securities-table': {
    endpoint: '/year-overview/securities',
    yearLabelId: 'securities-year-label',
    feedbackId: 'securities-feedback',
    title: 'Wertpapiere'
  },
  'income-table': {
    endpoint: '/accounts/income',
    yearLabelId: 'income-year-label',
    feedbackId: 'income-feedback',
    title: 'Haben',
    requiresAccount: true
  },
  'expenses-table': {
    endpoint: '/accounts/expenses',
    yearLabelId: 'expenses-year-label',
    feedbackId: 'expenses-feedback',
    title: 'Soll',
    requiresAccount: true
  }
  ,
  'summary-table': {
    endpoint: '/accounts/summary',
    yearLabelId: 'summary-year-label',
    feedbackId: 'summary-feedback',
    title: 'Gesamtbilanz',
    requiresAccount: true
  }
};
