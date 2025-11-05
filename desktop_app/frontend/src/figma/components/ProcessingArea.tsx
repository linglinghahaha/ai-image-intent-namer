import { useEffect, useMemo, useRef, useState } from 'react';
import { useBackend } from '@desktop/hooks/useBackend';
import { RefreshCw, Save, Search, Upload, Filter, ChevronDown, Settings } from 'lucide-react';
import { i18n } from '../../i18n';
import { toast } from 'sonner';

import { Input } from './ui/input';
import { Checkbox } from './ui/checkbox';
import { Badge } from './ui/badge';
import { Label } from './ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';

import type { MarkdownFile, ImageEntry } from '../App';
import type { Presets } from '@figma/types/presets';

interface ProcessingAreaProps {
  file?: MarkdownFile;
  imageEntries: ImageEntry[];
  onBatchPreview: () => void;
  onWriteBack: () => void;
  onUpdateIntent: (imageId: string, intent: string) => void;
  onToggleSkip: (imageId: string) => void;
  onSetCandidates: (imageId: string, cands: { name: string; strategy?: string; reason?: string; confidence?: number }[]) => void;
  onSelectImage: (imageId: string) => void;
  onShowFindReplace: () => void;
  onOpenSettings: () => void;
  isProcessing: boolean;
  language: 'zh' | 'en';
  presets: Presets;
  selectedAIPresetId: string;
  selectedNamingPresetId: string;
  selectedRuntimePresetId: string;
  onSelectAIPreset: (id: string) => void;
  onSelectNamingPreset: (id: string) => void;
  onSelectRuntimePreset: (id: string) => void;
}

export function ProcessingArea({
  file,
  imageEntries,
  onBatchPreview,
  onWriteBack,
  onUpdateIntent,
  onToggleSkip,
  onSetCandidates,
  onSelectImage,
  onShowFindReplace,
  onOpenSettings,
  isProcessing,
  language,
  presets,
  selectedAIPresetId,
  selectedNamingPresetId,
  selectedRuntimePresetId,
  onSelectAIPreset,
  onSelectNamingPreset,
  onSelectRuntimePreset,
}: ProcessingAreaProps) {
  const text = i18n(language).processing;
  const [filterMode, setFilterMode] = useState<'all' | 'pending' | 'skipped'>('all');
  const { client } = useBackend();
  const importRef = useRef<HTMLInputElement | null>(null);
  const fileAbsPath = file?.path || '';
  const [thumbs, setThumbs] = useState<Record<string, string>>({});

  function resolveAbsolutePath(mdPath: string, rel: string): string {
    if (!rel) return rel;
    if (/^([a-zA-Z]:\\|\\\\|\/)/.test(rel)) return rel; // absolute windows/UNC/posix
    const sep = mdPath.includes('\\') ? '\\' : '/';
    const dir = mdPath.replace(/[\\/][^\\/]+$/, '');
    const normRel = rel.replace(/[\\/]+/g, sep);
    return dir + sep + normRel;
  }

  const filteredEntries = useMemo(() => {
    return imageEntries.filter(entry => {
      if (filterMode === 'pending') return entry.status === 'pending' || entry.status === 'processing';
      if (filterMode === 'skipped') return entry.skipped;
      return true;
    });
  }, [imageEntries, filterMode]);

  useEffect(() => {
    if (!file) return;
    const isHttp = (s: string) => /^https?:\/\//i.test(s);
    for (const e of filteredEntries) {
      if (thumbs[e.id]) continue;
      const src = e.originalPath || '';
      if (!src) continue;
      if (isHttp(src)) {
        setThumbs(prev => (prev[e.id] ? prev : { ...prev, [e.id]: src }));
        continue;
      }
      if (window.electronAPI?.readFileAsDataUrl) {
        try {
          const abs = resolveAbsolutePath(file.path, src);
          const data = window.electronAPI.readFileAsDataUrl(abs);
          if (data) setThumbs(prev => ({ ...prev, [e.id]: data }));
        } catch {}
      }
    }
  }, [file, filteredEntries, thumbs]);

  const aiPreset = presets.ai.find(p => p.id === selectedAIPresetId) || presets.ai[0];
  const runtimePreset = presets.runtime.find(p => p.id === selectedRuntimePresetId) || presets.runtime[0];

  function mapApiConfigToSettings(api: { baseUrl: string; apiKey: string; model: string }) {
    return {
      base_url: api.baseUrl,
      api_key: api.apiKey,
      model: api.model,
      timeout: runtimePreset?.timeout ?? 120,
      max_retries: runtimePreset?.retryCount ?? 3,
      rate_limit: 0.4,
      vision: runtimePreset?.vision,
      batch_size: Math.max(1, runtimePreset?.concurrency ?? 5),
    } as const;
  }

  const toDataUrl = async (src: string): Promise<string | undefined> => {
    if (!src) return undefined;
    const isHttp = /^https?:\/\//i.test(src);
    if (isHttp) {
      try {
        const resp = await fetch(src);
        const blob = await resp.blob();
        const b64: string = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
        return b64;
      } catch {
        return undefined;
      }
    }
    if (window.electronAPI?.readFileAsDataUrl) {
      try {
        const isAbs = /^([a-zA-Z]:\\|\\\\|\/)/.test(src);
        const sep = fileAbsPath.includes('\\') ? '\\' : '/';
        const dir = fileAbsPath.replace(/[\\/][^\\/]+$/, '');
        const normRel = src.replace(/[\\/]+/g, sep);
        const abs = isAbs ? src : (dir + sep + normRel);
        return window.electronAPI.readFileAsDataUrl(abs) || undefined;
      } catch {
        return undefined;
      }
    }
    return undefined;
  };

  async function handleGenerate(entry: ImageEntry) {
    if (!file) return;
    try {
      const visionSrc = runtimePreset?.vision ? await toDataUrl(entry.originalPath) : undefined;
      const payload = {
        document_title: (file.title || file.name || '').toString(),
        above_text: entry.aboveText || '',
        below_text: entry.belowText || '',
        between_text: entry.betweenText || '',
        explicit_refs: entry.explicitRefs || [],
        alt_text: undefined,
        title_attr: undefined,
        vision_src: visionSrc,
        ai: mapApiConfigToSettings(aiPreset.mainApi),
        verbose: true,
      } as const;
      const resp = await client.generateCandidates(payload as unknown as Record<string, unknown>);
      const next = (resp.candidates || []).map((c: any) => ({
        name: c.name || '',
        strategy: c.strategy,
        reason: c.reason,
        confidence: typeof c.confidence === 'number' ? c.confidence : undefined,
      }));
      onSetCandidates(entry.id, next);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error(e);
    }
  }

  if (!file) {
    return (
      <div className="flex-1 flex items-center justify-center text-foreground/70">
        <div className="text-center">
          <RefreshCw className="w-16 h-16 mx-auto mb-4 opacity-20" />
          <p>{text.noFile}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="p-3 border-b bg-background space-y-3">
        <Separator />

        <div className="flex items-center gap-2 text-sm">
          <Label className="text-foreground/80">{text.aiModelPreset}</Label>
          <Select value={selectedAIPresetId} onValueChange={onSelectAIPreset}>
            <SelectTrigger className="w-48 h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {presets.ai.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Label className="ml-3 text-foreground/80">{text.namingRulesPreset}</Label>
          <Select value={selectedNamingPresetId} onValueChange={onSelectNamingPreset}>
            <SelectTrigger className="w-48 h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {presets.naming.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Label className="ml-3 text-foreground/80">{text.runtimeOptionsPreset}</Label>
          <Select value={selectedRuntimePresetId} onValueChange={onSelectRuntimePreset}>
            <SelectTrigger className="w-48 h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {presets.runtime.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <button className="ml-auto inline-flex items-center gap-2 text-foreground/80 hover:text-foreground" onClick={onOpenSettings}>
            <Settings className="w-4 h-4" />
            {text.openSettings}
          </button>
        </div>

        <div className="flex gap-2">
          <button className="px-3 py-1.5 border rounded text-sm" onClick={onShowFindReplace}>
            <Search className="w-4 h-4 mr-2 inline-block" />
            {text.findReplace}
          </button>
          <button className="px-3 py-1.5 border rounded text-sm" onClick={() => importRef.current?.click()}>
            <Upload className="w-4 h-4 mr-2 inline-block" />
            {text.importIntent}
          </button>
          <button
            className="px-3 py-1.5 border rounded text-sm"
            onClick={async () => {
              if (!file) return;
              try {
                await client.prefetchAttachments({
                  md_path: file.path,
                  runtime: {
                    attach_dir_name: runtimePreset.attachDir,
                    timeout: runtimePreset.timeout,
                  },
                  backup: runtimePreset.backup,
                } as any);
                toast.success(language === 'zh' ? '附件预下载完成' : 'Prefetch completed');
              } catch {}
            }}
          >
            {text.prefetchAttachments ?? (language === 'zh' ? '附件预下载' : 'Prefetch Attachments')}
          </button>
          <button
            className="px-3 py-1.5 border rounded text-sm"
            onClick={async () => {
              if (!file) return;
              try {
                const r: any = await client.normalizeHtml({ md_path: file.path, backup: true } as any);
                if (r.updated && r.count > 0) {
                  toast.success(language === 'zh' ? `规范化完成：${r.count} 处` : `Normalized ${r.count} changes`);
                } else {
                  toast.message(language === 'zh' ? '无需规范化' : 'No changes');
                }
              } catch {}
            }}
          >
            {text.normalizeHtml ?? (language === 'zh' ? '规范化HTML图片' : 'Normalize HTML <img>')}
          </button>
          <input
            ref={importRef}
            type="file"
            accept="application/json"
            className="hidden"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              try {
                const txt = await f.text();
                const obj = JSON.parse(txt) as Record<string, string>;
                const updates = new Map<string, string>();
                for (const [k, v] of Object.entries(obj)) updates.set(k, String(v || ''));
                imageEntries.forEach((entry) => {
                  const byIndex = updates.get(String(entry.index));
                  const byPath = updates.get(entry.originalPath) || Array.from(updates.keys()).find(key => entry.originalPath.endsWith(key));
                  const picked = byIndex || (byPath ? updates.get(byPath) : undefined);
                  if (picked) onUpdateIntent(entry.id, picked);
                });
              } catch (err) {
                // eslint-disable-next-line no-console
                console.error('import intents failed', err);
              } finally {
                e.currentTarget.value = '';
              }
            }}
          />
          <button className="px-3 py-1.5 border rounded text-sm" onClick={onWriteBack} disabled={isProcessing}>
            <Save className="w-4 h-4 mr-2 inline-block" />
            {text.writeBack}
          </button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="px-3 py-1.5 border rounded text-sm">
                <Filter className="w-4 h-4 mr-2 inline-block" />
                {text.filter}
                <ChevronDown className="w-4 h-4 ml-2 inline-block" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setFilterMode('all')}>{text.all}</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilterMode('pending')}>{text.pending}</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilterMode('skipped')}>{text.skipped}</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <ScrollArea className="flex-1 bg-background">
        <Table className="text-foreground">
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">{text.index}</TableHead>
              <TableHead className="w-24">{text.thumbnail}</TableHead>
              <TableHead className="w-48">{text.originalPath}</TableHead>
              <TableHead>{text.intent}</TableHead>
              <TableHead className="w-24">{text.candidates}</TableHead>
              <TableHead className="w-48">{text.finalName}</TableHead>
              <TableHead className="w-20">{text.skip}</TableHead>
              <TableHead className="w-32">{text.actions}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEntries.map((entry) => (
              <TableRow key={entry.id} className={entry.skipped ? 'opacity-50' : ''}>
                <TableCell>{entry.index}</TableCell>
                <TableCell>
                  <div className="w-16 h-16 bg-background rounded flex items-center justify-center overflow-hidden">
                    {thumbs[entry.id] ? (
                      <img src={thumbs[entry.id]} className="object-contain w-full h-full" />
                    ) : (
                      <span className="text-xs text-foreground/70" title={language === 'zh' ? '未找到图片或无法读取' : 'Not found or unreadable'}>IMG</span>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-sm">
                  <div className="max-w-[520px]">
                    <Input
                      readOnly
                      value={entry.originalPath}
                      title={entry.originalPath}
                      onFocus={(e) => e.currentTarget.select()}
                      className="h-8 bg-background border px-3 overflow-x-auto whitespace-nowrap cursor-text"
                    />
                  </div>
                </TableCell>
                <TableCell>
                  <Input
                    value={entry.intent}
                    onChange={(e) => onUpdateIntent(entry.id, e.target.value)}
                    placeholder={text.intent}
                    className="min-w-[200px]"
                    disabled={entry.skipped}
                  />
                </TableCell>
                <TableCell>
                  {entry.candidates.length > 0 && (
                    <Badge variant="secondary">{entry.candidates.length}</Badge>
                  )}
                </TableCell>
                <TableCell className="text-sm">{entry.finalName}</TableCell>
                <TableCell>
                  <Checkbox checked={entry.skipped} onCheckedChange={() => onToggleSkip(entry.id)} />
                </TableCell>
                <TableCell>
                  <button className="px-2 py-1 border rounded text-xs mr-2" onClick={() => handleGenerate(entry)}>AI</button>
                  <button className="px-2 py-1 text-xs" onClick={() => onSelectImage(entry.id)}>{text.review}</button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  );
}

