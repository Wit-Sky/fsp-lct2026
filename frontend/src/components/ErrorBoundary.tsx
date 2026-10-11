import { Component, type ReactNode } from "react";
import { recordQaEvent } from "../lib/qa";

/** Падение одного экрана не оставляет белую страницу: показываем сообщение и пишем ошибку в журнал баг-репорта. */
export default class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error) {
    recordQaEvent("js", `render: ${error.message}`);
  }
  componentDidUpdate(prev: { resetKey?: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }
  render() {
    if (this.state.error)
      return (
        <div className="card border-rose-200 bg-rose-50 text-rose-800">
          <p className="font-semibold">На этом экране что-то сломалось.</p>
          <p className="mt-1 text-sm">Вернитесь назад или обновите страницу. Ошибка: {this.state.error.message}</p>
        </div>
      );
    return this.props.children;
  }
}
