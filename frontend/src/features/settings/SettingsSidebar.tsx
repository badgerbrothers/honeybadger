import { CheckCircle2, CircleDashed, Copy, ServerCog } from "lucide-react";

import styles from "@/app/(workspace)/settings/settings.module.css";

import { formatSavedAt, providerMeta } from "./helpers";
import type { ProviderId } from "./types";

type ProviderStatusItem = {
  id: ProviderId;
  configured: boolean;
};

type SettingsSidebarProps = {
  loading: boolean;
  copied: boolean;
  isDirty: boolean;
  savedAt: string | null;
  envSnippet: string;
  providerStatus: ProviderStatusItem[];
  onCopySnippet: () => void;
};

export function SettingsSidebar({
  loading,
  copied,
  isDirty,
  savedAt,
  envSnippet,
  providerStatus,
  onCopySnippet,
}: SettingsSidebarProps) {
  return (
    <aside className={styles.sidePanel}>
      <section className={styles.infoCard}>
        <div className={styles.sideTitle}>配置概览</div>
        <div className={styles.statusList}>
          {providerStatus.map(({ id, configured }) => (
            <div key={id} className={styles.statusRow}>
              <span className={styles.statusName}>{providerMeta[id].label}</span>
              <span className={`${styles.statusValue} ${configured ? styles.statusValueReady : styles.statusValueMuted}`}>
                {configured ? (
                  <>
                    <CheckCircle2 size={15} />
                    已就绪
                  </>
                ) : (
                  <>
                    <CircleDashed size={15} />
                    未完成
                  </>
                )}
              </span>
            </div>
          ))}
        </div>
        <div className={styles.savedAt}>最后保存：{formatSavedAt(savedAt)}</div>
      </section>

      <section className={styles.infoCard}>
        <div className={styles.sideTitle}>当前项目环境变量映射</div>
        <ul className={styles.mappingList}>
          <li>`OpenAI / 天机中转站` 对应 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`</li>
          <li>`A 站 / Anthropic` 对应 `ANTHROPIC_API_KEY`</li>
          <li>`DEFAULT_MAIN_MODEL` 需要和后端支持模型保持一致</li>
        </ul>
      </section>

      <section className={styles.infoCard}>
        <div className={styles.sideHeader}>
          <div className={styles.sideTitle}>.env 片段预览</div>
          <button className="manus-btn" type="button" onClick={onCopySnippet}>
            <Copy size={15} />
            {copied ? "已复制" : "复制"}
          </button>
        </div>
        <pre className={styles.codeBlock}>{envSnippet}</pre>
        <div className={styles.snippetFoot}>
          <ServerCog size={14} />
          <span>
            {loading ? "正在从服务端读取配置" : isDirty ? "当前页面有未保存修改" : "当前页面已与服务端同步"}
          </span>
        </div>
      </section>
    </aside>
  );
}
