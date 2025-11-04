import { useState, useEffect, useCallback } from 'react';
import { AppBar } from './components/AppBar';
import { FileList } from './components/FileList';
import { ProcessingArea } from './components/ProcessingArea';
import { SettingsPanel } from './components/SettingsPanel';
import { LogPanel } from './components/LogPanel';
import { ImageReviewPanel } from './components/ImageReviewPanel';
import { FindReplaceBar } from './components/FindReplaceBar';
import { Toaster } from './components/ui/sonner';
import { usePresets } from './hooks/usePresets';
import { useBackend } from '../hooks/useBackend';
import type {
  BackendApplyResponse,
  BackendCandidateResponse,
  BackendLogEntry,
  BackendPreviewResponse,
  BackendPreviewItem,
} from '../types/backend';
import type { APIConfig, AIPreset, NamingPreset, RuntimePreset } from './types/presets';

export interface MarkdownFile {
  id: string;
  name: string;
  path: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  imageCount: number;
  processedCount: number;
  lastModified: Date;
  title?: string;
}

export interface CandidateOption {
  name: string;
  strategy?: string;
  reason?: string;
  confidence?: number;
}

export interface ImageEntry {
  id: string;
  index: number;
  originalPath: string;
  intent: string;
  candidates: CandidateOption[];
  bestStrategy?: string;
  finalName: string;
  skipped: boolean;
  status: 'pending' | 'processing' | 'completed' | 'error';
  thumbnail?: string;
  aboveText?: string;
  belowText?: string;
  betweenText?: string;
  explicitRefs?: string[];
  aiError?: string | null;
  aiRaw?: string | null;
  requestMode?: string | null;
}

export interface Profile {
  id: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  model: string;
}

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'info' | 'warning' | 'error';
  message: string;
}

const DEFAULT_ATTACH_DIR = 'attachments';

const NAMING_STRATEGY_MAP: Record<NamingPreset['strategy'], string> = {
  seq: 'seq',
  above: 'above',
  below: 'below',
  vision: 'intent',
  hybrid: 'hybrid',
  sci: 'sci',
};

function resolveAIPreset(presets: AIPreset[], id: string) {
  return presets.find(preset => preset.id === id) ?? presets[0];
}

function resolveNamingPreset(presets: NamingPreset[], id: string) {
  return presets.find(preset => preset.id === id) ?? presets[0];
}

function resolveRuntimePreset(presets: RuntimePreset[], id: string) {
  return presets.find(preset => preset.id === id) ?? presets[0];
}

function createMarkdownFileDescriptor(file: File, key: string): MarkdownFile {
  const fileWithPath = file as File & { path?: string };
  return {
    id: key,
    name: file.name,
    path: fileWithPath.path ?? file.name,
    status: 'pending',
    imageCount: 0,
    processedCount: 0,
    lastModified: file.lastModified ? new Date(file.lastModified) : new Date(),
  };
}

function mapApiConfigToSettings(api: APIConfig, runtime: RuntimePreset) {
  return {
    base_url: api.baseUrl,
    api_key: api.apiKey,
    model: api.model,
    timeout: runtime.timeout ?? 120,
    max_retries: runtime.retryCount ?? 3,
    rate_limit: 0.4,
    vision: runtime.vision,
    batch_size: Math.max(1, runtime.concurrency ?? 5),
  };
}

function buildPreviewPayload(
  file: MarkdownFile,
  aiPreset: AIPreset,
  namingPreset: NamingPreset,
  runtimePreset: RuntimePreset,
  language: 'zh' | 'en',
) {
  return {
    md_path: file.path,
    ai: mapApiConfigToSettings(aiPreset.mainApi, runtimePreset),
    naming: {
      strategy: NAMING_STRATEGY_MAP[namingPreset.strategy] ?? 'above',
      template: namingPreset.template,
      seq_width: namingPreset.seqWidth ?? 2,
      max_name_len: namingPreset.maxLength ?? 80,
      intent_language: (namingPreset as any).intentLanguage || 'auto',
      reason_language: (namingPreset as any).reasonLanguage || (language === 'en' ? 'en' : 'zh'),
    },
    runtime: {
      attach_dir_name: runtimePreset.attachDir || DEFAULT_ATTACH_DIR,
      download: runtimePreset.autoSave,
      verbose: true,
      backup: runtimePreset.backup,
    },
  };
}

function toImageEntry(
  fileId: string,
  item: BackendPreviewItem,
): ImageEntry {
  const candidates: CandidateOption[] = Array.isArray(item.candidates)
    ? item.candidates.map((candidate: CandidateOption) => ({
        name: candidate?.name ?? '',
        strategy: candidate?.strategy,
        reason: candidate?.reason,
        confidence:
          typeof candidate?.confidence === 'number'
            ? candidate.confidence
            : undefined,
      }))
    : [];

  const normalizedIntent = item.normalized_title ?? '';
  const suggestedName = item.suggested_name ?? normalizedIntent;

  return {
    id: `img-${fileId}-${item.index}`,
    index: item.index,
    originalPath: item.src,
    intent: normalizedIntent,
    candidates,
    bestStrategy: item.best,
    finalName: suggestedName ?? normalizedIntent,
    skipped: false,
    status: 'pending',
    thumbnail: undefined,
    aboveText: item.above_text ?? '',
    belowText: item.below_text ?? '',
    betweenText: item.between_text ?? '',
    explicitRefs: item.explicit_refs ?? [],
    aiError: item.ai_error ?? null,
    aiRaw: item.ai_raw ?? null,
    requestMode: item.request_mode ?? null,
  };
}

function generateMockEntries(fileId: string, count: number): ImageEntry[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `img-${fileId}-${index + 1}`,
    index: index + 1,
    originalPath: `mock/image_${index + 1}.png`,
    intent: '',
    candidates: [],
    finalName: '',
    skipped: false,
    status: 'pending',
    aboveText: '',
    belowText: '',
    betweenText: '',
    explicitRefs: [],
    aiError: null,
    aiRaw: null,
    requestMode: null,
  }));
}

export default function App() {
  const [files, setFiles] = useState<MarkdownFile[]>([]);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [settingsPanelOpen, setSettingsPanelOpen] = useState(false);
  const [imageEntries, setImageEntries] = useState<ImageEntry[]>([]);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [language, setLanguage] = useState<'zh' | 'en'>('zh');
  const [reviewOpen, setReviewOpen] = useState(false);

  const { client, backendReachable, lastError } = useBackend();
  
  // 棰勮绠＄悊
  const { presets } = usePresets();
  const [selectedAIPresetId, setSelectedAIPresetId] = useState(() => presets.ai[0]?.id || '');
  const [selectedNamingPresetId, setSelectedNamingPresetId] = useState(() => presets.naming[0]?.id || '');
  const [selectedRuntimePresetId, setSelectedRuntimePresetId] = useState(() => presets.runtime[0]?.id || '');
  
  // 褰撻璁惧姞杞藉悗锛屾洿鏂伴€変腑鐨処D锛堝鏋滃綋鍓岻D涓嶅瓨鍦級
  useEffect(() => {
    if (presets.ai.length > 0 && !presets.ai.find(p => p.id === selectedAIPresetId)) {
      setSelectedAIPresetId(presets.ai[0].id);
    }
    if (presets.naming.length > 0 && !presets.naming.find(p => p.id === selectedNamingPresetId)) {
      setSelectedNamingPresetId(presets.naming[0].id);
    }
    if (presets.runtime.length > 0 && !presets.runtime.find(p => p.id === selectedRuntimePresetId)) {
      setSelectedRuntimePresetId(presets.runtime[0].id);
    }
  }, [presets, selectedAIPresetId, selectedNamingPresetId, selectedRuntimePresetId]);
  
  const activeAIPreset = resolveAIPreset(presets.ai, selectedAIPresetId);
  const activeNamingPreset = resolveNamingPreset(presets.naming, selectedNamingPresetId);
  const activeRuntimePreset = resolveRuntimePreset(presets.runtime, selectedRuntimePresetId);

  const selectedFile = files.find(f => f.id === selectedFileId);
  const selectedImage = imageEntries.find(img => img.id === selectedImageId);
  const currentIndex = selectedImage ? imageEntries.findIndex(e => e.id === selectedImage.id) : -1;
  const previousImage = currentIndex > 0 ? imageEntries[currentIndex - 1] : undefined;
  const nextImage = currentIndex >= 0 && currentIndex < imageEntries.length - 1 ? imageEntries[currentIndex + 1] : undefined;

  const addLog = useCallback((level: LogEntry['level'], message: string) => {
    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      timestamp: new Date(),
      level,
      message,
    };
    setLogs(prev => [...prev, entry]);
  }, []);

  const appendBackendLogs = useCallback(
    (entries?: BackendLogEntry[], scope?: string) => {
      if (!entries || entries.length === 0) return;
      setLogs(prev => [
        ...prev,
        ...entries.map((entry, index) => {
          const levelMap: Record<string, LogEntry['level']> = {
            warning: 'warning',
            error: 'error',
            info: 'info',
            debug: 'info',
          };
          const ts = entry.ts ? new Date(entry.ts * 1000) : new Date();
          const level = levelMap[entry.level] ?? 'info';
          const prefix = scope ? `[${scope}] ` : '';
          return {
            id: `${Date.now()}-${index}`,
            timestamp: ts,
            level,
            message: `${prefix}${entry.message}`,
          };
        }),
      ]);
    },
    [],
  );

  const loadImageEntriesForFile = useCallback(
    async (file: MarkdownFile | undefined, resetSelection = false) => {
      if (!file) return;

      if (!backendReachable) {
        const fallbackEntries = generateMockEntries(file.id, file.imageCount || 8);
        setImageEntries(fallbackEntries);
        setFiles(prev => prev.map(item => item.id === file.id
          ? { ...item, status: 'completed', imageCount: fallbackEntries.length, processedCount: 0 }
          : item,
        ));
        if (resetSelection && fallbackEntries.length > 0) setSelectedImageId(fallbackEntries[0].id);
        addLog('warning', 'Backend not reachable, using mock data');
        return;
      }

      const payload = buildPreviewPayload(
        file,
        activeAIPreset,
        activeNamingPreset,
        activeRuntimePreset,
        language,
      );

      setIsProcessing(true);
      setFiles(prev => prev.map(item => item.id === file.id ? { ...item, status: 'processing' } : item));

      try {
        const response = await client.previewDocument(payload);
        const items = (response.items ?? []).map((item: BackendPreviewItem) => toImageEntry(file.id, item));
        setImageEntries(items);
        setFiles(prev => prev.map(item => item.id === file.id
          ? { ...item, title: response.title ?? item.title, status: 'completed', imageCount: response.count ?? items.length, processedCount: 0 }
          : item,
        ));
        if (resetSelection && items.length > 0) setSelectedImageId(items[0].id);
        appendBackendLogs(response.logs, file.name);
        addLog('info', `棰勮瀹屾垚锛?{file.name}锛?{items.length} 寮狅級`);
      } catch (error) {
        addLog('error', `棰勮澶辫触锛?{(error as Error).message}`);
        setFiles(prev => prev.map(item => item.id === file.id ? { ...item, status: 'error' } : item));
      } finally {
        setIsProcessing(false);
      }
    },
    [appendBackendLogs, backendReachable, client, activeAIPreset, activeNamingPreset, activeRuntimePreset, language, addLog],
  );

  // 鏂囦欢鍒楄〃鐩稿叧澶勭悊
  const handleAddFiles = useCallback((incoming: File[]) => {
    if (!incoming || incoming.length === 0) return;
    const mdFiles = incoming.filter(f => f.name.endsWith('.md') || f.name.endsWith('.markdown'));
    if (mdFiles.length === 0) {
      addLog('warning', 'No Markdown files detected');
      return;
    }
    const timestamp = Date.now();
    const newItems = mdFiles.map((f, i) => createMarkdownFileDescriptor(f, `${timestamp}-${i}`));
    const existing = new Set(files.map(it => it.path));
    const deduped = newItems.filter(it => !existing.has(it.path));
    if (deduped.length === 0) {
      addLog('info', 'Files already in list');
      return;
    }
    setFiles(prev => [...prev, ...deduped]);
    setSelectedFileId(deduped[0].id);
    setSelectedImageId(null);
    setReviewOpen(false);
    void loadImageEntriesForFile(deduped[0], true);
  }, [files, addLog, loadImageEntriesForFile]);

  const handleRemoveFiles = useCallback((ids: string[]) => {
    if (!ids || ids.length === 0) return;
    setFiles(prev => prev.filter(f => !ids.includes(f.id)));
    if (ids.includes(selectedFileId ?? '')) {
      setSelectedFileId(null);
      setImageEntries([]);
      setSelectedImageId(null);
      setReviewOpen(false);
    }
  }, [selectedFileId]);

  const handleClearAll = useCallback(() => {
    setFiles([]);
    setSelectedFileId(null);
    setImageEntries([]);
    setSelectedImageId(null);
    setReviewOpen(false);
  }, []);

  const handleSelectFile = useCallback((fileId: string) => {
    setSelectedFileId(fileId);
    setSelectedImageId(null);
    setReviewOpen(false);
    const file = files.find(f => f.id === fileId);
    if (file) void loadImageEntriesForFile(file);
  }, [files, loadImageEntriesForFile]);

  // 鍒楄〃缂栬緫
  const handleUpdateIntent = useCallback((imageId: string, intent: string) => {
    setImageEntries(prev => prev.map(e => e.id === imageId ? { ...e, intent } : e));
  }, []);
  const handleToggleSkip = useCallback((imageId: string) => {
    setImageEntries(prev => prev.map(e => e.id === imageId ? { ...e, skipped: !e.skipped } : e));
  }, []);
  const handleSelectImage = useCallback((imageId: string) => {
    setSelectedImageId(imageId);
    setReviewOpen(true);
  }, []);

  const handleSetCandidates = useCallback((imageId: string, cands: CandidateOption[]) => {
    setImageEntries(prev => prev.map(e => e.id === imageId ? { ...e, candidates: cands } : e));
  }, []);

  // 椤堕儴涓庢帶鍒舵潯
  const handleBatchPreview = useCallback(() => {
    if (selectedFile) void loadImageEntriesForFile(selectedFile, true);
  }, [selectedFile, loadImageEntriesForFile]);
  const handleWriteBack = useCallback(() => {
    if (!selectedFile) {
      addLog('warning', '璇烽€夋嫨瑕佸啓鍥炵殑 Markdown 鏂囦欢');
      return;
    }
    if (imageEntries.length === 0) {
      addLog('warning', '褰撳墠鏂囦欢娌℃湁鍙啓鍥炵殑鍥剧墖鏉＄洰');
      return;
    }

    const payload = {
      ...buildPreviewPayload(
        selectedFile,
        activeAIPreset,
        activeNamingPreset,
        activeRuntimePreset,
        language,
      ),
      chosen_map: Object.fromEntries(
        imageEntries
          .filter((e) => !e.skipped)
          .map((e) => {
            const intent = (e.intent || e.finalName || '').trim();
            return [e.index, intent];
          }),
      ),
      skip_indexes: imageEntries.filter((e) => e.skipped).map((e) => e.index),
    };

    setIsProcessing(true);
    addLog('info', `寮€濮嬪啓鍥烇細${selectedFile.name}`);
    client
      .applyDocument(payload)
      .then((resp) => {
        appendBackendLogs(resp.logs, selectedFile.name);
        const applied = new Set(resp.applied || []);
        setImageEntries((prev) =>
          prev.map((e) =>
            applied.has(e.index) ? { ...e, status: 'completed', skipped: false } : e,
          ),
        );
        addLog('info', `鍐欏洖瀹屾垚锛?{selectedFile.name}`);
      })
      .catch((err) => {
        addLog('error', `鍐欏洖澶辫触锛?{(err as Error).message}`);
      })
      .finally(() => setIsProcessing(false));
  }, [
    selectedFile,
    imageEntries,
    client,
    activeAIPreset,
    activeNamingPreset,
    activeRuntimePreset,
    language,
    addLog,
    appendBackendLogs,
  ]);
  const handleShowFindReplace = useCallback(() => setShowFindReplace(true), []);
  const handleCloseFindReplace = useCallback(() => setShowFindReplace(false), []);
  const handleLanguageChange = useCallback((lang: 'zh' | 'en') => setLanguage(lang), []);
  const handleStopProcessing = useCallback(() => {
    setIsProcessing(false);
    addLog('warning', 'Stop requested (backend cancel not implemented)');
  }, [addLog]);
  const handleOpenSettings = useCallback(() => setSettingsPanelOpen(true), []);
  const handleCloseSettings = useCallback(() => setSettingsPanelOpen(false), []);

  // 鍗曞浘澶嶅
  const handleReviewClose = useCallback(() => setReviewOpen(false), []);
  const handleReviewApply = useCallback((newName: string) => {
    if (!selectedImage) return;
    setImageEntries(prev => prev.map(e => e.id === selectedImage.id ? { ...e, finalName: newName, intent: newName, status: 'completed', skipped: false } : e));
    setReviewOpen(false);
  }, [selectedImage]);
  const handleReviewSkip = useCallback(() => { if (selectedImage) handleToggleSkip(selectedImage.id); }, [handleToggleSkip, selectedImage]);
  const handleReviewNext = useCallback(() => { if (nextImage) setSelectedImageId(nextImage.id); else setReviewOpen(false); }, [nextImage]);
  const handleReviewPrevious = useCallback(() => { if (previousImage) setSelectedImageId(previousImage.id); }, [previousImage]);

  // 鍚庣鍋ュ悍鏃ュ織
  useEffect(() => { if (lastError) addLog('warning', `鍚庣杩炴帴澶辫触锛?{lastError}`); }, [lastError, addLog]);

  // 鍚屾鏂囦欢缁熻
  useEffect(() => {
    if (!selectedFileId) return;
    const processed = imageEntries.filter(e => e.status === 'completed' && !e.skipped).length;
    const total = imageEntries.length;
    setFiles(prev => prev.map(it => it.id === selectedFileId ? { ...it, processedCount: processed, imageCount: total || it.imageCount } : it));
  }, [imageEntries, selectedFileId]);

  return (
    <div className="flex h-screen flex-col">
      <AppBar
        language={language}
        onLanguageChange={handleLanguageChange}
        onOpenSettings={handleOpenSettings}
        isProcessing={isProcessing}
        currentFile={selectedFile?.name}
        aiPresets={presets.ai}
        namingPresets={presets.naming}
        runtimePresets={presets.runtime}
        selectedAIPresetId={selectedAIPresetId}
        selectedNamingPresetId={selectedNamingPresetId}
        selectedRuntimePresetId={selectedRuntimePresetId}
        onAIPresetChange={setSelectedAIPresetId}
        onNamingPresetChange={setSelectedNamingPresetId}
        onRuntimePresetChange={setSelectedRuntimePresetId}
      />

      <div className="flex flex-1 overflow-hidden">
        <FileList
          files={files}
          selectedFileId={selectedFileId}
          onSelectFile={handleSelectFile}
          onAddFiles={handleAddFiles}
          onRemoveFiles={handleRemoveFiles}
          onClearAll={handleClearAll}
          language={language}
        />

        <div className="flex flex-1 flex-col">
          <ProcessingArea
            file={selectedFile}
            imageEntries={imageEntries}
            onBatchPreview={handleBatchPreview}
            onWriteBack={handleWriteBack}
            onUpdateIntent={handleUpdateIntent}
            onToggleSkip={handleToggleSkip}
            onSetCandidates={handleSetCandidates}
            onSelectImage={handleSelectImage}
            onShowFindReplace={handleShowFindReplace}
            onOpenSettings={handleOpenSettings}
            isProcessing={isProcessing}
            language={language}
            presets={presets}
            selectedAIPresetId={selectedAIPresetId}
            selectedNamingPresetId={selectedNamingPresetId}
            selectedRuntimePresetId={selectedRuntimePresetId}
            onSelectAIPreset={setSelectedAIPresetId}
            onSelectNamingPreset={setSelectedNamingPresetId}
            onSelectRuntimePreset={setSelectedRuntimePresetId}
          />

          {showFindReplace && (
            <FindReplaceBar onClose={handleCloseFindReplace} language={language} />
          )}

          <LogPanel
            logs={logs}
            isProcessing={isProcessing}
            onStop={handleStopProcessing}
            language={language}
          />
        </div>
      </div>

      {selectedImage && (
        <ImageReviewPanel
          image={selectedImage}
          isOpen={reviewOpen}
          onClose={() => setReviewOpen(false)}
          onApply={handleReviewApply}
          onSkip={handleReviewSkip}
          onNext={handleReviewNext}
          onPrevious={handleReviewPrevious}
          language={language}
          documentTitle={selectedFile?.title || selectedFile?.name || ''}
          aiPreset={activeAIPreset}
          runtimePreset={activeRuntimePreset}
          onUpdateCandidates={(imageId, cands) => handleSetCandidates(imageId, cands)}
          totalImages={imageEntries.length}
          previousImage={previousImage}
          nextImage={nextImage}
        />
      )}

      <SettingsPanel
        isOpen={settingsPanelOpen}
        onClose={handleCloseSettings}
        language={language}
      />
      <Toaster />
    </div>
  );
}
