import { Component, type ErrorInfo, type ReactNode } from 'react'

interface AppErrorBoundaryProps {
  children: ReactNode
}

interface AppErrorBoundaryState {
  error: Error | null
}

/**
 * Prevent an uncaught render error from unmounting the entire application into
 * an opaque blank page. The original error remains available in DevTools.
 */
export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('InsightDocs UI error', error, errorInfo)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="flex min-h-svh items-center justify-center bg-background p-6 text-foreground">
          <section className="w-full max-w-lg space-y-4 rounded-xl border bg-card p-6 shadow-sm" role="alert">
            <div className="space-y-2">
              <h1 className="text-lg font-semibold">InsightDocs could not render this screen</h1>
              <p className="text-sm leading-relaxed text-muted-foreground">
                The page encountered a UI error. Reload the application to recover. If it happens again,
                copy the error text below and send it with your browser console output.
              </p>
            </div>
            <code className="block overflow-x-auto rounded-md bg-muted p-3 text-xs text-destructive">
              {this.state.error.message || 'Unknown UI error'}
            </code>
            <button
              type="button"
              className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/80"
              onClick={() => window.location.reload()}
            >
              Reload application
            </button>
          </section>
        </main>
      )
    }

    return this.props.children
  }
}
