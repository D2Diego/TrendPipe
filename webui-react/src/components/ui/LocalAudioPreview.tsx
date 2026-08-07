import { useEffect, useState } from "react";

export function LocalAudioPreview({ file, label }: { file: File | null; label: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file || typeof URL.createObjectURL !== "function") { setUrl(null); return; }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  return url ? <audio aria-label={label} className="w-full" controls src={url} /> : null;
}
