'use client';

import { useProjectFiles } from '../hooks/useProjectFiles';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteProjectFile } from '../api/files';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface FileListProps {
  projectId: string;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileList({ projectId }: FileListProps) {
  const { data: files, isLoading } = useProjectFiles(projectId);
  const queryClient = useQueryClient();

  const { mutate: deleteFile } = useMutation({
    mutationFn: (fileId: string) => deleteProjectFile(projectId, fileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectFiles', projectId] });
    },
  });

  if (isLoading) {
    return <p className="text-gray-500">Loading files...</p>;
  }

  if (!files || files.length === 0) {
    return (
      <Card>
        <p className="text-gray-500 text-center py-8">No files uploaded yet</p>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="text-lg font-semibold mb-4">Project Files</h3>
      <div className="space-y-2">
        {files.map((file) => (
          <div
            key={file.id}
            className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <div className="flex-1">
              <p className="font-medium text-gray-900">{file.name}</p>
              <p className="text-sm text-gray-500">
                {formatFileSize(file.size)} • {new Date(file.created_at).toLocaleDateString()}
              </p>
            </div>
            <Button
              onClick={() => deleteFile(file.id)}
              className="text-red-600 hover:text-red-700"
            >
              Delete
            </Button>
          </div>
        ))}
      </div>
    </Card>
  );
}
