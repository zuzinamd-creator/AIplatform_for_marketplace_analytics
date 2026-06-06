import React, { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api, formatApiError } from "../../state/http";
import { useAuth } from "../../state/auth";
import { t } from "../../i18n";
import { Button } from "../../ui/button";
import { Card } from "../../ui/card";
import { Input, Label } from "../../ui/field";
import { toast } from "../../ui/toast";

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = useMemo(() => params.get("token") ?? "", [params]);
  const { signIn } = useAuth();
  const nav = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!token) {
      setError(t("auth.reset_link_invalid"));
      return;
    }
    if (password.length < 8) {
      setError(t("auth.password_too_short"));
      return;
    }
    if (password !== confirm) {
      setError(t("auth.password_mismatch"));
      return;
    }
    setLoading(true);
    try {
      const result = await api.auth.resetPassword({
        token,
        new_password: password,
        confirm_password: confirm,
      });
      await signIn(result.access_token);
      toast(t("auth.password_reset_complete"), t("auth.password_reset_complete_detail"));
      nav("/app/settings", { replace: true });
    } catch (err) {
      const message = formatApiError(err);
      setError(message);
      toast(t("auth.password_reset_failed"), message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-14">
      <Card className="p-6 shadow-soft">
        <div className="text-lg font-semibold">{t("auth.reset_password_title")}</div>
        <p className="mt-1 text-sm text-ink-muted">{t("auth.reset_password_subtitle")}</p>

        {!token ? (
          <div className="mt-6 rounded-lg border border-semantic-danger/30 bg-semantic-danger-bg px-3 py-2 text-sm text-semantic-danger">
            {t("auth.reset_link_invalid")}
          </div>
        ) : (
          <form className="mt-6 space-y-4" onSubmit={onSubmit}>
            {error ? (
              <div
                className="rounded-lg border border-semantic-danger/30 bg-semantic-danger-bg px-3 py-2 text-sm text-semantic-danger"
                role="alert"
              >
                {error}
              </div>
            ) : null}
            <div className="space-y-1.5">
              <Label>{t("auth.new_password")}</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            <div className="space-y-1.5">
              <Label>{t("auth.confirm_password")}</Label>
              <Input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? t("auth.saving_password") : t("auth.set_new_password")}
            </Button>
          </form>
        )}

        <div className="mt-5 text-sm text-ink-secondary">
          <Link className="link-muted" to="/login">
            {t("auth.back_to_sign_in")}
          </Link>
        </div>
      </Card>
    </div>
  );
}
