import { request } from '@/lib/api';
import { Artifact, SavedProjectNode } from '@/lib/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export async function fetchProjectArtifacts(projectId: string): Promise<Artifact[]> {
  return request<Artifact[]>(`/projects/${projectId}/artifacts`);
}

export async function fetchRunArtifacts(runId: string): Promise<Artifact[]> {
  return request<Artifact[]>(`/runs/${runId}/artifacts`);
}

export function buildArtifactDownloadUrl(artifactId: string): string {
  return `${API_BASE}/artifacts/${artifactId}/download`;
}

export async function saveArtifactToProject(artifactId: string): Promise<SavedProjectNode> {
  return request<SavedProjectNode>(`/artifacts/${artifactId}/save-to-project`, {
    method: 'POST',
  });
}
