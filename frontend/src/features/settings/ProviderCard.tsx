import { Bot, Globe2, KeyRound, ServerCog, Sparkles } from "lucide-react";

import styles from "@/app/(workspace)/settings/settings.module.css";

import { maskKey, providerMeta } from "./helpers";
import type { ProviderConfig, ProviderId } from "./types";

type ProviderCardProps = {
  id: ProviderId;
  config: ProviderConfig;
  active: boolean;
  disabled?: boolean;
  onSelect: (id: ProviderId) => void;
};

export function ProviderCard({ id, config, active, disabled = false, onSelect }: ProviderCardProps) {
  const item = providerMeta[id];
  const configured = config.enabled && config.apiKey.trim().length > 0 && config.baseUrl.trim().length > 0;

  return (
    <button
      type="button"
      className={`${styles.providerCard} ${active ? styles.providerCardActive : ""}`}
      style={{
        backgroundImage: item.tint,
        borderColor: active ? item.accent : undefined,
        boxShadow: active ? `0 16px 36px -28px ${item.accent}` : undefined,
      }}
      onClick={() => onSelect(id)}
      disabled={disabled}
    >
      <div className={styles.providerCardTop}>
        <span
          className={styles.providerIcon}
          style={{
            backgroundColor: `${item.accent}18`,
            color: item.accent,
          }}
        >
          {id === "openai" ? (
            <Sparkles size={18} />
          ) : id === "anthropic" ? (
            <Bot size={18} />
          ) : (
            <ServerCog size={18} />
          )}
        </span>
        <span className={`${styles.statusPill} ${configured ? styles.statusPillReady : styles.statusPillMuted}`}>
          {configured ? "已配置" : "待配置"}
        </span>
      </div>

      <div className={styles.providerName}>{item.label}</div>
      <div className={styles.providerDesc}>{item.description}</div>

      <div className={styles.providerMetaList}>
        <div className={styles.providerMetaRow}>
          <Globe2 size={14} />
          <span className={styles.providerMetaText}>{config.baseUrl}</span>
        </div>
        <div className={styles.providerMetaRow}>
          <KeyRound size={14} />
          <span className={styles.providerMetaText}>{maskKey(config.apiKey)}</span>
        </div>
      </div>
    </button>
  );
}
