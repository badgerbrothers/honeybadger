import { useEffect, useState, useCallback } from 'react';
import { WebSocketClient } from '@/lib/websocket';
import { TaskRunEvent } from '../types';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost';

function eventKey(event: TaskRunEvent): string {
  return JSON.stringify(event);
}

export function useTaskRunStream(runId: string | null, initialEvents: TaskRunEvent[] = []) {
  const [events, setEvents] = useState<TaskRunEvent[]>(initialEvents);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEvents(initialEvents);
  }, [initialEvents, runId]);

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
        setEvents((prev) => {
          const key = eventKey(data);
          if (prev.some((item) => eventKey(item) === key)) {
            return prev;
          }
          return [...prev, data];
        });
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
