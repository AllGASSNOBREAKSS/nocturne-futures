import { Component, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

// A failing page must never blank the whole terminal: isolate and report it.
export class ErrorBoundary extends Component<{ children: ReactNode; resetKey: string }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidUpdate(prev: { resetKey: string }) { if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null }); }
  componentDidCatch(error: Error) { console.error("PAGE_ERROR", error.message, error.stack); }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="m-6 flex items-start gap-3 rounded border border-down/40 bg-down/5 p-4 font-mono text-xs text-down">
        <AlertTriangle className="h-5 w-5 shrink-0" />
        <div><div className="mb-1 font-semibold uppercase tracking-wider">This view failed to render</div><div className="text-ink-300">{this.state.error.message}</div></div>
      </div>
    );
  }
}
