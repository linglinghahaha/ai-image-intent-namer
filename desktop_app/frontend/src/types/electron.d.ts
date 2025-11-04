export {};

declare global {
  interface Window {
    electronAPI?: {
      readFileAsDataUrl: (filePath: string) => string | null;
    };
  }
}
