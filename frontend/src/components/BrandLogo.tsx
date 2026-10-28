import type { SVGProps } from 'react'

export interface BrandLogoProps extends SVGProps<SVGSVGElement> {
  size?: number
}

/**
 * Layered Liquid-Glass App Icon for Douyin Crawler.
 * Combines the Douyin harmonic pulse ("d" / musical note), a translucent
 * media stream echo layer, and a central play/capture prism.
 */
export function BrandLogo({ size = 28, className, ...props }: BrandLogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
      aria-hidden="true"
      className={className}
      {...props}
    >
      <defs>
        <linearGradient
          id="brand-logo-bg"
          x1="8"
          y1="4"
          x2="56"
          y2="60"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor="#232631" />
          <stop offset="100%" stopColor="#0D0E12" />
        </linearGradient>
        <linearGradient
          id="brand-logo-rim"
          x1="0"
          y1="0"
          x2="64"
          y2="64"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.06" />
        </linearGradient>
        <linearGradient
          id="brand-logo-fg"
          x1="16"
          y1="10"
          x2="48"
          y2="54"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="100%" stopColor="#D5D8E2" />
        </linearGradient>
      </defs>

      {/* Squircle Base */}
      <rect x="2" y="2" width="60" height="60" rx="15" fill="url(#brand-logo-bg)" />
      <rect
        x="2.75"
        y="2.75"
        width="58.5"
        height="58.5"
        rx="14.25"
        stroke="url(#brand-logo-rim)"
        strokeWidth="1.5"
      />

      {/* Secondary Translucent Echo Layer */}
      <path
        d="M34.5 14.5 C34.5 13.4 35.4 12.5 36.5 12.5 H38.8 C39.8 12.5 40.6 13.2 40.9 14.1 C42.1 18.8 46.0 22.2 50.9 22.9 C51.9 23.0 52.6 23.9 52.6 24.9 V27.6 C52.6 28.8 51.5 29.7 50.3 29.5 C46.5 29.0 43.1 27.4 40.5 25.0 V39.0 A 13.5 13.5 0 1 1 27.0 25.5 A 3.0 3.0 0 0 1 27.0 31.5 A 7.5 7.5 0 1 0 34.5 39.0 V14.5Z"
        fill="#9497A1"
        fillOpacity="0.35"
      />

      {/* Primary Exact-Tangent Douyin Note + Capture Loop */}
      <path
        d="M31.8 12.8 C31.8 11.5 32.8 10.5 34.1 10.5 H36.2 C37.2 10.5 38.1 11.2 38.4 12.2 C39.6 16.9 43.5 20.4 48.5 21.1 C49.6 21.3 50.4 22.2 50.4 23.3 V26.0 C50.4 27.3 49.3 28.3 48.0 28.1 C44.1 27.6 40.6 25.9 38.0 23.4 V37.5 A 13.5 13.5 0 1 1 24.5 24.0 A 3.1 3.1 0 0 1 24.5 30.2 A 7.3 7.3 0 1 0 31.8 37.5 V12.8Z"
        fill="url(#brand-logo-fg)"
      />

      {/* Center Play / Capture Prism */}
      <path
        d="M22.2 34.3 C22.2 33.4 23.2 32.9 23.9 33.3 L29.1 36.4 C29.8 36.8 29.8 37.9 29.1 38.3 L23.9 41.4 C23.2 41.8 22.2 41.3 22.2 40.4 V34.3Z"
        fill="#FFFFFF"
      />
    </svg>
  )
}
