'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in component:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="p-4 border border-red-500/20 bg-red-500/10 rounded-md text-red-400">
          <h2 className="text-lg font-bold mb-2">Component Error</h2>
          <p className="text-sm opacity-80">This component encountered an unexpected error.</p>
          {this.state.error && <p className="text-xs font-mono mt-2 break-all opacity-50">{this.state.error.message}</p>}
        </div>
      );
    }

    return this.props.children;
  }
}
