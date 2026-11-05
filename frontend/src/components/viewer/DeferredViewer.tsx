import { Component, Suspense } from "react";
import type { ReactNode } from "react";

type Props = { children: ReactNode };
type State = { failed: boolean };

class ViewerBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="viewer-empty" role="alert">
          <p>Не удалось загрузить 3D-просмотр. Остальные режимы доступны.</p>
          <button type="button" onClick={() => window.location.reload()}>
            Обновить страницу
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default function DeferredViewer({ children }: Props) {
  return (
    <ViewerBoundary>
      <Suspense fallback={<div role="status">Загрузка 3D-просмотра…</div>}>
        {children}
      </Suspense>
    </ViewerBoundary>
  );
}
