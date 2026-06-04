import { Link, useRouteError } from "react-router-dom";

import { Card } from "./card";
import { Button } from "./button";

export function RouteError(props: { error?: unknown; status?: number; title?: string }) {
  const routeError = useRouteError();
  const err = props.error ?? routeError;
  const msg = err instanceof Error ? err.message : typeof err === "string" ? err : "Неизвестная ошибка";

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Card className="p-6">
        <div className="text-lg font-semibold">{props.title ?? "Что-то пошло не так"}</div>
        <div className="mt-2 text-sm text-ink-secondary">
          {props.status ? `Статус ${props.status}. ` : null}
          {msg}
        </div>
        <div className="mt-6 flex gap-2">
          <Link to="/app">
            <Button variant="secondary">Вернуться в приложение</Button>
          </Link>
          <Link to="/login">
            <Button variant="ghost">Войти</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}

