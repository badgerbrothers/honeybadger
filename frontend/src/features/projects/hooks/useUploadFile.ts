import { useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadProjectFile } from '../api/files';

export function useUploadFile(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => uploadProjectFile(projectId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectFiles', projectId] });
    },
  });
}
