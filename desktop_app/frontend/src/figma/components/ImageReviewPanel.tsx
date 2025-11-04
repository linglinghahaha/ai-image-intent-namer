import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import type { ImageEntry } from '../App';
import type { AIPreset, RuntimePreset } from '../types/presets';
import { useBackend } from '../../hooks/useBackend';

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
  const [customName, setCustomName] = useState(image.finalName || '');
  const { client } = useBackend();

  async function handleGenerate() {
    const payload = {
      document_title: String(documentTitle || ''),
      above_text: image.aboveText || '',
      below_text: image.belowText || '',
      between_text: image.betweenText || '',
      explicit_refs: image.explicitRefs || [],
      ai: {
        base_url: aiPreset.mainApi.baseUrl,
        api_key: aiPreset.mainApi.apiKey,
        model: aiPreset.mainApi.model,
        timeout: 120,
        max_retries: 3,
        rate_limit: 0.4,
        vision: runtimePreset.vision,
        batch_size: 5,
      },
      verbose: true,
    } as const;
    const resp = await client.generateCandidates(payload as unknown as Record<string, unknown>);
    if (resp.normalized_title) setCustomName(resp.normalized_title);
    if (onUpdateCandidates) onUpdateCandidates(image.id, (resp.candidates || []).map(c => ({ name: c.name || '', strategy: c.strategy, reason: c.reason, confidence: c.confidence })));
  }

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[720px] p-6">
        <SheetHeader>
          <div className="flex items-center justify-between">
            <SheetTitle>Review #{image.index} / {totalImages}</SheetTitle>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={onPrevious}><ChevronLeft className="w-4 h-4 mr-1" />Prev</Button>
              <Button variant="ghost" size="sm" onClick={onNext}>Next<ChevronRight className="w-4 h-4 ml-1" /></Button>
              <Button variant="ghost" size="icon" onClick={onClose}><X className="w-4 h-4" /></Button>
            </div>
          </div>
        </SheetHeader>

        <div className="space-y-4 mt-4">
          <div className="space-y-1">
            <Label>Rename to</Label>
            <Input value={customName} onChange={(e) => setCustomName(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <Button onClick={() => { onApply(customName.trim()); onNext(); }}>Confirm & Continue</Button>
            <Button variant="outline" onClick={() => { onApply(customName.trim()); onClose(); }}>Confirm & Close</Button>
            <Button variant="outline" onClick={handleGenerate}>Generate</Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}