export type ProviderId = "openai" | "anthropic" | "relay";

export type ProviderConfig = {
  enabled: boolean;
  apiKey: string;
  baseUrl: string;
  mainModel: string;
  note: string;
};

export type ProviderMap = Record<ProviderId, ProviderConfig>;

export type ProviderMeta = {
  label: string;
  shortLabel: string;
  description: string;
  accent: string;
  tint: string;
  defaultBaseUrl: string;
  baseUrlMode: "readonly" | "editable";
  apiKeyHint: string;
};
