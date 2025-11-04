import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import type { ImageEntry, CandidateOption } from '../App';
import type { AIPreset, RuntimePreset } from '../types/presets';
import { useBackend } from '@desktop/hooks/useBackend';
import { i18n } from '../../i18n';

interface ImageReviewPanelProps {
  image: ImageEntry;
  isOpen: boolean;
  onClose: () => void;
  onApply: (newName: string) => void;
  onSkip: () => void;
  onNext: () => void;
  onPrevious: () => void;
  language: 'zh' | 'en';
  totalImages?: number;
  previousImage?: ImageEntry;
  nextImage?: ImageEntry;
  documentTitle?: string;
  aiPreset: AIPreset;
  runtimePreset: RuntimePreset;
  onUpdateCandidates?: (imageId: string, cands: { name: string; strategy?: string; reason?: string; confidence?: number }[]) => void;
}

export function ImageReviewPanel({ image, isOpen, onClose, onApply, onSkip, onNext, onPrevious, language, totalImages = 0, documentTitle, aiPreset, runtimePreset, onUpdateCandidates }: ImageReviewPanelProps) {
  const text = i18n(language).review;
  const [customName, setCustomName] = useState(image.finalName || '');
  const [translating, setTranslating] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [translateResult, setTranslateResult] = useState('');
  const [summaryResult, setSummaryResult] = useState('');
  const { client } = useBackend();

  const contextText = useMemo(() => {
    return [image.aboveText, image.betweenText, image.belowText].filter(Boolean).join('\n\n');
  }, [image.aboveText, image.betweenText, image.belowText]);

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

  async function handleGenerate() {
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

    const visionSrc = runtimePreset?.vision ? await toDataUrl(image.originalPath) : undefined;

    const payload = {
      document_title: String(documentTitle || ''),
      above_text: image.aboveText || '',
      below_text: image.belowText || '',
      between_text: image.betweenText || '',
      explicit_refs: image.explicitRefs || [],
      alt_text: undefined,
      title_attr: undefined,
      vision_src: visionSrc,
      ai: mapApiConfigToSettings(aiPreset.mainApi),
      verbose: true,
    } as const;
    const resp = await client.generateCandidates(payload as unknown as Record<string, unknown>);
    if (resp.normalized_title) setCustomName(resp.normalized_title);
    if (onUpdateCandidates) onUpdateCandidates(image.id, (resp.candidates || []).map(c => ({ name: c.name || '', strategy: c.strategy, reason: c.reason, confidence: c.confidence })));
  }

  async function handleTranslate(content?: string) {
    setTranslating(true);
    try {
      const target = language === 'zh' ? 'Chinese' : 'English';
      const prompt_template = `Translate the following text to ${target}:\n\n{text}`;
      const resp = await client.processText({
        prompt_template,
        content: content ?? contextText,
        ai: mapApiConfigToSettings(aiPreset.translationApi),
        verbose: false,
      });
      setTranslateResult(resp.result || '');
    } finally {
      setTranslating(false);
    }
  }

  async function handleSummarize(content?: string) {
    setSummarizing(true);
    try {
      const target = language === 'zh' ? 'Chinese' : 'English';
      const prompt_template = `Summarize the following text concisely in ${target}:\n\n{text}`;
      const resp = await client.processText({
        prompt_template,
        content: content ?? contextText,
        ai: mapApiConfigToSettings(aiPreset.summaryApi),
        verbose: false,
      });
      setSummaryResult(resp.result || '');
    } finally {
      setSummarizing(false);
    }
  }

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[720px] p-6">
        <SheetHeader>
          <div className="flex items-center justify-between">
            <SheetTitle>{text.reviewTitle} #{image.index} / {totalImages}</SheetTitle>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={onPrevious}><ChevronLeft className="w-4 h-4 mr-1" />{text.previous}</Button>
              <Button variant="ghost" size="sm" onClick={onNext}>{text.next}<ChevronRight className="w-4 h-4 ml-1" /></Button>
              <Button variant="ghost" size="icon" onClick={onClose} aria-label={text.close}><X className="w-4 h-4" /></Button>
            </div>
          </div>
        </SheetHeader>

        <div className="space-y-4 mt-4">
          <div className="space-y-1">
            <Label>{text.renameTo}</Label>
            <Input value={customName} onChange={(e) => setCustomName(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <Button onClick={() => { onApply(customName.trim()); onNext(); }}>{text.confirmAndContinue}</Button>
            <Button variant="outline" onClick={() => { onApply(customName.trim()); onClose(); }}>{text.confirmAndClose}</Button>
            <Button variant="outline" onClick={handleGenerate}>AI</Button>
            <Button variant="outline" onClick={() => handleTranslate()} disabled={translating}>{text.translate}</Button>
            <Button variant="outline" onClick={() => handleSummarize()} disabled={summarizing}>{text.summarize}</Button>
          </div>

          {/* Candidates list with strategy, reason, confidence */}
          {Array.isArray(image.candidates) && image.candidates.length > 0 && (
            <div className="space-y-2">
              <Label>{text.candidateStrategies}</Label>
              <ScrollArea className="max-h-64 border rounded">
                <div className="p-2 space-y-2">
                  {image.candidates.map((c: CandidateOption, i: number) => (
                    <div key={`${c.name}-${i}`} className="flex items-start justify-between gap-2 p-2 rounded hover:bg-muted/40">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">{c.strategy || '—'}</Badge>
                          {typeof c.confidence === 'number' && (
                            <span className="text-xs text-muted-foreground">{text.confidence}: {Math.round(c.confidence * 100)}%</span>
                          )}
                        </div>
                        <div className="font-medium truncate">{c.name}</div>
                        {c.reason && <div className="text-xs text-muted-foreground whitespace-pre-wrap">{c.reason}</div>}
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={() => setCustomName(c.name)}>{text.use}</Button>
                        <Button size="sm" onClick={() => { setCustomName(c.name); onApply(c.name); }}>{i18n(language).processing.apply}</Button>
                        <Button size="sm" variant="ghost" onClick={() => handleTranslate(c.name)}>{text.translate}</Button>
                        <Button size="sm" variant="ghost" onClick={() => handleSummarize(c.reason || c.name)}>{text.summarize}</Button>
                        {c.reason && (
                          <Button size="sm" variant="ghost" onClick={async () => { try { await navigator.clipboard.writeText(c.reason || ''); alert(text.copiedToClipboard); } catch { /* ignore */ } }}>{text.copyReason}</Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {(translateResult || summarizing || translating) && (
            <div className="space-y-1">
              <Label>{text.translate}</Label>
              <div className="p-2 border rounded min-h-[60px] text-sm whitespace-pre-wrap">{translating ? '…' : translateResult}</div>
            </div>
          )}

          {(summaryResult || summarizing) && (
            <div className="space-y-1">
              <Label>{text.summarize}</Label>
              <div className="p-2 border rounded min-h-[60px] text-sm whitespace-pre-wrap">{summarizing ? '…' : summaryResult}</div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
