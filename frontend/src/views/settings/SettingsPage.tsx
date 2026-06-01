import { useState } from "react";

import { loadWorkspaceProfile, saveWorkspaceProfile } from "../../state/onboarding";
import { loadSettings, saveSettings, type TenantSettings } from "../../state/settings";
import { trackUsage } from "../../state/usage";
import { Card } from "../../ui/card";
import { Button } from "../../ui/button";
import { Input, Label, Select } from "../../ui/field";
import { StatusBadge } from "../../ui/status-badge";
import { toast } from "../../ui/toast";

export function SettingsPage() {
  const [profile, setProfile] = useState(() => loadWorkspaceProfile());
  const [settings, setSettings] = useState<TenantSettings>(() => loadSettings());

  const saveAll = () => {
    saveWorkspaceProfile(profile);
    saveSettings(settings);
    trackUsage("settings_saved", { mode: settings.product_mode });
    toast("Настройки сохранены", "Сохранено локально в этом браузере.");
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Настройки</div>
        <div className="text-sm text-slate-300">
          Профиль рабочего пространства и уведомления. Пока сохраняется локально, без серверных настроек.
        </div>
      </div>

      <Card className="space-y-4 p-5">
        <div className="text-sm font-semibold">Рабочее пространство</div>
        <div className="space-y-1.5">
          <Label>Название</Label>
          <Input
            value={profile.workspace_name}
            onChange={(e) => setProfile((p) => ({ ...p, workspace_name: e.target.value }))}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Основной маркетплейс</Label>
          <Select
            value={profile.marketplace}
            onChange={(e) =>
              setProfile((p) => ({ ...p, marketplace: e.target.value as typeof p.marketplace }))
            }
          >
            <option value="unknown">Не выбрано</option>
            <option value="wildberries">Wildberries</option>
            <option value="ozon">Ozon</option>
          </Select>
        </div>
      </Card>

      <Card className="space-y-4 p-5">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Режим продукта</div>
          <StatusBadge tone="info">{settings.product_mode}</StatusBadge>
        </div>
        <div className="space-y-1.5">
          <Label>Режим</Label>
          <Select
            value={settings.product_mode}
            onChange={(e) =>
              setSettings((s) => ({ ...s, product_mode: e.target.value as TenantSettings["product_mode"] }))
            }
          >
            <option value="mvp">MVP (для продавца, скрывает внутренние страницы)</option>
            <option value="demo">Демо (для демонстраций)</option>
            <option value="full">Полный (показывать все страницы)</option>
          </Select>
          <div className="text-xs text-slate-400">
            В MVP внутренние “операторские” страницы скрыты из навигации. Поддержка/диагностика остаётся доступной.
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={settings.show_internal_ops}
            onChange={(e) => setSettings((s) => ({ ...s, show_internal_ops: e.target.checked }))}
          />
          Показывать внутренние страницы в навигации
        </label>
      </Card>

      <Card className="space-y-3 p-5">
        <div className="text-sm font-semibold">Уведомления (внутри приложения)</div>
        {(
          [
            ["stale_data_alerts", "Предупреждать об устаревших данных"],
            ["ai_degraded_alerts", "Предупреждать об «осторожном режиме» AI"],
            ["rebuild_alerts", "Показывать статус пересборки данных"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-2 text-sm text-slate-200">
            <input
              type="checkbox"
              checked={settings[key]}
              onChange={(e) => setSettings((s) => ({ ...s, [key]: e.target.checked }))}
            />
            {label}
          </label>
        ))}
        <div className="text-xs text-slate-400">
          Email‑уведомления требуют серверной доставки — пока недоступно. Баннеры в интерфейсе используют эти настройки.
        </div>
      </Card>

      <Button onClick={saveAll}>Сохранить настройки</Button>
    </div>
  );
}
