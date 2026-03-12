import { useEffect, useState, useCallback } from 'react';
import { WebSocketClient } from '@/lib/websocket';
import { TaskRunEvent } from '../types';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export function useTaskRunStream(runId: string | null) {
  const [events, setEvents] = useState<TaskRunEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;

    const wsUrl = `${WS_BASE}/api/runs/${runId}/stream`;
    const client = new WebSocketClient(wsUrl);

    client.connect()
      .then(() => setIsConnected(true))
      .catch((err) => setError(err.message));

    const unsubscribe = client.onMessage((event) => {
      try {
        const data = JSON.parse(event.data) as TaskRunEvent;
        setEvents((prev) => [...prev, data]);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    });

    return () => {
      unsubscribe();
      client.disconnect();
      setIsConnected(false);
    };
  }, [runId]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return { events, isConnected, error, clearEvents };
}
