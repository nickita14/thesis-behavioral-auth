// Sigur Bank brand identity — used across all pages for consistent styling.
// Colors are also applied via CSS variables in index.css (--brand-*).
export const BRAND = {
  name: 'Sigur Bank',
  tagline: 'Безопасные транзакции с AI-аналитикой',

  colors: {
    primary: '#1e3a5f',
    primaryDark: '#0f2240',
    primaryLight: '#2e5180',
    accent: '#d4af37',
    accentDark: '#b8941f',
    success: '#2e7d32',
    warning: '#ed6c02',
    danger: '#c62828',
    bg: '#f5f7fa',
    surface: '#ffffff',
    border: '#e0e4e9',
    text: '#1a1a1a',
    textSecondary: '#5a6478',
  },

  mockAccount: {
    accountNumber: 'MD93 SBNK 0000 0123 4567 8901',
    balance: 24580.50,
    currency: 'MDL',
    accountType: 'Текущий счёт',
    holderName: 'Mironov Nichita',
  },

  mockHistory: [
    {
      id: 'TX-2026-001',
      date: '2026-05-15',
      recipient: 'Orange Moldova SA',
      amount: -290.00,
      status: 'allowed' as const,
      description: 'Оплата мобильной связи',
    },
    {
      id: 'TX-2026-002',
      date: '2026-05-12',
      recipient: 'Linella SRL',
      amount: -456.20,
      status: 'allowed' as const,
      description: 'Покупка в магазине',
    },
    {
      id: 'TX-2026-003',
      date: '2026-05-10',
      recipient: 'Ion Popescu',
      amount: 5000.00,
      status: 'allowed' as const,
      description: 'Поступление средств',
    },
    {
      id: 'TX-2026-004',
      date: '2026-05-08',
      recipient: 'Premier Energy',
      amount: -1250.00,
      status: 'challenge' as const,
      description: 'Оплата электроэнергии',
    },
  ],
} as const
