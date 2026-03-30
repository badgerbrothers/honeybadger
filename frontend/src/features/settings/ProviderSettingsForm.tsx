import { Eye, EyeOff } from "lucide-react";

import styles from "@/app/(workspace)/settings/settings.module.css";

import { defaultProviders, providerMeta } from "./helpers";
import type { ProviderConfig, ProviderId } from "./types";

type ProviderSettingsFormProps = {
  activeProvider: ProviderId;
  current: ProviderConfig;
  loading: boolean;
  keyVisible: boolean;
  onToggleKeyVisibility: () => void;
  onUpdate: (patch: Partial<ProviderConfig>) => void;
};

export function ProviderSettingsForm({
  activeProvider,
  current,
  loading,
  keyVisible,
  onToggleKeyVisibility,
  onUpdate,
}: ProviderSettingsFormProps) {
  const meta = providerMeta[activeProvider];

  return (
    <section className={styles.panel}>
      <div className={styles.sectionHeader}>
        <div>
          <div className={styles.sectionTitle}>{meta.label}</div>
          <p className={styles.sectionText}>按服务商分别维护密钥、地址和默认主模型。</p>
        </div>
        <span className={styles.providerFocusTag}>{meta.shortLabel}</span>
      </div>

      <div className={styles.switchRow}>
        <div>
          <div className={styles.switchTitle}>启用当前提供商</div>
          <div className={styles.switchText}>关闭后仍保留填写内容，但不会参与当前导出的配置片段。</div>
        </div>

        <label className={styles.switch}>
          <input
            className={styles.switchInput}
            type="checkbox"
            checked={current.enabled}
            onChange={(event) => onUpdate({ enabled: event.target.checked })}
            disabled={loading}
          />
          <span className={styles.switchTrack}>
            <span className={styles.switchThumb} />
          </span>
        </label>
      </div>

      <div className={styles.fields}>
        <label className={styles.field}>
          <span className={styles.label}>API Key</span>
          <span className={styles.hint}>按当前提供商填写密钥。服务端会按用户保存。</span>
          <div className={styles.inputWrap}>
            <input
              className={styles.input}
              type={keyVisible ? "text" : "password"}
              value={current.apiKey}
              placeholder={meta.apiKeyHint}
              onChange={(event) => onUpdate({ apiKey: event.target.value })}
              disabled={loading}
            />
            <button
              className={styles.inputAction}
              type="button"
              aria-label={keyVisible ? "Hide API key" : "Show API key"}
              onClick={onToggleKeyVisibility}
              disabled={loading}
            >
              {keyVisible ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </label>

        <label className={styles.field}>
          <span className={styles.label}>API 地址</span>
          <span className={styles.hint}>
            {meta.baseUrlMode === "readonly"
              ? "官方提供商固定显示官方地址。"
              : "自定义服务商可以填写 OpenAI 兼容网关地址。"}
          </span>
          <div className={styles.inputWrap}>
            <input
              className={`${styles.input} ${meta.baseUrlMode === "readonly" ? styles.inputReadonly : ""}`}
              type="text"
              value={current.baseUrl}
              readOnly={meta.baseUrlMode === "readonly"}
              placeholder={meta.defaultBaseUrl}
              onChange={(event) => onUpdate({ baseUrl: event.target.value })}
              disabled={loading}
            />
          </div>
        </label>

        <label className={styles.field}>
          <span className={styles.label}>默认主模型</span>
          <span className={styles.hint}>用于生成后端 `DEFAULT_MAIN_MODEL` 和 `SUPPORTED_MODELS`。</span>
          <div className={styles.inputWrap}>
            <input
              className={styles.input}
              type="text"
              value={current.mainModel}
              placeholder={defaultProviders[activeProvider].mainModel}
              onChange={(event) => onUpdate({ mainModel: event.target.value })}
              disabled={loading}
            />
          </div>
        </label>

        <label className={styles.field}>
          <span className={styles.label}>备注</span>
          <span className={styles.hint}>用于记录这是官方直连、A 站备用还是某个自定义服务环境。</span>
          <textarea
            className={styles.textarea}
            rows={4}
            value={current.note}
            onChange={(event) => onUpdate({ note: event.target.value })}
            placeholder="例如：测试环境走自定义服务商，生产环境走官方。"
            disabled={loading}
          />
        </label>
      </div>
    </section>
  );
}
