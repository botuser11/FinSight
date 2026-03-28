const CATEGORY_STYLES = {
  Groceries:     { bg: '#E1F5EE', text: '#1D9E75' },
  Transport:     { bg: '#EEEDFE', text: '#534AB7' },
  Dining:        { bg: '#FAEEDA', text: '#BA7517' },
  Subscriptions: { bg: '#FAECE7', text: '#D85A30' },
  Utilities:     { bg: '#E6F1FB', text: '#378ADD' },
  Income:        { bg: '#E1F5EE', text: '#1D9E75' },
  Other:         { bg: '#F1F1EF', text: '#6B7280' },
}

export const CATEGORY_COLORS = {
  Groceries: '#1D9E75',
  Transport: '#534AB7',
  Dining: '#BA7517',
  Subscriptions: '#D85A30',
  Utilities: '#378ADD',
  Income: '#1D9E75',
  Other: '#888780',
}

export default function CategoryBadge({ name, onClick, className = '' }) {
  const style = CATEGORY_STYLES[name] || CATEGORY_STYLES.Other
  return (
    <span
      onClick={onClick}
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${onClick ? 'cursor-pointer hover:opacity-80' : ''} ${className}`}
      style={{ backgroundColor: style.bg, color: style.text }}
    >
      {name || 'Uncategorised'}
    </span>
  )
}
