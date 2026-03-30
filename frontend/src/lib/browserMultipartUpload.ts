import { uploadBlobToSignedUrl } from "@/lib/minioMultipart";

export interface MultipartUploadPartDescriptor {
  part_number: number;
  url: string;
}

export interface MultipartUploadCompletedPart {
  part_number: number;
  etag: string;
}

export interface UploadMultipartFilePartsOptions {
  file: File;
  partSize: number;
  parts: MultipartUploadPartDescriptor[];
  contentType?: string;
  concurrency?: number;
  onProgress?: (loaded: number, total: number) => void;
}

export const DEFAULT_MULTIPART_UPLOAD_CONCURRENCY = 4;

export async function uploadMultipartFileParts({
  file,
  partSize,
  parts,
  contentType,
  concurrency = DEFAULT_MULTIPART_UPLOAD_CONCURRENCY,
  onProgress,
}: UploadMultipartFilePartsOptions): Promise<MultipartUploadCompletedPart[]> {
  if (parts.length === 0) {
    return [];
  }

  const totalBytes = file.size;
  const completedParts = new Array<MultipartUploadCompletedPart>(parts.length);
  const partLoadedBytes = new Map<number, number>();
  let uploadedBytes = 0;
  let nextIndex = 0;

  const reportProgress = (partNumber: number, loaded: number) => {
    const previousLoaded = partLoadedBytes.get(partNumber) ?? 0;
    if (loaded <= previousLoaded) return;
    uploadedBytes += loaded - previousLoaded;
    partLoadedBytes.set(partNumber, loaded);
    onProgress?.(Math.min(uploadedBytes, totalBytes), totalBytes);
  };

  const uploadOnePart = async (index: number) => {
    const part = parts[index];
    const start = (part.part_number - 1) * partSize;
    const end = Math.min(totalBytes, start + partSize);
    const blob = file.slice(start, end);
    const etag = await uploadBlobToSignedUrl(part.url, blob, {
      contentType: contentType || "application/octet-stream",
      onProgress: (loaded) => reportProgress(part.part_number, loaded),
    });
    reportProgress(part.part_number, blob.size);
    completedParts[index] = { part_number: part.part_number, etag };
  };

  const workerCount = Math.max(1, Math.min(concurrency, parts.length));
  await Promise.all(
    Array.from({ length: workerCount }, async () => {
      while (true) {
        const currentIndex = nextIndex;
        nextIndex += 1;
        if (currentIndex >= parts.length) return;
        await uploadOnePart(currentIndex);
      }
    }),
  );

  return completedParts;
}
