import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, formatApiError } from "../../state/http";
import { t } from "../../i18n";
import { Button } from "../../ui/button";
import { Card } from "../../ui/card";
import { Input, Label } from "../../ui/field";
import { toast } from "../../ui/toast";

export function RegisterPage() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.auth.register({ email, password });
      toast(t("auth.account_created"), t("auth.you_can_sign_in_now"));
      nav("/login");
    } catch (err) {
      toast(t("auth.registration_failed"), formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-14">
      <Card className="p-6 shadow-soft">
        <div className="text-lg font-semibold">{t("auth.register_title")}</div>
        <div className="mt-1 text-sm text-slate-300">
          {t("auth.register_subtitle")}
        </div>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div className="space-y-1.5">
            <Label>{t("auth.email")}</Label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
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
            <div className="text-xs text-slate-400">{t("auth.password_hint")}</div>
          </div>
          <Button disabled={loading} className="w-full">
            {loading ? t("auth.creating") : t("auth.create")}
          </Button>
        </form>

        <div className="mt-5 text-sm text-slate-300">
          {t("auth.already_have_account")}{" "}
          <Link className="text-sky-300 hover:underline" to="/login">
            {t("auth.sign_in")}
          </Link>
        </div>
      </Card>
    </div>
  );
}

