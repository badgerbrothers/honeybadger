"use client";

export async function uploadBlobToSignedUrl(
  url: string,
  blob: Blob,
  options: {
    contentType?: string;
    onProgress?: (loaded: number, total: number) => void;
  } = {},
): Promise<string> {
  const { contentType, onProgress } = options;

  return await new Promise<string>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url, true);
    if (contentType) {
      xhr.setRequestHeader("Content-Type", contentType);
    }

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || !onProgress) return;
      onProgress(event.loaded, event.total);
    };

    xhr.onerror = () => {
      reject(new Error("Part upload failed."));
    };

    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(`Part upload failed (${xhr.status}).`));
        return;
      }

      const etag = xhr.getResponseHeader("ETag") ?? xhr.getResponseHeader("Etag");
      if (!etag) {
        reject(new Error("Part upload succeeded but ETag header is missing."));
        return;
      }
      resolve(etag);
    };

    xhr.send(blob);
  });
}
