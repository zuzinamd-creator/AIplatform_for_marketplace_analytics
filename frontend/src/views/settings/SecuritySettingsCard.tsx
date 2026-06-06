import { useState } from "react";

import { api, formatApiError } from "../../state/http";
import { t } from "../../i18n";
import { Button } from "../../ui/button";
import { Card } from "../../ui/card";
import { Input, Label } from "../../ui/field";
import { toast } from "../../ui/toast";

export function SecuritySettingsCard() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword.length < 8) {
      setError(t("auth.password_too_short"));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t("auth.password_mismatch"));
      return;
    }
    setLoading(true);
    try {
      await api.auth.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast(t("auth.password_changed"), t("auth.password_changed_detail"));
    } catch (err) {
      const message = formatApiError(err);
      setError(message);
      toast(t("auth.password_change_failed"), message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="space-y-4 p-5">
      <div>
        <div className="text-sm font-semibold">{t("settings.security_title")}</div>
        <p className="mt-1 text-xs text-ink-muted">{t("settings.security_subtitle")}</p>
      </div>

      <form className="space-y-4" onSubmit={onSubmit}>
        {error ? (
          <div
            className="rounded-lg border border-semantic-danger/30 bg-semantic-danger-bg px-3 py-2 text-sm text-semantic-danger"
            role="alert"
          >
            {error}
          </div>
        ) : null}
        <div className="space-y-1.5">
          <Label>{t("auth.current_password")}</Label>
          <Input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        <div className="space-y-1.5">
          <Label>{t("auth.new_password")}</Label>
          <Input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
          />
        </div>
        <div className="space-y-1.5">
          <Label>{t("auth.confirm_password")}</Label>
          <Input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
          />
        </div>
        <Button type="submit" disabled={loading}>
          {loading ? t("auth.saving_password") : t("auth.change_password")}
        </Button>
      </form>
    </Card>
  );
}
