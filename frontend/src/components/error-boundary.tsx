/**
 * React error boundary component.
 *
 * Catches unhandled JavaScript errors in the component tree below it,
 * logs the error, and displays a Hebrew-language fallback UI with a
 * page refresh button. Uses a class component because React error
 * boundaries require getDerivedStateFromError / componentDidCatch.
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
    // Log to console for debugging. In production this could be
    // forwarded to an error reporting service (e.g. Sentry).
    console.error("[ErrorBoundary] Uncaught error:", error, errorInfo);
  }

  private handleRefresh = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          dir="rtl"
          className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-8 text-center"
        >
          <div className="rounded-xl border border-red-200 bg-red-50 px-10 py-8 shadow-sm">
            <h2 className="text-xl font-bold text-red-700">
              {"משהו השתבש"}
            </h2>
            <p className="mt-2 text-sm text-red-600/80">
              {"נא לרענן את הדף"}
            </p>

            {process.env.NODE_ENV === "development" && this.state.error && (
              <pre className="mt-4 max-w-lg overflow-auto rounded bg-red-100 p-3 text-left text-xs text-red-800">
                {this.state.error.message}
              </pre>
            )}

            <button
              type="button"
              onClick={this.handleRefresh}
              className="mt-6 rounded-lg bg-megido-primary px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-megido-primary-hover"
            >
              {"רענן את הדף"}
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
