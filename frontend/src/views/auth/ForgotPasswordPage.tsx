import React, { useState } from "react";
import { Link } from "react-router-dom";

import { api, formatApiError } from "../../state/http";
import { t } from "../../i18n";
import { Button } from "../../ui/button";
import { Card } from "../../ui/card";
import { Input, Label } from "../../ui/field";
import { toast } from "../../ui/toast";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const trimmed = email.trim();
    if (!trimmed) {
      setError(t("auth.email_required"));
      return;
    }
    setLoading(true);
    try {
      await api.auth.forgotPassword(trimmed);
      setSent(true);
      toast(t("auth.password_reset_sent"), t("auth.password_reset_sent_detail"));
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
        <div className="text-lg font-semibold">{t("auth.forgot_password_title")}</div>
        <div className="mt-1 text-sm text-ink-secondary">{t("auth.forgot_password_subtitle")}</div>

        {sent ? (
          <div className="mt-6 rounded-lg border border-semantic-success/30 bg-semantic-success-bg p-4 text-sm text-semantic-success">
            {t("auth.password_reset_sent_detail")}
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
              <Label>{t("auth.email")}</Label>
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                type="email"
              />
            </div>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? t("auth.sending_reset") : t("auth.send_new_password")}
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
