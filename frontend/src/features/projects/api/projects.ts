import { request } from '@/lib/api';
import { Project, CreateProjectInput } from '@/lib/types';

export async function fetchProjects(): Promise<Project[]> {
  return request<Project[]>('/projects');
}

export async function createProject(data: CreateProjectInput): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
