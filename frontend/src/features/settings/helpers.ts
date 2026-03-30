import type { ApiModelSettings } from "@/lib/api/types";

import type { ProviderConfig, ProviderId, ProviderMap, ProviderMeta } from "./types";

export const providerMeta: Record<ProviderId, ProviderMeta> = {
  openai: {
    label: "OpenAI 官方",
    shortLabel: "OpenAI",
    description: "适合 OpenAI 官方接口，API 地址固定显示为官方地址。",
    accent: "#10a37f",
    tint: "linear-gradient(135deg, rgba(16,163,127,0.12), rgba(16,163,127,0.02))",
    defaultBaseUrl: "https://api.openai.com/v1",
    baseUrlMode: "readonly",
    apiKeyHint: "sk-...",
  },
  anthropic: {
    label: "A 站 / Anthropic",
    shortLabel: "Anthropic",
    description: "单独填写 Anthropic 密钥，地址默认显示官方入口。",
    accent: "#d97706",
    tint: "linear-gradient(135deg, rgba(217,119,6,0.12), rgba(217,119,6,0.02))",
    defaultBaseUrl: "https://api.anthropic.com",
    baseUrlMode: "readonly",
    apiKeyHint: "sk-ant-...",
  },
  relay: {
    label: "自定义服务商",
    shortLabel: "Custom",
    description: "用于接入兼容 OpenAI 协议的自定义服务商，可自定义 API 地址。",
    accent: "#2563eb",
    tint: "linear-gradient(135deg, rgba(37,99,235,0.14), rgba(37,99,235,0.03))",
    defaultBaseUrl: "https://your-provider.example.com/v1",
    baseUrlMode: "editable",
    apiKeyHint: "provider-key-...",
  },
};

export const defaultProviders: ProviderMap = {
  openai: {
    enabled: true,
    apiKey: "",
    baseUrl: providerMeta.openai.defaultBaseUrl,
    mainModel: "gpt-5.3-codex",
    note: "官方 OpenAI 直连",
  },
  anthropic: {
    enabled: false,
    apiKey: "",
    baseUrl: providerMeta.anthropic.defaultBaseUrl,
    mainModel: "claude-3-opus-20240229",
    note: "A 站单独接入",
  },
  relay: {
    enabled: false,
    apiKey: "",
    baseUrl: providerMeta.relay.defaultBaseUrl,
    mainModel: "gpt-5.3-codex",
    note: "兼容 OpenAI 协议的自定义服务商",
  },
};

export function cloneDefaultProviders(): ProviderMap {
  return {
    openai: { ...defaultProviders.openai },
    anthropic: { ...defaultProviders.anthropic },
    relay: { ...defaultProviders.relay },
  };
}

export function mergeProviders(
  incoming?: Partial<Record<ProviderId, Partial<ProviderConfig>>>,
): ProviderMap {
  const merged = cloneDefaultProviders();
  if (!incoming) return merged;

  for (const id of Object.keys(merged) as ProviderId[]) {
    if (!incoming[id]) continue;
    merged[id] = {
      ...merged[id],
      ...incoming[id],
    };
  }
  return merged;
}

export function maskKey(value: string) {
  if (!value) return "未填写";
  if (value.length <= 8) return `${value.slice(0, 2)}***`;
  return `${value.slice(0, 4)}••••${value.slice(-4)}`;
}

export function buildEnvSnippet(activeProvider: ProviderId, providers: ProviderMap) {
  const current = providers[activeProvider];
  const model = current.mainModel.trim() || defaultProviders[activeProvider].mainModel;

  if (activeProvider === "anthropic") {
    return [
      "ANTHROPIC_API_KEY=" + (current.apiKey || "<your-anthropic-key>"),
      "DEFAULT_MAIN_MODEL=" + model,
      "SUPPORTED_MODELS=" + model,
    ].join("\n");
  }

  return [
    "OPENAI_API_KEY=" + (current.apiKey || "<your-openai-compatible-key>"),
    "OPENAI_BASE_URL=" + (current.baseUrl || providerMeta[activeProvider].defaultBaseUrl),
    "DEFAULT_MAIN_MODEL=" + model,
    "SUPPORTED_MODELS=" + model,
  ].join("\n");
}

export function formatSavedAt(value: string | null) {
  if (!value) return "尚未保存";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return date.toLocaleString();
}

export function fromApiSettings(data: ApiModelSettings) {
  return {
    activeProvider: data.active_provider,
    providers: mergeProviders({
      openai: {
        enabled: data.providers.openai.enabled,
        apiKey: data.providers.openai.api_key,
        baseUrl: data.providers.openai.base_url,
        mainModel: data.providers.openai.main_model,
        note: data.providers.openai.note,
      },
      anthropic: {
        enabled: data.providers.anthropic.enabled,
        apiKey: data.providers.anthropic.api_key,
        baseUrl: data.providers.anthropic.base_url,
        mainModel: data.providers.anthropic.main_model,
        note: data.providers.anthropic.note,
      },
      relay: {
        enabled: data.providers.relay.enabled,
        apiKey: data.providers.relay.api_key,
        baseUrl: data.providers.relay.base_url,
        mainModel: data.providers.relay.main_model,
        note: data.providers.relay.note,
      },
    }),
    savedAt: data.updated_at,
  };
}

export function toApiSettings(activeProvider: ProviderId, providers: ProviderMap, updatedAt: string | null) {
  return {
    active_provider: activeProvider,
    providers: {
      openai: {
        enabled: providers.openai.enabled,
        api_key: providers.openai.apiKey,
        base_url: providers.openai.baseUrl,
        main_model: providers.openai.mainModel,
        note: providers.openai.note,
      },
      anthropic: {
        enabled: providers.anthropic.enabled,
        api_key: providers.anthropic.apiKey,
        base_url: providers.anthropic.baseUrl,
        main_model: providers.anthropic.mainModel,
        note: providers.anthropic.note,
      },
      relay: {
        enabled: providers.relay.enabled,
        api_key: providers.relay.apiKey,
        base_url: providers.relay.baseUrl,
        main_model: providers.relay.mainModel,
        note: providers.relay.note,
      },
    },
    updated_at: updatedAt,
  };
}
