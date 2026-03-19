import { useQuery } from '@tanstack/react-query';
import { fetchModelCatalog } from '../api/models';

export function useModelCatalog() {
  return useQuery({
    queryKey: ['taskModelCatalog'],
    queryFn: fetchModelCatalog,
  });
}
