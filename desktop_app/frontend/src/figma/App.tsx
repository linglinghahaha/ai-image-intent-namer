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
import { useBackend } from '@desktop/hooks/useBackend';
import type { BackendPreviewResponse, BackendPreviewItem } from '@desktop/types/backend';
import type { AIPreset, NamingPreset, RuntimePreset } from './types/presets';

export interface MarkdownFile {
  id: string;
  name: string;
  path: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  imageCount: number;
  processedCount: number;
  lastModified: Date;
}

export interface ImageEntry {
  id: string;
  index: number;
  originalPath: string;
  intent: string;
  candidates: string[];
  finalName: string;
  skipped: boolean;
  status: 'pending' | 'processing' | 'completed' | 'error';
  thumbnail?: string;
  context?: string;
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
  context: 'above',
  vision: 'intent',
  hybrid: 'hybrid',
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

function buildPreviewPayload(
  file: MarkdownFile,
  aiPreset: AIPreset,
  namingPreset: NamingPreset,
  runtimePreset: RuntimePreset,
  language: 'zh' | 'en',
) {
  return {
    md_path: file.path,
    ai: {
      base_url: aiPreset.mainApi.baseUrl,
      api_key: aiPreset.mainApi.apiKey,
      model: aiPreset.mainApi.model,
      timeout: runtimePreset.timeout ?? 120,
      max_retries: runtimePreset.retryCount ?? 3,
      rate_limit: 0.4,
      vision: runtimePreset.vision,
      batch_size: Math.max(1, runtimePreset.concurrency ?? 5),
    },
    naming: {
      strategy: NAMING_STRATEGY_MAP[namingPreset.strategy] ?? 'above',
      template: namingPreset.template,
      seq_width: namingPreset.seqWidth ?? 2,
      max_name_len: namingPreset.maxLength ?? 80,
      intent_language: language === 'en' ? 'en' : 'zh',
      reason_language: language === 'en' ? 'en' : 'zh',
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
  const candidates = Array.isArray(item.candidates)
    ? item.candidates
        .map(candidate => candidate?.name ?? candidate?.intent ?? '')
        .filter(Boolean)
    : [];

  return {
    id: `img-${fileId}-${item.index}`,
    index: item.index,
    originalPath: item.src,
    intent: item.normalized_title ?? '',
    candidates,
    finalName: item.normalized_title ?? '',
    skipped: false,
    status: 'pending',
    thumbnail: undefined,
    context: item.above_text || item.between_text || '',
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
    context: '',
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
  const { client, backendReachable, lastError } = useBackend();
  
  // 预设管理
  const { presets } = usePresets();
  const [selectedAIPresetId, setSelectedAIPresetId] = useState(() => presets.ai[0]?.id || '');
  const [selectedNamingPresetId, setSelectedNamingPresetId] = useState(() => presets.naming[0]?.id || '');
  const [selectedRuntimePresetId, setSelectedRuntimePresetId] = useState(() => presets.runtime[0]?.id || '');
  
  // 当预设加载后，更新选中的ID（如果当前ID不存在）
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

  const addLog = (level: LogEntry['level'], message: string) => {
    const newLog: LogEntry = {
      id: Date.now().toString(),
      timestamp: new Date(),
      level,
      message,
    };
    setLogs(prev => [...prev, newLog]);
  };

  const loadImageEntriesForFile = useCallback(
    async (file: MarkdownFile | undefined, resetSelection = false) => {
      if (!file) {
        return;
      }
      if (!backendReachable) {
        const fallbackEntries = generateMockEntries(file.id, file.imageCount || 8);
        setImageEntries(fallbackEntries);
        setFiles(prev =>
          prev.map(item =>
            item.id === file.id
              ? {
                  ...item,
                  status: 'completed',
                  imageCount: fallbackEntries.length,
                  processedCount: 0,
                }
              : item,
          ),
        );
        if (resetSelection && fallbackEntries.length > 0) {
          setSelectedImageId(fallbackEntries[0].id);
        }
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
      setFiles(prev =>
        prev.map(item =>
          item.id === file.id ? { ...item, status: 'processing' } : item,
        ),
      );

      try {
        const response = await client.previewDocument<BackendPreviewResponse>(payload);
        const items = (response.items ?? []).map(item => toImageEntry(file.id, item));
        setImageEntries(items);
        setFiles(prev =>
          prev.map(item =>
            item.id === file.id
              ? {
                  ...item,
                  status: 'completed',
                  imageCount: response.count ?? items.length,
                  processedCount: 0,
                }
              : item,
          ),
        );
        if (resetSelection && items.length > 0) {
          setSelectedImageId(items[0].id);
        }
        addLog('info', `预览完成：${file.name}（${items.length} 张图像）`);
      } catch (error) {
        addLog('error', `预览失败：${(error as Error).message}`);
        setFiles(prev =>
          prev.map(item =>
            item.id === file.id ? { ...item, status: 'error' } : item,
          ),
        );
      } finally {
        setIsProcessing(false);
      }
    },
    [
      activeAIPreset,
      activeNamingPreset,
      activeRuntimePreset,
      addLog,
      backendReachable,
      client,
      language,
    ],
  );

  useEffect(() => {
    if (lastError) {
      addLog('warning', `后端连接失败：${lastError}`);
    } else if (backendReachable) {
      addLog('info', `后端已连接：${client.baseUrl()}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backendReachable, lastError]);

  const handleAddFiles = useCallback(
    (incomingFiles: File[]) => {
      const timestamp = Date.now();
      const markdownFiles = incomingFiles
        .filter(file => file.name.endsWith('.md') || file.name.endsWith('.markdown'))
        .map((file, idx) =>
          createMarkdownFileDescriptor(file, `file-${timestamp}-${idx}`),
        );

      if (markdownFiles.length === 0) {
        addLog('warning', '未找到 Markdown 文件');
        return;
      }

      setFiles(prev => [...prev, ...markdownFiles]);
      addLog('info', `导入 ${markdownFiles.length} 个 Markdown 文件`);

      const firstFile = markdownFiles[0];
      if (!selectedFileId) {
        setSelectedFileId(firstFile.id);
      }
      void loadImageEntriesForFile(firstFile, true);
    },
    [addLog, loadImageEntriesForFile, selectedFileId],
  );

  const handleRemoveFiles = (fileIds: string[]) => {
    setFiles(prev => prev.filter(f => !fileIds.includes(f.id)));
    if (fileIds.includes(selectedFileId || '')) {
      setSelectedFileId(null);
      setImageEntries([]);
    }
    addLog('info', `Removed ${fileIds.length} file(s)`);
  };

  const handleClearAll = () => {
    setFiles([]);
    setSelectedFileId(null);
    setImageEntries([]);
    addLog('info', 'Cleared all files');
  };

  const handleSelectFile = (fileId: string) => {
    setSelectedFileId(fileId);
    const file = files.find(f => f.id === fileId);
    void loadImageEntriesForFile(file, true);
  };

  const handleBatchPreview = () => {
    if (!selectedFile) {
      return;
    }
    addLog('info', `重新分析：${selectedFile.name}`);
    void loadImageEntriesForFile(selectedFile, true);
  };

  const handleUpdateIntent = (imageId: string, intent: string) => {
    setImageEntries(prev => prev.map(img => 
      img.id === imageId ? { ...img, intent, finalName: img.finalName || intent } : img
    ));
  };

  const handleToggleSkip = (imageId: string) => {
    setImageEntries(prev => prev.map(img => 
      img.id === imageId ? { ...img, skipped: !img.skipped } : img
    ));
  };

  const handleWriteBack = useCallback(async () => {
    if (!selectedFile) {
      addLog('warning', '请先选择文件');
      return;
    }
    if (!backendReachable) {
      addLog('warning', '后端未连接，无法写回');
      return;
    }

    const chosenMap = imageEntries.reduce<Record<number, string>>((acc, entry) => {
      if (!entry.skipped) {
        const name = entry.finalName?.trim() || entry.intent?.trim();
        if (name) {
          acc[entry.index] = name;
        }
      }
      return acc;
    }, {});
    const skipIndexes = imageEntries.filter(entry => entry.skipped).map(entry => entry.index);

    if (Object.keys(chosenMap).length === 0) {
      addLog('warning', '没有可写回的命名结果');
      return;
    }

    const payload = buildPreviewPayload(
      selectedFile,
      activeAIPreset,
      activeNamingPreset,
      activeRuntimePreset,
      language,
    );

    setIsProcessing(true);
    addLog('info', `写回 ${Object.keys(chosenMap).length} 个命名到 ${selectedFile.name}`);

    try {
      await client.applyDocument({
        ...payload,
        chosen_map: chosenMap,
        skip_indexes: skipIndexes,
      });
      addLog('info', '写回完成');
    } catch (error) {
      addLog('error', `写回失败：${(error as Error).message}`);
    } finally {
      setIsProcessing(false);
    }
  }, [
    activeAIPreset,
    activeNamingPreset,
    activeRuntimePreset,
    addLog,
    backendReachable,
    client,
    imageEntries,
    language,
    selectedFile,
  ]);

  return (
    <div className="h-screen flex flex-col bg-background">
      <AppBar
        language={language}
        onLanguageChange={setLanguage}
        onOpenSettings={() => setSettingsPanelOpen(true)}
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

      <div className="flex-1 flex overflow-hidden">
        <FileList
          files={files}
          selectedFileId={selectedFileId}
          onSelectFile={handleSelectFile}
          onAddFiles={handleAddFiles}
          onRemoveFiles={handleRemoveFiles}
          onClearAll={handleClearAll}
          language={language}
        />

        <ProcessingArea
          file={selectedFile}
          imageEntries={imageEntries}
          onBatchPreview={handleBatchPreview}
          onWriteBack={() => {
            void handleWriteBack();
          }}
          onUpdateIntent={handleUpdateIntent}
          onToggleSkip={handleToggleSkip}
          onSelectImage={setSelectedImageId}
          onShowFindReplace={() => setShowFindReplace(true)}
          onOpenSettings={() => setSettingsPanelOpen(true)}
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
      </div>

      <LogPanel
        logs={logs}
        isProcessing={isProcessing}
        onStop={() => setIsProcessing(false)}
        language={language}
      />

      {selectedImage && (
        <ImageReviewPanel
          image={selectedImage}
          isOpen={!!selectedImage}
          onClose={() => setSelectedImageId(null)}
          onApply={(newName) => {
            setImageEntries(prev => prev.map(img => 
              img.id === selectedImage.id ? { ...img, finalName: newName } : img
            ));
            setSelectedImageId(null);
          }}
          onSkip={() => {
            handleToggleSkip(selectedImage.id);
            setSelectedImageId(null);
          }}
          onNext={() => {
            const currentIdx = imageEntries.findIndex(img => img.id === selectedImage.id);
            if (currentIdx < imageEntries.length - 1) {
              setSelectedImageId(imageEntries[currentIdx + 1].id);
            }
          }}
          onPrevious={() => {
            const currentIdx = imageEntries.findIndex(img => img.id === selectedImage.id);
            if (currentIdx > 0) {
              setSelectedImageId(imageEntries[currentIdx - 1].id);
            }
          }}
          language={language}
          totalImages={imageEntries.length}
          previousImage={(() => {
            const currentIdx = imageEntries.findIndex(img => img.id === selectedImage.id);
            return currentIdx > 0 ? imageEntries[currentIdx - 1] : undefined;
          })()}
          nextImage={(() => {
            const currentIdx = imageEntries.findIndex(img => img.id === selectedImage.id);
            return currentIdx < imageEntries.length - 1 ? imageEntries[currentIdx + 1] : undefined;
          })()}
        />
      )}

      {showFindReplace && (
        <FindReplaceBar
          onClose={() => setShowFindReplace(false)}
          language={language}
        />
      )}

      <SettingsPanel
        isOpen={settingsPanelOpen}
        onClose={() => setSettingsPanelOpen(false)}
        language={language}
      />

      <Toaster />
    </div>
  );
}
