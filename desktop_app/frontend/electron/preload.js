const { contextBridge } = require('electron');
const fs = require('fs');
const path = require('path');

function extToMime(ext) {
  const map = {
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    gif: 'image/gif',
    webp: 'image/webp',
    bmp: 'image/bmp',
    svg: 'image/svg+xml',
    ico: 'image/x-icon',
    tif: 'image/tiff',
    tiff: 'image/tiff',
    heic: 'image/heic',
  };
  return map[ext.toLowerCase()] || 'application/octet-stream';
}

contextBridge.exposeInMainWorld('electronAPI', {
  readFileAsDataUrl(filePath) {
    try {
      const buf = fs.readFileSync(filePath);
      const ext = (path.extname(filePath) || '').slice(1) || 'png';
      const mime = extToMime(ext);
      const b64 = buf.toString('base64');
      return `data:${mime};base64,${b64}`;
    } catch (e) {
      return null;
    }
  },
});

