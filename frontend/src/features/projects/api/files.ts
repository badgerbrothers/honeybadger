import { request } from '@/lib/api';

export interface ProjectFile {
  id: string;
  project_id: string;
  name: string;
  path: string;
  size: number;
  mime_type: string | null;
  created_at: string;
}

export async function uploadProjectFile(
  projectId: string,
  file: File
): Promise<ProjectFile> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost/api'}/projects/${projectId}/files/upload`,
    {
      method: 'POST',
      body: formData,
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail);
  }

  return response.json();
}

export async function fetchProjectFiles(projectId: string): Promise<ProjectFile[]> {
  return request<ProjectFile[]>(`/projects/${projectId}/files`);
}

export async function deleteProjectFile(projectId: string, fileId: string): Promise<void> {
  return request<void>(`/projects/${projectId}/files/${fileId}`, {
    method: 'DELETE',
  });
}
