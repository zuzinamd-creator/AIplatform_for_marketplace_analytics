import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api, formatApiError } from "../../state/http";
import { t } from "../../i18n";
import { Button } from "../../ui/button";
import { Card } from "../../ui/card";
import { Input, Label } from "../../ui/field";
import { toast } from "../../ui/toast";

type InviteState =
  | { kind: "loading" }
  | { kind: "invalid"; message: string }
  | { kind: "valid"; email: string; token: string };

export function RegisterPage() {
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const inviteToken = searchParams.get("invite");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [registrationAvailable, setRegistrationAvailable] = useState<boolean | null>(null);
  const [inviteState, setInviteState] = useState<InviteState | null>(
    inviteToken ? { kind: "loading" } : null,
  );

  useEffect(() => {
    if (!inviteToken) {
      let active = true;
      api.auth
        .registrationStatus()
        .then((status) => {
          if (active) setRegistrationAvailable(status.available);
        })
        .catch(() => {
          if (active) setRegistrationAvailable(false);
        });
      return () => {
        active = false;
      };
    }

    let active = true;
    api.auth
      .validateInvite(inviteToken)
      .then((result) => {
        if (!active) return;
        if (!result.valid || !result.email) {
          setInviteState({ kind: "invalid", message: "Приглашение недействительно." });
          return;
        }
        setInviteState({ kind: "valid", email: result.email, token: inviteToken });
      })
      .catch(() => {
        if (active) setInviteState({ kind: "invalid", message: "Приглашение недействительно." });
      });
    return () => {
      active = false;
    };
  }, [inviteToken]);

  const onSubmit = async (e: React.FormEvent, submitEmail: string, token?: string) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    if (password.length < 8) {
      setError(t("auth.password_too_short"));
      return;
    }
    setLoading(true);
    try {
      await api.auth.register({
        email: submitEmail,
        password,
        invite_token: token,
      });
      setSuccess(true);
      toast(t("auth.account_created"), t("auth.you_can_sign_in_now"));
      setTimeout(() => nav("/login", { replace: true }), 1500);
    } catch (err) {
      const message = formatApiError(err);
      setError(message);
      toast(t("auth.registration_failed"), message);
    } finally {
      setLoading(false);
    }
  };

  if (inviteToken) {
    if (!inviteState || inviteState.kind === "loading") {
      return (
        <div className="mx-auto max-w-md px-4 py-14">
          <Card className="p-6 shadow-soft">
            <div className="text-sm text-ink-muted">{t("common.loading")}</div>
          </Card>
        </div>
      );
    }

    if (inviteState.kind === "invalid") {
      return (
        <div className="mx-auto max-w-md px-4 py-14">
          <Card className="p-6 shadow-soft">
            <div className="text-lg font-semibold">Регистрация по приглашению</div>
            <p className="mt-2 text-sm text-semantic-danger">{inviteState.message}</p>
            <p className="mt-2 text-sm text-ink-secondary">
              Приглашение может быть просрочено, использовано или отозвано.
            </p>
            <div className="mt-5 text-sm text-ink-secondary">
              <Link className="link-muted" to="/login">
                {t("auth.back_to_sign_in")}
              </Link>
            </div>
          </Card>
        </div>
      );
    }

    return (
      <div className="mx-auto max-w-md px-4 py-14">
        <Card className="p-6 shadow-soft">
          <div className="text-lg font-semibold">Регистрация по приглашению</div>
          <div className="mt-1 text-sm text-ink-secondary">Создайте пароль для доступа к платформе.</div>

          {success ? (
            <div
              className="mt-6 rounded-lg border border-semantic-success/30 bg-semantic-success-bg px-3 py-3 text-sm text-semantic-success"
              role="status"
            >
              <div className="font-medium">{t("auth.account_created")}</div>
              <div className="mt-1 text-ink-secondary">{t("auth.you_can_sign_in_now")}</div>
            </div>
          ) : (
            <form
              className="mt-6 space-y-4"
              onSubmit={(e) => onSubmit(e, inviteState.email, inviteState.token)}
            >
              {error ? (
                <div
                  className="rounded-lg border border-semantic-danger/30 bg-semantic-danger-bg px-3 py-2 text-sm text-semantic-danger"
                  role="alert"
                >
                  {error}
                </div>
              ) : null}
              <div className="space-y-1.5">
                <Label>{t("auth.email")}</Label>
                <Input value={inviteState.email} readOnly type="email" autoComplete="email" />
              </div>
              <div className="space-y-1.5">
                <Label>{t("auth.password")}</Label>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
                <div className="text-xs text-ink-muted">{t("auth.password_hint")}</div>
              </div>
              <Button type="submit" disabled={loading} className="w-full">
                {loading ? t("auth.creating") : t("auth.create")}
              </Button>
            </form>
          )}

          <div className="mt-5 text-sm text-ink-secondary">
            {t("auth.already_have_account")}{" "}
            <Link className="link-muted" to="/login">
              {t("auth.sign_in")}
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  if (registrationAvailable === null) {
    return (
      <div className="mx-auto max-w-md px-4 py-14">
        <Card className="p-6 shadow-soft">
          <div className="text-sm text-ink-muted">{t("common.loading")}</div>
        </Card>
      </div>
    );
  }

  if (!registrationAvailable) {
    return (
      <div className="mx-auto max-w-md px-4 py-14">
        <Card className="p-6 shadow-soft">
          <div className="text-lg font-semibold">{t("auth.registration_unavailable_title")}</div>
          <p className="mt-2 text-sm text-ink-secondary">{t("auth.registration_unavailable_detail")}</p>
          <div className="mt-5 text-sm text-ink-secondary">
            <Link className="link-muted" to="/login">
              {t("auth.back_to_sign_in")}
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md px-4 py-14">
      <Card className="p-6 shadow-soft">
        <div className="text-lg font-semibold">{t("auth.register_title")}</div>
        <div className="mt-1 text-sm text-ink-secondary">{t("auth.register_subtitle")}</div>

        {success ? (
          <div
            className="mt-6 rounded-lg border border-semantic-success/30 bg-semantic-success-bg px-3 py-3 text-sm text-semantic-success"
            role="status"
          >
            <div className="font-medium">{t("auth.account_created")}</div>
            <div className="mt-1 text-ink-secondary">{t("auth.you_can_sign_in_now")}</div>
          </div>
        ) : (
          <form className="mt-6 space-y-4" onSubmit={(e) => onSubmit(e, email.trim())}>
            {error ? (
              <div
                className="rounded-lg border border-semantic-danger/30 bg-semantic-danger-bg px-3 py-2 text-sm text-semantic-danger"
                role="alert"
              >
                {error}
              </div>
            ) : null}
            <div className="space-y-1.5">
              <Label>{t("auth.email")}</Label>
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                type="email"
              />
            </div>
            <div className="space-y-1.5">
              <Label>{t("auth.password")}</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
              />
              <div className="text-xs text-ink-muted">{t("auth.password_hint")}</div>
            </div>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? t("auth.creating") : t("auth.create")}
            </Button>
          </form>
        )}

        <div className="mt-5 text-sm text-ink-secondary">
          {t("auth.already_have_account")}{" "}
          <Link className="link-muted" to="/login">
            {t("auth.sign_in")}
          </Link>
        </div>
      </Card>
    </div>
  );
}
