import { ShieldCheck } from "lucide-react";

import styles from "@/app/(workspace)/settings/settings.module.css";

export function SettingsNotice() {
  return (
    <section className={styles.notice}>
      <div className={styles.noticeIcon}>
        <ShieldCheck size={18} />
      </div>
      <div>
        <div className={styles.noticeTitle}>当前按登录用户保存到后端</div>
        <p className={styles.noticeText}>
          页面配置会保存到服务端数据库，而不是只存在浏览器本地。右侧会同步生成适合你当前项目的
          `.env` 片段，便于核对或手动应用。
        </p>
      </div>
    </section>
  );
}
