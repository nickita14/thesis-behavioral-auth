import { BRAND } from '@/brand'

interface LogoProps {
  variant?: 'full' | 'mark' | 'white'
  size?: 'sm' | 'md' | 'lg'
}

export function Logo({ variant = 'full', size = 'md' }: LogoProps) {
  const sizes = {
    sm: { mark: 24, fontSize: 14 },
    md: { mark: 32, fontSize: 18 },
    lg: { mark: 48, fontSize: 24 },
  }
  const s = sizes[size]
  const isWhite = variant === 'white'
  const markColor = isWhite ? '#ffffff' : BRAND.colors.primary
  const textColor = isWhite ? '#ffffff' : BRAND.colors.primary
  const letterColor = isWhite ? BRAND.colors.primary : BRAND.colors.accent

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <svg
        width={s.mark}
        height={s.mark}
        viewBox="0 0 32 32"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path
          d="M16 2 L28 8 L28 16 C28 22 22 28 16 30 C10 28 4 22 4 16 L4 8 Z"
          fill={markColor}
          stroke={isWhite ? 'rgba(255,255,255,0.3)' : BRAND.colors.primaryDark}
          strokeWidth="1.5"
        />
        <text
          x="16"
          y="22"
          textAnchor="middle"
          fontSize="18"
          fontWeight="700"
          fill={letterColor}
          fontFamily="-apple-system, BlinkMacSystemFont, sans-serif"
        >
          S
        </text>
      </svg>
      {variant !== 'mark' && (
        <span
          style={{
            fontSize: s.fontSize,
            fontWeight: 700,
            color: textColor,
            letterSpacing: '-0.02em',
            lineHeight: 1,
          }}
        >
          Sigur Bank
        </span>
      )}
    </div>
  )
}
