// Utility styles for theme-aware components
// Use these as className combinations or inline styles

export const themeStyles = {
  // Cards
  card: {
    backgroundColor: 'var(--surface)',
    borderColor: 'var(--border)',
    border: '1px solid var(--border)',
    borderRadius: '2px'
  },
  
  // Text colors
  textPrimary: { color: 'var(--text-primary)' },
  textSecondary: { color: 'var(--text-secondary)' },
  textMuted: { color: 'var(--text-muted)' },
  
  // Backgrounds
  bgPrimary: { backgroundColor: 'var(--bg-primary)' },
  bgSecondary: { backgroundColor: 'var(--bg-secondary)' },
  surface: { backgroundColor: 'var(--surface)' },
  
  // Borders
  border: { borderColor: 'var(--border)' },
  borderStrong: { borderColor: 'var(--border-strong)' },
  
  // Input
  input: {
    backgroundColor: 'var(--surface)',
    borderColor: 'var(--border)',
    color: 'var(--text-primary)'
  },
  
  // Table
  tableHeader: {
    backgroundColor: 'var(--bg-secondary)',
    borderColor: 'var(--border)'
  },
  tableRow: {
    backgroundColor: 'var(--surface)',
    borderColor: 'var(--border)'
  },
  
  // Accents
  accentBlue: { color: 'var(--accent-blue)' },
  accentOrange: { color: 'var(--accent-orange)' },
  
  // Status
  success: { backgroundColor: 'var(--success-bg)', color: 'var(--success)' },
  warning: { backgroundColor: 'var(--warning-bg)', color: 'var(--warning)' },
  error: { backgroundColor: 'var(--error-bg)', color: 'var(--error)' },
  info: { backgroundColor: 'var(--info-bg)', color: 'var(--info)' }
};

// Combine multiple style objects
export const mergeStyles = (...styles) => {
  return Object.assign({}, ...styles);
};

// Common className combinations
export const classNames = {
  card: 'card hover-lift animate-fade-in-up',
  cardStatic: 'card',
  button: 'btn-primary hover-lift',
  input: 'input rounded-sm px-3 py-2 text-sm',
  table: 'table-wrapper',
  badge: 'px-2 py-0.5 rounded text-xs font-medium'
};
