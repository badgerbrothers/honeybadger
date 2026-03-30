"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { RotateCcw, Save } from "lucide-react";

import { tasksApi } from "@/lib/api/endpoints";
import { ProviderCard } from "@/features/settings/ProviderCard";
import { ProviderSettingsForm } from "@/features/settings/ProviderSettingsForm";
import { SettingsNotice } from "@/features/settings/SettingsNotice";
import { SettingsSidebar } from "@/features/settings/SettingsSidebar";
import {
  buildEnvSnippet,
  cloneDefaultProviders,
  fromApiSettings,
  providerMeta,
  toApiSettings,
} from "@/features/settings/helpers";
import type { ProviderConfig, ProviderId, ProviderMap } from "@/features/settings/types";

import styles from "./settings.module.css";

export default function SettingsPage() {
  const [activeProvider, setActiveProvider] = useState<ProviderId>("openai");
  const [providers, setProviders] = useState<ProviderMap>(cloneDefaultProviders);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [savedSnapshot, setSavedSnapshot] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<ProviderId, boolean>>({
    openai: false,
    anthropic: false,
    relay: false,
  });
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setLoadError(null);
      try {
        const response = await tasksApi.getModelSettings();
        if (cancelled) return;

        const next = fromApiSettings(response);
        setActiveProvider(next.activeProvider);
        setProviders(next.providers);
        setSavedAt(next.savedAt);
        setSavedSnapshot(
          JSON.stringify({
            activeProvider: next.activeProvider,
            providers: next.providers,
          }),
        );
      } catch (error) {
        if (cancelled) return;
        setLoadError(error instanceof Error ? error.message : "加载设置失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const snapshot = useMemo(
    () =>
      JSON.stringify({
        activeProvider,
        providers,
      }),
    [activeProvider, providers],
  );

  const isDirty = snapshot !== savedSnapshot;
  const current = providers[activeProvider];
  const envSnippet = useMemo(
    () => buildEnvSnippet(activeProvider, providers),
    [activeProvider, providers],
  );

  const providerStatus = useMemo(() => {
    return (Object.keys(providers) as ProviderId[]).map((id) => {
      const config = providers[id];
      const configured = config.enabled && config.apiKey.trim().length > 0 && config.baseUrl.trim().length > 0;
      return { id, configured };
    });
  }, [providers]);

  const saveConfig = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const response = await tasksApi.putModelSettings(toApiSettings(activeProvider, providers, savedAt));
      const next = fromApiSettings(response);
      setActiveProvider(next.activeProvider);
      setProviders(next.providers);
      setSavedAt(next.savedAt);
      setSavedSnapshot(
        JSON.stringify({
          activeProvider: next.activeProvider,
          providers: next.providers,
        }),
      );
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "保存设置失败");
    } finally {
      setSaving(false);
    }
  };

  const resetCurrentProvider = () => {
    setProviders((prev) => ({
      ...prev,
      [activeProvider]: { ...cloneDefaultProviders()[activeProvider] },
    }));
  };

  const updateCurrentProvider = (patch: Partial<ProviderConfig>) => {
    setProviders((prev) => ({
      ...prev,
      [activeProvider]: {
        ...prev[activeProvider],
        ...patch,
      },
    }));
  };

  const toggleKeyVisibility = (providerId: ProviderId) => {
    setShowKeys((prev) => ({ ...prev, [providerId]: !prev[providerId] }));
  };

  const copySnippet = async () => {
    try {
      await navigator.clipboard.writeText(envSnippet);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <main className={`main-content ${styles.page}`}>
      <header className={`header ${styles.pageHeader}`}>
        <div className={styles.titleBlock}>
          <h1 className="header-title">模型设置</h1>
          <p className={styles.subtitle}>
            在这里配置 OpenAI、Anthropic 和自定义服务商的密钥、地址与默认模型。
          </p>
        </div>

        <div className={styles.headerActions}>
          <button className="manus-btn" type="button" onClick={resetCurrentProvider} disabled={loading || saving}>
            <RotateCcw size={16} />
            重置当前
          </button>
          <button
            className="manus-btn manus-btn-primary"
            type="button"
            onClick={() => void saveConfig()}
            disabled={loading || saving}
          >
            <Save size={16} />
            {saving ? "保存中..." : "保存设置"}
          </button>
          <Link className="manus-btn" href="/conversation" aria-label="Back to conversation">
            返回会话
          </Link>
        </div>
      </header>

      <div className={styles.content}>
        <SettingsNotice />

        {loadError ? <section className={styles.errorBanner}>加载设置失败：{loadError}</section> : null}
        {saveError ? <section className={styles.errorBanner}>保存设置失败：{saveError}</section> : null}

        <section className={styles.providerGrid} aria-label="Provider cards">
          {(Object.keys(providerMeta) as ProviderId[]).map((id) => (
            <ProviderCard
              key={id}
              id={id}
              config={providers[id]}
              active={id === activeProvider}
              disabled={loading}
              onSelect={setActiveProvider}
            />
          ))}
        </section>

        <div className={styles.layoutGrid}>
          <ProviderSettingsForm
            activeProvider={activeProvider}
            current={current}
            loading={loading}
            keyVisible={showKeys[activeProvider]}
            onToggleKeyVisibility={() => toggleKeyVisibility(activeProvider)}
            onUpdate={updateCurrentProvider}
          />

          <SettingsSidebar
            loading={loading}
            copied={copied}
            isDirty={isDirty}
            savedAt={savedAt}
            envSnippet={envSnippet}
            providerStatus={providerStatus}
            onCopySnippet={() => void copySnippet()}
          />
        </div>
      </div>
    </main>
  );
}
