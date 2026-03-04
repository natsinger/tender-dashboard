/**
 * MEGIDO design system cva variant definitions.
 *
 * Reusable variant configurations for common component patterns.
 * These are NOT replacements for shadcn/ui components — they are
 * supplementary variants that can be composed with the shadcn base
 * or used standalone for custom components.
 *
 * Usage:
 *   import { megidoButton } from "@/design-system/variants";
 *   <button className={megidoButton({ intent: "primary", size: "md" })} />
 */

import { cva } from "class-variance-authority";

// ---------------------------------------------------------------------------
// Button variants
// ---------------------------------------------------------------------------

export const megidoButton = cva(
  [
    "inline-flex items-center justify-center gap-2",
    "rounded-md font-medium transition-all duration-150",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
    "disabled:pointer-events-none disabled:opacity-50",
    "whitespace-nowrap shrink-0",
    "[&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0",
  ],
  {
    variants: {
      intent: {
        primary: [
          "bg-[var(--megido-primary)] text-white",
          "hover:bg-[var(--megido-primary-hover)] hover:shadow-[0_4px_12px_-2px_rgba(37,99,235,0.20)]",
          "focus-visible:ring-[var(--megido-primary)]",
          "active:bg-[#1E40AF]",
        ],
        secondary: [
          "bg-[var(--megido-secondary)] text-[var(--megido-text-on-dark)]",
          "hover:bg-[#163152]",
          "focus-visible:ring-[var(--megido-secondary)]",
        ],
        ghost: [
          "bg-transparent text-[var(--megido-text-body)]",
          "hover:bg-[#F1F5F9] hover:text-[var(--megido-text-heading)]",
          "focus-visible:ring-[var(--megido-primary)]",
        ],
        danger: [
          "bg-[var(--megido-danger)] text-white",
          "hover:bg-[#DC2626]",
          "focus-visible:ring-[var(--megido-danger)]",
        ],
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-9 px-4 text-sm",
        lg: "h-10 px-6 text-base",
        icon: "size-9",
        "icon-sm": "size-8",
      },
    },
    defaultVariants: {
      intent: "primary",
      size: "md",
    },
  }
);

// ---------------------------------------------------------------------------
// Card variants
// ---------------------------------------------------------------------------

export const megidoCard = cva(
  [
    "rounded-xl text-[var(--megido-text-body)]",
    "transition-shadow duration-200",
  ],
  {
    variants: {
      variant: {
        default: [
          "bg-[var(--megido-bg-card)] border border-[var(--megido-border)]",
          "shadow-[0_4px_6px_-1px_rgba(0,0,0,0.07),0_2px_4px_-2px_rgba(0,0,0,0.05)]",
        ],
        elevated: [
          "bg-[var(--megido-bg-card)] border border-[var(--megido-border)]",
          "shadow-[0_10px_15px_-3px_rgba(0,0,0,0.08),0_4px_6px_-4px_rgba(0,0,0,0.04)]",
          "hover:shadow-[0_8px_16px_-4px_rgba(37,99,235,0.10),0_4px_8px_-4px_rgba(37,99,235,0.06)]",
        ],
        outlined: [
          "bg-transparent border-2 border-[var(--megido-border)]",
          "shadow-none",
        ],
        flat: [
          "bg-[var(--megido-bg-card)] border-none shadow-none",
        ],
      },
      padding: {
        none: "p-0",
        sm: "p-4",
        md: "p-6",
        lg: "p-8",
      },
    },
    defaultVariants: {
      variant: "default",
      padding: "md",
    },
  }
);

// ---------------------------------------------------------------------------
// Badge variants
// ---------------------------------------------------------------------------

export const megidoBadge = cva(
  [
    "inline-flex items-center justify-center",
    "rounded-full px-2.5 py-0.5",
    "text-xs font-medium whitespace-nowrap",
    "border transition-colors",
  ],
  {
    variants: {
      status: {
        success: [
          "bg-[#ECFDF5] text-[#065F46] border-[#A7F3D0]",
        ],
        warning: [
          "bg-[#FFFBEB] text-[#92400E] border-[#FDE68A]",
        ],
        danger: [
          "bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]",
        ],
        info: [
          "bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]",
        ],
        neutral: [
          "bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]",
        ],
      },
      size: {
        sm: "text-[10px] px-1.5 py-px",
        md: "text-xs px-2.5 py-0.5",
        lg: "text-sm px-3 py-1",
      },
    },
    defaultVariants: {
      status: "neutral",
      size: "md",
    },
  }
);

// ---------------------------------------------------------------------------
// Text variants
// ---------------------------------------------------------------------------

export const megidoText = cva("", {
  variants: {
    variant: {
      heading: [
        "font-semibold text-[var(--megido-text-heading)]",
        "leading-tight tracking-tight",
      ],
      body: [
        "font-normal text-[var(--megido-text-body)]",
        "leading-normal",
      ],
      label: [
        "font-medium text-[var(--megido-text-heading)]",
        "leading-none",
      ],
      muted: [
        "font-normal text-[var(--megido-text-muted)]",
        "leading-normal",
      ],
      "on-dark": [
        "font-normal text-[var(--megido-text-on-dark)]",
        "leading-normal",
      ],
    },
    size: {
      xs: "text-[0.64rem]",
      sm: "text-[0.80rem]",
      base: "text-base",
      lg: "text-[1.25rem]",
      xl: "text-[1.563rem]",
      "2xl": "text-[1.953rem]",
      "3xl": "text-[2.441rem]",
      "4xl": "text-[3.052rem]",
    },
  },
  defaultVariants: {
    variant: "body",
    size: "base",
  },
});

// ---------------------------------------------------------------------------
// Input variants (supplementary — wraps native input styling)
// ---------------------------------------------------------------------------

export const megidoInput = cva(
  [
    "flex w-full rounded-md border bg-[var(--megido-bg-card)]",
    "text-[var(--megido-text-body)] text-sm",
    "transition-colors duration-150",
    "file:border-0 file:bg-transparent file:text-sm file:font-medium",
    "placeholder:text-[var(--megido-text-muted)]",
    "focus-visible:outline-none focus-visible:ring-2",
    "focus-visible:ring-[var(--megido-primary)] focus-visible:ring-offset-1",
    "disabled:cursor-not-allowed disabled:opacity-50",
  ],
  {
    variants: {
      variant: {
        default: "border-[var(--megido-border)]",
        error: "border-[var(--megido-danger)] focus-visible:ring-[var(--megido-danger)]",
      },
      inputSize: {
        sm: "h-8 px-2.5 text-xs",
        md: "h-9 px-3 text-sm",
        lg: "h-10 px-4 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      inputSize: "md",
    },
  }
);

// ---------------------------------------------------------------------------
// Type exports for variant props
// ---------------------------------------------------------------------------

export type MegidoButtonVariants = Parameters<typeof megidoButton>[0];
export type MegidoCardVariants = Parameters<typeof megidoCard>[0];
export type MegidoBadgeVariants = Parameters<typeof megidoBadge>[0];
export type MegidoTextVariants = Parameters<typeof megidoText>[0];
export type MegidoInputVariants = Parameters<typeof megidoInput>[0];
