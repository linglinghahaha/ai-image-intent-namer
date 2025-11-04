import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { Switch } from './ui/switch';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from './ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { ImageWithFallback } from './figma/ImageWithFallback';
import type { ImageEntry, CandidateOption } from '../App';
import { toast } from 'sonner';
import { useBackend } from '@desktop/hooks/useBackend';
import type { AIPreset, RuntimePreset } from '../types/presets';

type CandidateItem = {
  name: string;
  strategy?: string;
  confidence?: number;
  reason?: string;
};

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
  onUpdateCandidates?: (imageId: string, cands: CandidateOption[]) => void;
}

const t = {
  zh: {
    reviewTitle: '单图复审',
    status: { pending: '待确认', skipped: '已跳过', completed: '已写回', processing: '生成中' },
    markSkipped: '标记跳过',
    close: '关闭',
    previous: '上一张',
    next: '下一张',
    imageTitle: '图片',
    source: '来源',
    document: '文档',
    adjacentImages: '邻接图片',
    previousImageLabel: '上一张',
    nextImageLabel: '下一张',
    noImage: '暂无图片',
    previousContext: '上文',
    nextContext: '下文',
    characterCount: '字符',
    translate: '翻译',
    summarize: '归纳',
    candidateStrategies: '候选策略',
    strategy: { prevContext3: '上文候选', nextContext3: '下文候选', directIntent: '直接意图', phonetic: '音意' },
    confidence: '置信',
    renameTo: '重命名为',
    confirmAndContinue: '确定并继续',
    confirmAndClose: '确定并关闭',
    cancel: '取消',
    copiedToClipboard: '已复制到剪贴板',
    translationResult: '翻译结果',
    summaryResult: '摘要结果',
    copy: '复制',
  },
  en: {
    reviewTitle: 'Image Review',
    status: { pending: 'Pending', skipped: 'Skipped', completed: 'Completed', processing: 'Processing' },
    markSkipped: 'Mark as Skipped',
    close: 'Close',
    previous: 'Previous',
    next: 'Next',
    imageTitle: 'Image',
    source: 'Source',
    document: 'Document',
    adjacentImages: 'Adjacent Images',
    previousImageLabel: 'Previous',
    nextImageLabel: 'Next',
    noImage: 'No Image',
    previousContext: 'Previous Context',
    nextContext: 'Next Context',
    characterCount: 'chars',
    translate: 'Translate',
    summarize: 'Summarize',
    candidateStrategies: 'Candidate Strategies',
    strategy: { prevContext3: 'Prev Context', nextContext3: 'Next Context', directIntent: 'Direct Intent', phonetic: 'Phonetic' },
    confidence: 'Confidence',
    renameTo: 'Rename to',
    confirmAndContinue: 'Confirm & Continue',
    confirmAndClose: 'Confirm & Close',
    cancel: 'Cancel',
    copiedToClipboard: 'Copied to clipboard',
    translationResult: 'Translation',
    summaryResult: 'Summary',
    copy: 'Copy',
  },
} as const;

export function ImageReviewPanel({
  image,
  isOpen,
  onClose,
  onApply,
  onSkip,
  onNext,
  onPrevious,
  language,
  totalImages = 0,
  previousImage,
  nextImage,
  documentTitle,
  aiPreset,
  runtimePreset,
  onUpdateCandidates,
}: ImageReviewPanelProps) {
  const text = t[language];
  const { client } = useBackend();

  const [customName, setCustomName] = useState('');
  const [isSkipped, setIsSkipped] = useState(image.skipped);
  const [selectedCandidate, setSelectedCandidate] = useState('');

  // Context around image
  const previousContextText = image.aboveText || '';
  const nextContextText = image.belowText || '';

  // Candidates
  const [liveCandidates, setLiveCandidates] = useState<CandidateItem[]>(() =>
    (image.candidates || []).map((c) => ({
      name: c.name || '',
      strategy: c.strategy,
      confidence: c.confidence,
      reason: c.reason,
    })),
  );
  const [generating, setGenerating] = useState(false);

  // Text processing results
  const [prevTranslation, setPrevTranslation] = useState('');
  const [prevSummary, setPrevSummary] = useState('');
  const [nextTranslation, setNextTranslation] = useState('');
  const [nextSummary, setNextSummary] = useState('');
  const [procPrevTranslating, setProcPrevTranslating] = useState(false);
  const [procPrevSummarizing, setProcPrevSummarizing] = useState(false);
  const [procNextTranslating, setProcNextTranslating] = useState(false);
  const [procNextSummarizing, setProcNextSummarizing] = useState(false);

  useEffect(() => {
    setCustomName(image.finalName || '');
    setIsSkipped(image.skipped);
    setSelectedCandidate('');
    setLiveCandidates((image.candidates || []).map((c) => ({
      name: c.name || '',
      strategy: c.strategy,
      confidence: c.confidence,
      reason: c.reason,
    })));
    setPrevTranslation(''); setPrevSummary(''); setNextTranslation(''); setNextSummary('');
  }, [image.id, image.finalName, image.skipped]);

  const statusBadge = useMemo(() => {
    if (isSkipped) return <Badge variant="secondary">{text.status.skipped}</Badge>;
    if (image.status === 'completed') return <Badge variant="default">{text.status.completed}</Badge>;
    if (image.status === 'processing') return <Badge variant="default">{text.status.processing}</Badge>;
    return <Badge variant="outline">{text.status.pending}</Badge>;
  }, [image.status, isSkipped, text.status]);

  function mapApiConfigToSettings(api: { baseUrl: string; apiKey: string; model: string }) {
    return {
      base_url: api.baseUrl,
      api_key: api.apiKey,
      model: api.model,
      timeout: runtimePreset.timeout ?? 120,
      max_retries: runtimePreset.retryCount ?? 3,
      rate_limit: 0.4,
      vision: runtimePreset.vision,
      batch_size: Math.max(1, runtimePreset.concurrency ?? 5),
    } as const;
  }

  async function processText(content: string, kind: 'translate' | 'summarize') {
    const target = language === 'en' ? 'English' : 'Chinese';
    const tpl = kind === 'translate'
      ? `Translate the following text to ${target}:\n{text}`
      : `Summarize the following text concisely in ${target}:\n{text}`;
    const api = kind === 'translate' ? aiPreset.translationApi : aiPreset.summaryApi;
    const payload = {
      prompt_template: tpl,
      content,
      ai: mapApiConfigToSettings(api),
      verbose: true,
    };
    const resp = await client.processText(payload as unknown as Record<string, unknown>);
    return resp.result || '';
  }

  async function handleGenerateCandidates() {
    try {
      setGenerating(true);
      const payload = {
        document_title: (documentTitle || '').toString(),
        above_text: image.aboveText || '',
        below_text: image.belowText || '',
        between_text: image.betweenText || '',
        explicit_refs: image.explicitRefs || [],
        alt_text: undefined,
        title_attr: undefined,
        vision_src: runtimePreset.vision ? image.originalPath : undefined,
        ai: mapApiConfigToSettings(aiPreset.mainApi),
        verbose: true,
      } as const;
      const resp = await client.generateCandidates(payload as unknown as Record<string, unknown>);
      const next = (resp.candidates || []).map((c) => ({
        name: c.name || '',
        strategy: c.strategy,
        confidence: c.confidence,
        reason: c.reason,
      }));
      setLiveCandidates(next);
      if (onUpdateCandidates) onUpdateCandidates(image.id, next);
      if (resp.normalized_title) {
        setSelectedCandidate(resp.normalized_title);
        setCustomName(resp.normalized_title);
      }
      toast.success(language === 'en' ? 'Candidates generated' : '候选已生成');
    } catch (e) {
      toast.error((language === 'en' ? 'Generate failed: ' : '生成失败：') + (e as Error).message);
    } finally {
      setGenerating(false);
    }
  }

  const handleToggleSkip = () => {
    setIsSkipped(!isSkipped);
    if (!isSkipped) onSkip();
  };

  const handleConfirmAndContinue = () => {
    const finalName = customName.trim();
    if (!finalName) return;
    onApply(finalName);
    onNext();
    toast.success(language === 'en' ? 'Applied' : '已应用');
  };

  const handleConfirmAndClose = () => {
    const finalName = customName.trim();
    if (!finalName) return;
    onApply(finalName);
    onClose();
    toast.success(language === 'en' ? 'Applied' : '已应用');
  };

  const handleCopy = async (textToCopy: string) => {
    if (!textToCopy) return;
    try { await navigator.clipboard.writeText(textToCopy); toast.success(text.copiedToClipboard); } catch { /* noop */ }
  };

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[98vw] max-w-[1800px] p-0 flex flex-col">
        <SheetHeader className="px-6 py-3 border-b flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <SheetTitle className="text-lg">{text.reviewTitle} #{image.index} / {totalImages}</SheetTitle>
              {statusBadge}
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="skip-toggle" className="text-sm cursor-pointer">{text.markSkipped}</Label>
              <Switch id="skip-toggle" checked={isSkipped} onCheckedChange={handleToggleSkip} />
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={onPrevious}><ChevronLeft className="w-4 h-4 mr-1" />{text.previous}</Button>
              <Button variant="ghost" size="sm" onClick={onNext}>{text.next}<ChevronRight className="w-4 h-4 ml-1" /></Button>
              <Button variant="ghost" size="icon" onClick={onClose}><X className="w-4 h-4" /></Button>
            </div>
          </div>
          <SheetDescription className="sr-only">Review and edit image naming for {image.originalPath}</SheetDescription>
        </SheetHeader>

        <div className="flex-1 flex overflow-hidden">
          {/* Left: image info */}
          <div className="w-[45%] border-r flex flex-col bg-muted/30">
            <div className="p-4 space-y-3">
              <div className="space-y-2">
                <h3 className="font-medium">{text.imageTitle} #{image.index}</h3>
                <div className="text-sm space-y-1">
                  <div className="flex gap-2"><span className="text-muted-foreground min-w-12">{text.source}:</span><span className="font-mono text-xs break-all">{image.originalPath}</span></div>
                  <div className="flex gap-2"><span className="text-muted-foreground min-w-12">{text.document}:</span><span className="text-xs">{documentTitle || '-'}</span></div>
                </div>
              </div>
              <Separator />
              <div className="bg-background rounded-lg border p-4">
                <div className="aspect-square bg-muted/50 rounded flex items-center justify-center overflow-hidden">
                  <ImageWithFallback src={image.thumbnail || '/placeholder-image.png'} alt={image.originalPath} className="w-full h-full object-contain" />
                </div>
              </div>
              <Separator />
              <div className="space-y-2">
                <Label className="text-sm">{text.adjacentImages}</Label>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs text-muted-foreground">{text.previousImageLabel}</Label>
                    <div className="aspect-video bg-muted rounded border cursor-pointer hover:border-primary transition-colors overflow-hidden" onClick={onPrevious}>
                      {previousImage ? <ImageWithFallback src={previousImage.thumbnail || '/placeholder-image.png'} alt={previousImage.originalPath} className="w-full h-full object-cover" /> : <div className="w-full h-full flex items-center justify-center text-xs text-muted-foreground">{text.noImage}</div>}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs text-muted-foreground">{text.nextImageLabel}</Label>
                    <div className="aspect-video bg-muted rounded border cursor-pointer hover:border-primary transition-colors overflow-hidden" onClick={onNext}>
                      {nextImage ? <ImageWithFallback src={nextImage.thumbnail || '/placeholder-image.png'} alt={nextImage.originalPath} className="w-full h-full object-cover" /> : <div className="w-full h-full flex items-center justify-center text-xs text-muted-foreground">{text.noImage}</div>}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: context + candidates */}
          <div className="flex-1 flex flex-col">
            <Tabs defaultValue="prev" className="flex-1 flex flex-col">
              <div className="border-b px-4 pt-3"><TabsList className="w-full grid grid-cols-2"><TabsTrigger value="prev">{text.previousContext}</TabsTrigger><TabsTrigger value="next">{text.nextContext}</TabsTrigger></TabsList></div>

              <TabsContent value="prev" className="flex-1 flex flex-col m-0 overflow-hidden">
                <div className="p-4 space-y-3 flex-1 flex flex-col overflow-hidden">
                  <div className="flex items-center justify-between flex-shrink-0">
                    <span className="text-sm text-muted-foreground">{text.characterCount}: {previousContextText.length}</span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" disabled={procPrevTranslating} onClick={async () => { try { setProcPrevTranslating(true); const res = await processText(previousContextText, 'translate'); setPrevTranslation(res); } finally { setProcPrevTranslating(false); } }}>{text.translate}</Button>
                      <Button variant="outline" size="sm" disabled={procPrevSummarizing} onClick={async () => { try { setProcPrevSummarizing(true); const res = await processText(previousContextText, 'summarize'); setPrevSummary(res); } finally { setProcPrevSummarizing(false); } }}>{text.summarize}</Button>
                    </div>
                  </div>
                  <ScrollArea className="flex-1 border rounded-lg"><div className="p-3 text-sm whitespace-pre-wrap">{previousContextText}</div></ScrollArea>
                  <div className="grid grid-cols-2 gap-3 mt-3">
                    <div className="space-y-2"><Label className="text-xs">{text.translationResult}</Label><ScrollArea className="h-24 border rounded"><div className="p-2 text-sm whitespace-pre-wrap">{prevTranslation || (language === 'en' ? 'No result' : '暂无')}</div></ScrollArea><div className="flex justify-end"><Button size="sm" variant="outline" onClick={() => handleCopy(prevTranslation)} disabled={!prevTranslation}>{text.copy}</Button></div></div>
                    <div className="space-y-2"><Label className="text-xs">{text.summaryResult}</Label><ScrollArea className="h-24 border rounded"><div className="p-2 text-sm whitespace-pre-wrap">{prevSummary || (language === 'en' ? 'No result' : '暂无')}</div></ScrollArea><div className="flex justify-end"><Button size="sm" variant="outline" onClick={() => handleCopy(prevSummary)} disabled={!prevSummary}>{text.copy}</Button></div></div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="next" className="flex-1 flex flex-col m-0 overflow-hidden">
                <div className="p-4 space-y-3 flex-1 flex flex-col overflow-hidden">
                  <div className="flex items-center justify-between flex-shrink-0">
                    <span className="text-sm text-muted-foreground">{text.characterCount}: {nextContextText.length}</span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" disabled={procNextTranslating} onClick={async () => { try { setProcNextTranslating(true); const res = await processText(nextContextText, 'translate'); setNextTranslation(res); } finally { setProcNextTranslating(false); } }}>{text.translate}</Button>
                      <Button variant="outline" size="sm" disabled={procNextSummarizing} onClick={async () => { try { setProcNextSummarizing(true); const res = await processText(nextContextText, 'summarize'); setNextSummary(res); } finally { setProcNextSummarizing(false); } }}>{text.summarize}</Button>
                    </div>
                  </div>
                  <ScrollArea className="flex-1 border rounded-lg"><div className="p-3 text-sm whitespace-pre-wrap">{nextContextText}</div></ScrollArea>
                  <div className="grid grid-cols-2 gap-3 mt-3">
                    <div className="space-y-2"><Label className="text-xs">{text.translationResult}</Label><ScrollArea className="h-24 border rounded"><div className="p-2 text-sm whitespace-pre-wrap">{nextTranslation || (language === 'en' ? 'No result' : '暂无')}</div></ScrollArea><div className="flex justify-end"><Button size="sm" variant="outline" onClick={() => handleCopy(nextTranslation)} disabled={!nextTranslation}>{text.copy}</Button></div></div>
                    <div className="space-y-2"><Label className="text-xs">{text.summaryResult}</Label><ScrollArea className="h-24 border rounded"><div className="p-2 text-sm whitespace-pre-wrap">{nextSummary || (language === 'en' ? 'No result' : '暂无')}</div></ScrollArea><div className="flex justify-end"><Button size="sm" variant="outline" onClick={() => handleCopy(nextSummary)} disabled={!nextSummary}>{text.copy}</Button></div></div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            <Separator />

            {/* Candidates */}
            <div className="p-4 space-y-3 max-h-[40vh] overflow-hidden flex flex-col">
              <div className="flex items-center justify-between">
                <Label className="text-sm">{text.candidateStrategies}</Label>
                <Button size="sm" variant="outline" onClick={handleGenerateCandidates} disabled={generating}>{generating ? (language === 'en' ? 'Generating…' : '生成中…') : (language === 'en' ? 'Generate' : '生成候选')}</Button>
              </div>
              <ScrollArea className="flex-1">
                <div className="space-y-2 pr-4">
                  {liveCandidates.map((candidate, idx) => (
                    <div key={idx} className={`p-3 border rounded-lg cursor-pointer hover:bg-accent transition-colors ${selectedCandidate === candidate.name ? 'border-primary bg-accent' : ''}`} onClick={() => { setSelectedCandidate(candidate.name); setCustomName(candidate.name); }}>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="text-xs">{text.strategy[(candidate.strategy || 'directIntent') as keyof typeof text.strategy] || candidate.strategy}</Badge>
                            {typeof candidate.confidence === 'number' && (
                              <span className="text-xs text-muted-foreground">{text.confidence}: {candidate.confidence.toFixed(2)}</span>
                            )}
                          </div>
                          <code className="text-sm font-mono">{candidate.name}</code>
                        </div>
                      </div>
                      {candidate.reason && <p className="text-xs text-muted-foreground mt-2">{candidate.reason}</p>}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>

            <Separator />

            {/* Rename */}
            <div className="p-4 space-y-3 flex-shrink-0 bg-muted/30">
              <div className="space-y-2">
                <Label className="text-sm">{text.renameTo}</Label>
                <Input value={customName} onChange={(e) => setCustomName(e.target.value)} placeholder="domain_name_humor" className="font-mono" />
              </div>
              <div className="flex gap-2">
                <Button className="flex-1" onClick={handleConfirmAndContinue}>{text.confirmAndContinue}</Button>
                <Button variant="outline" className="flex-1" onClick={handleConfirmAndClose}>{text.confirmAndClose}</Button>
                <Button variant="outline" onClick={onClose}>{text.cancel}</Button>
              </div>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}