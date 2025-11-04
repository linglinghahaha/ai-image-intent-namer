import { useState } from 'react';
import { useBackend } from '@desktop/hooks/useBackend';
import { RefreshCw, Save, Search, Upload, Filter, ChevronDown, Settings } from 'lucide-react';
import { i18n } from '../../i18n';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Checkbox } from './ui/checkbox';
import { Badge } from './ui/badge';
import { Label } from './ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
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

  async function handleGenerate(entry: ImageEntry) {
    if (!file) return;
    try {
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
            return window.electronAPI.readFileAsDataUrl(src) || undefined;
          } catch {
            return undefined;
          }
        }
        return undefined;
      };

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
      const next = (resp.candidates || []).map((c) => ({
        name: c.name || '',
        strategy: c.strategy,
        reason: c.reason,
        confidence: typeof c.confidence === 'number' ? c.confidence : undefined,
      }));
      onSetCandidates(entry.id, next);
      if (resp.normalized_title) {
        onUpdateIntent(entry.id, resp.normalized_title);
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error(e);
    }
  }

  const filteredEntries = imageEntries.filter(entry => {
    if (filterMode === 'pending') return entry.status === 'pending' || entry.status === 'processing';
    if (filterMode === 'skipped') return entry.skipped;
    return true;
  });

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
      <div className="p-3 border-b bg-background space-y-3">\n<Separator />
        
        {/* 闁哄鐗嗛幊搴㈡叏椤忓牆绀夐柣鏃囶嚙閸樻挳鏌熺粙娆炬█闁?*/}
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={onShowFindReplace}>
            <Search className="w-4 h-4 mr-2" />
            {text.findReplace}
          </Button>
          <Button size="sm" variant="outline">
            <Upload className="w-4 h-4 mr-2" />
            {text.importIntent}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onWriteBack}
            disabled={isProcessing}
          >
            <Save className="w-4 h-4 mr-2" />
            {text.writeBack}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="outline">
                <Filter className="w-4 h-4 mr-2" />
                {text.filter}
                <ChevronDown className="w-4 h-4 ml-2" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setFilterMode('all')}>
                {text.all}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilterMode('pending')}>
                {text.pending}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFilterMode('skipped')}>
                {text.skipped}
              </DropdownMenuItem>
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
                  <div className="w-16 h-16 bg-background rounded flex items-center justify-center">
                    <span className="text-xs text-foreground/70">IMG</span>
                  </div>
                </TableCell>
                <TableCell className="text-sm">{entry.originalPath}</TableCell>
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
                    <Badge variant="secondary">
                      {entry.candidates.length}
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-sm">{entry.finalName}</TableCell>
                <TableCell>
                  <Checkbox
                    checked={entry.skipped}
                    onCheckedChange={() => onToggleSkip(entry.id)}
                  />
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="outline"
                    className="mr-2"
                    onClick={() => handleGenerate(entry)}
                  >
                    AI
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onSelectImage(entry.id)}
                  >
                    {text.review}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  );
}

