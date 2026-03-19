import { request } from '@/lib/api';
import { ModelCatalog } from '@/lib/types';

export async function fetchModelCatalog(): Promise<ModelCatalog> {
  return request<ModelCatalog>('/tasks/models');
}
