'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Container } from '@/components/layout/Container';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import {
  buildArtifactDownloadUrl,
  saveArtifactToProject,
} from '@/features/artifacts/api/artifacts';
import { useProjectArtifacts } from '@/features/artifacts/hooks/useProjectArtifacts';

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ProjectArtifactsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id || null;
  const queryClient = useQueryClient();
  const { data: artifacts, isLoading, error } = useProjectArtifacts(projectId);

  const { mutate: saveMutation, isPending: isSaving } = useMutation({
    mutationFn: (artifactId: string) => saveArtifactToProject(artifactId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectFiles', projectId] });
    },
  });

  return (
    <Container>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Project Artifacts</h1>
            {projectId && <p className="text-sm text-gray-600 mt-1">Project ID: {projectId}</p>}
          </div>
          {projectId && (
            <Link href={`/projects/${projectId}`} className="text-sm text-blue-600 hover:text-blue-700">
              Back to project
            </Link>
          )}
        </div>

        <Card>
          {isLoading && <p className="text-gray-500">Loading artifacts...</p>}
          {error && <p className="text-red-700">Failed to load artifacts.</p>}
          {!isLoading && !error && (!artifacts || artifacts.length === 0) && (
            <p className="text-gray-500">No artifacts generated yet.</p>
          )}

          {artifacts && artifacts.length > 0 && (
            <div className="space-y-3">
              {artifacts.map((artifact) => (
                <div key={artifact.id} className="rounded-lg border border-gray-200 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-gray-900">{artifact.name}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {artifact.artifact_type} - {formatSize(artifact.size)} -{' '}
                        {new Date(artifact.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <a
                        className="inline-flex items-center rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                        href={buildArtifactDownloadUrl(artifact.id)}
                      >
                        Download
                      </a>
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={isSaving}
                        onClick={() => saveMutation(artifact.id)}
                      >
                        Save to Project
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </Container>
  );
}
