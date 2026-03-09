/**
 * React error boundary component.
 *
 * Catches unhandled JavaScript errors in the component tree below it,
 * logs the error, and displays a Hebrew-language fallback UI with a
 * retry button. Uses a class component because React error boundaries
 * require getDerivedStateFromError / componentDidCatch.
 *
 * Supports two modes:
 * - Page-level: full-page fallback with "refresh" button (default).
 * - Section-level: compact inline fallback with "retry" that resets
 *   the boundary state without reloading the page.
 */
"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ErrorBoundaryProps {
  /** Content to render when no error has occurred. */
  children: ReactNode;
  /** Optional custom fallback. If omitted, uses the built-in Hebrew fallback. */
  fallback?: ReactNode;
  /** Custom fallback message (Hebrew). Defaults to "משהו השתבש". */
  fallbackMessage?: string;
  /** If true, the retry button resets the boundary instead of reloading. */
  sectionLevel?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    if (process.env.NODE_ENV === "development") {
      console.error("[ErrorBoundary] Uncaught error:", error, errorInfo);
    }
  }

  private handleRetry = (): void => {
    if (this.props.sectionLevel) {
      this.setState({ hasError: false, error: null });
    } else {
      window.location.reload();
    }
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const message = this.props.fallbackMessage ?? "משהו השתבש";
      const buttonLabel = this.props.sectionLevel ? "נסה שוב" : "רענן את הדף";
      const containerClass = this.props.sectionLevel
        ? "flex flex-col items-center justify-center gap-3 p-4 text-center"
        : "flex min-h-[50vh] flex-col items-center justify-center gap-4 p-8 text-center";

      return (
        <div dir="rtl" className={containerClass}>
          <div className="rounded-xl border border-red-200 bg-red-50 px-10 py-8 shadow-sm">
            <h2 className="text-xl font-bold text-red-700">{message}</h2>
            <p className="mt-2 text-sm text-red-600/80">
              {this.props.sectionLevel
                ? "אירעה שגיאה בטעינת הקטע"
                : "נא לרענן את הדף"}
            </p>

            {process.env.NODE_ENV === "development" && this.state.error && (
              <pre className="mt-4 max-w-lg overflow-auto rounded bg-red-100 p-3 text-left text-xs text-red-800">
                {this.state.error.message}
              </pre>
            )}

            <button
              type="button"
              onClick={this.handleRetry}
              className="mt-6 rounded-lg bg-megido-primary px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-megido-primary-hover"
            >
              {buttonLabel}
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
