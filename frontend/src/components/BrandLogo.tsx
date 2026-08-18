interface BrandLogoProps {
  /** Rendered size in px. The asset is 192px, so it stays crisp up to 96px at 2x. */
  size?: number
  className?: string
}

/**
 * The InsightDocs mark.
 *
 * Uses the 192px export rather than the 1254px master so a sidebar icon does
 * not pull a 659 KB image. The master lives in `frontend/brand/` and is not
 * served or bundled.
 */
export function BrandLogo({ size = 32, className = '' }: BrandLogoProps) {
  return (
    <img
      src="/logo-192.png"
      width={size}
      height={size}
      alt="InsightDocs"
      loading="eager"
      decoding="async"
      className={`shrink-0 select-none object-contain ${className}`}
      style={{ width: size, height: size }}
    />
  )
}
