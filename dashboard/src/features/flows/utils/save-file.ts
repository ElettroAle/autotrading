import type { DownloadedFile } from '@/lib/api-client';

/** Hands the file to the browser, which saves it under its name as any download. */
export const saveFile = ({ name, content }: DownloadedFile): void => {
  const address = URL.createObjectURL(content);
  const link = document.createElement('a');
  link.href = address;
  link.download = name;
  link.click();
  URL.revokeObjectURL(address);
};
