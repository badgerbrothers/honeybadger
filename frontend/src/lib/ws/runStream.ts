import { WS_BASE_URL } from "@/lib/config";

export type RunEvent = Record<string, unknown>;

export interface RunStreamHandlers {
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onEvent?: (event: RunEvent) => void;
  onError?: (event: Event) => void;
}

export function connectRunStream(
  runId: string,
  accessToken: string,
  handlers: RunStreamHandlers,
): () => void {
  const url = `${WS_BASE_URL}/api/runs/${encodeURIComponent(runId)}/stream?token=${encodeURIComponent(accessToken)}`;
  const ws = new WebSocket(url);
  let pingTimer: ReturnType<typeof setInterval> | null = null;

  ws.onopen = () => {
    handlers.onOpen?.();
    pingTimer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 25_000);
  };

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data as string) as RunEvent;
      handlers.onEvent?.(data);
    } catch {
      handlers.onEvent?.({ type: "message", raw: String(evt.data ?? "") });
    }
  };
  ws.onerror = (evt) => handlers.onError?.(evt);
  ws.onclose = (evt) => {
    if (pingTimer) clearInterval(pingTimer);
    handlers.onClose?.(evt);
  };

  return () => {
    if (pingTimer) clearInterval(pingTimer);
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  };
}

