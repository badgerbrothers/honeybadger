'use client';

import { useParams } from 'next/navigation';
import { useMemo } from 'react';
import { Container } from '@/components/layout/Container';
import { Card } from '@/components/ui/Card';
import { TaskRunViewer } from '@/features/tasks/components/TaskRunViewer';
import { useTaskRun } from '@/features/tasks/hooks/useTaskRun';
import { TaskRunEvent } from '@/features/tasks/types';
import { buildArtifactDownloadUrl } from '@/features/artifacts/api/artifacts';
import { useRunArtifacts } from '@/features/artifacts/hooks/useRunArtifacts';

function normalizeEvents(logs: Array<Record<string, unknown>> | null): TaskRunEvent[] {
  if (!logs) return [];
  return logs
    .filter((log): log is Record<string, unknown> => typeof log === 'object' && log !== null)
    .filter((log) => typeof log.type === 'string')
    .map((log) => log as TaskRunEvent);
}

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params?.id || null;
  const { data: run, isLoading, error } = useTaskRun(runId);
  const { data: artifacts } = useRunArtifacts(runId);

  if (isLoading) {
    return (
      <Container>
        <p className="text-gray-500">Loading run...</p>
      </Container>
    );
  }

  if (error || !run) {
    return (
      <Container>
        <Card>
          <p className="text-red-700">Failed to load run details.</p>
        </Card>
      </Container>
    );
  }

  const initialEvents = useMemo(() => normalizeEvents(run.logs), [run.logs]);

  return (
    <Container>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Run Details</h1>
            <p className="text-sm text-gray-600 mt-1">Run ID: {run.id}</p>
          </div>
        </div>

        <TaskRunViewer
          runId={run.id}
          initialStatus={run.status}
          initialEvents={initialEvents}
        />

        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Run Metadata</h2>
          <div className="space-y-2 text-sm text-gray-700">
            <p>Task ID: {run.task_id}</p>
            <p>Created: {new Date(run.created_at).toLocaleString()}</p>
            <p>Started: {run.started_at ? new Date(run.started_at).toLocaleString() : '-'}</p>
            <p>Completed: {run.completed_at ? new Date(run.completed_at).toLocaleString() : '-'}</p>
            {run.error_message && <p className="text-red-700">Error: {run.error_message}</p>}
            <p>Artifacts: {artifacts?.length || 0}</p>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Run Artifacts</h2>
          {!artifacts || artifacts.length === 0 ? (
            <p className="text-sm text-gray-500">No artifacts for this run yet.</p>
          ) : (
            <div className="space-y-2">
              {artifacts.map((artifact) => (
                <div key={artifact.id} className="flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{artifact.name}</p>
                    <p className="text-xs text-gray-500">{artifact.artifact_type}</p>
                  </div>
                  <a
                    className="text-sm text-blue-600 hover:text-blue-700"
                    href={buildArtifactDownloadUrl(artifact.id)}
                  >
                    Download
                  </a>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </Container>
  );
}
