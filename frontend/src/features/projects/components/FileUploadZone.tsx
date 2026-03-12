'use client';

import { useState, useRef, DragEvent } from 'react';
import { useUploadFile } from '../hooks/useUploadFile';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

interface FileUploadZoneProps {
  projectId: string;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024;
const ALLOWED_TYPES = ['.txt', '.md', '.markdown', '.pdf', '.json', '.csv'];

export function FileUploadZone({ projectId }: FileUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { mutate: uploadFile, isPending } = useUploadFile(projectId);

  const validateFile = (file: File): string | null => {
    if (file.size > MAX_FILE_SIZE) {
      return `File too large. Maximum size is ${MAX_FILE_SIZE / (1024 * 1024)}MB`;
    }
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_TYPES.includes(ext)) {
      return `File type not allowed. Supported: ${ALLOWED_TYPES.join(', ')}`;
    }
    return null;
  };

  const handleFile = (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    uploadFile(file, {
      onError: (err) => setError(err.message),
    });
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <Card>
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileSelect}
          accept={ALLOWED_TYPES.join(',')}
          disabled={isPending}
        />

        <p className="text-gray-600 mb-4">
          Drag and drop a file here, or click to select
        </p>

        <Button
          onClick={() => fileInputRef.current?.click()}
          disabled={isPending}
        >
          {isPending ? 'Uploading...' : 'Select File'}
        </Button>

        <p className="text-xs text-gray-500 mt-4">
          Supported: {ALLOWED_TYPES.join(', ')} (max {MAX_FILE_SIZE / (1024 * 1024)}MB)
        </p>

        {error && (
          <p className="text-sm text-red-500 mt-4">{error}</p>
        )}
      </div>
    </Card>
  );
}
