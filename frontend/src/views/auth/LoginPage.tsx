import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { api, formatApiError } from "../../state/http";
import { useAuth, bootstrapTokenFromStorage } from "../../state/auth";
import { t } from "../../i18n";
import { Button } from "../../ui/button";
import { Card } from "../../ui/card";
import { Input, Label } from "../../ui/field";
import { toast } from "../../ui/toast";

export function LoginPage() {
  const { signIn } = useAuth();
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    bootstrapTokenFromStorage();
  }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const token = await api.auth.login(email, password);
      await signIn(token.access_token);
      toast(
        t("auth.signed_in"),
        `${t("auth.welcome_back")}${email ? `, ${email}` : ""}.`,
      );
      nav(loc.state?.from ?? "/app/dashboard", { replace: true });
    } catch (err) {
      toast(t("auth.login_failed"), formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-14">
      <Card className="p-6 shadow-soft">
        <div className="text-lg font-semibold">{t("auth.sign_in_title")}</div>
        <div className="mt-1 text-sm text-slate-300">
          {t("auth.sign_in_subtitle")}
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
              autoComplete="current-password"
            />
          </div>
          <Button disabled={loading} className="w-full">
            {loading ? t("auth.signing_in") : t("auth.sign_in")}
          </Button>
        </form>

        <div className="mt-5 text-sm text-slate-300">
          {t("auth.new_here")}{" "}
          <Link className="text-sky-300 hover:underline" to="/register">
            {t("auth.create_account")}
          </Link>
        </div>
      </Card>
    </div>
  );
}

