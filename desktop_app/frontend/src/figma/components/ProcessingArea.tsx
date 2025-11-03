import { useState } from 'react';
import { RefreshCw, Save, Search, Upload, Filter, ChevronDown, Settings } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Checkbox } from './ui/checkbox';
import { Badge } from './ui/badge';
import { Label } from './ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
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
import type { Presets } from '../types/presets';

interface ProcessingAreaProps {
  file?: MarkdownFile;
  imageEntries: ImageEntry[];
  onBatchPreview: () => void;
  onWriteBack: () => void;
  onUpdateIntent: (imageId: string, intent: string) => void;
  onToggleSkip: (imageId: string) => void;
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

const t = {
  zh: {
    noFile: '请从左侧选择或添加文件',
    fileInfo: '文件信息',
    step1: '步骤 1: 文件选择',
    step2: '步骤 2: 处理控制台',
    aiModelPreset: 'AI 模型预设',
    namingRulesPreset: '命名规则预设',
    runtimeOptionsPreset: '运行选项预设',
    openSettings: '打开设置',
    batchPreview: '开始批量预览',
    writeBack: '批量写回',
    findReplace: '查找替换',
    importIntent: '导入意图',
    filter: '过滤',
    all: '全部',
    pending: '待确认',
    skipped: '已跳过',
    index: '序号',
    thumbnail: '预览',
    originalPath: '原始路径',
    intent: 'AI 意图',
    candidates: '候选',
    finalName: '最终命名',
    skip: '跳过',
    actions: '操作',
    review: '复审',
    apply: '应用',
    images: '张图片',
    total: '共',
  },
  en: {
    noFile: 'Please select or add a file from the left panel',
    fileInfo: 'File Information',
    step1: 'Step 1: File Selection',
    step2: 'Step 2: Processing Console',
    aiModelPreset: 'AI Model Preset',
    namingRulesPreset: 'Naming Rules Preset',
    runtimeOptionsPreset: 'Runtime Options Preset',
    openSettings: 'Open Settings',
    batchPreview: 'Start Batch Preview',
    writeBack: 'Write Back',
    findReplace: 'Find & Replace',
    importIntent: 'Import Intent',
    filter: 'Filter',
    all: 'All',
    pending: 'Pending',
    skipped: 'Skipped',
    index: 'Index',
    thumbnail: 'Preview',
    originalPath: 'Original Path',
    intent: 'AI Intent',
    candidates: 'Candidates',
    finalName: 'Final Name',
    skip: 'Skip',
    actions: 'Actions',
    review: 'Review',
    apply: 'Apply',
    images: 'images',
    total: 'Total',
  },
};

export function ProcessingArea({
  file,
  imageEntries,
  onBatchPreview,
  onWriteBack,
  onUpdateIntent,
  onToggleSkip,
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
  const text = t[language];
  const [filterMode, setFilterMode] = useState<'all' | 'pending' | 'skipped'>('all');

  const filteredEntries = imageEntries.filter(entry => {
    if (filterMode === 'pending') return entry.status === 'pending' || entry.status === 'processing';
    if (filterMode === 'skipped') return entry.skipped;
    return true;
  });

  if (!file) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <RefreshCw className="w-16 h-16 mx-auto mb-4 opacity-20" />
          <p>{text.noFile}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="p-4 border-b bg-card space-y-4">
        {/* 步骤 1: 文件选择 */}
        <div>
          <Label className="text-sm text-muted-foreground mb-2 block">{text.step1}</Label>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="mb-1">{file.name}</h2>
              <p className="text-sm text-muted-foreground">
                {text.total} {file.imageCount} {text.images}
              </p>
            </div>
          </div>
        </div>
        
        <Separator />
        
        {/* 步骤 2: 处理控制台 */}
        <div className="space-y-3">
          <Label className="text-sm text-muted-foreground">{text.step2}</Label>
          
          {/* 预设选择器 */}
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">{text.aiModelPreset}</Label>
              <Select value={selectedAIPresetId} onValueChange={onSelectAIPreset}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {presets.ai.map(preset => (
                    <SelectItem key={preset.id} value={preset.id}>
                      {preset.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-1.5">
              <Label className="text-xs">{text.namingRulesPreset}</Label>
              <Select value={selectedNamingPresetId} onValueChange={onSelectNamingPreset}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {presets.naming.map(preset => (
                    <SelectItem key={preset.id} value={preset.id}>
                      {preset.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-1.5">
              <Label className="text-xs">{text.runtimeOptionsPreset}</Label>
              <Select value={selectedRuntimePresetId} onValueChange={onSelectRuntimePreset}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {presets.runtime.map(preset => (
                    <SelectItem key={preset.id} value={preset.id}>
                      {preset.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          
          {/* 操作按钮 */}
          <div className="flex items-center gap-2">
            <Button
              onClick={onBatchPreview}
              disabled={isProcessing}
              className="flex-1"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isProcessing ? 'animate-spin' : ''}`} />
              {text.batchPreview}
            </Button>
            <Button
              variant="outline"
              onClick={onOpenSettings}
            >
              <Settings className="w-4 h-4 mr-2" />
              {text.openSettings}
            </Button>
          </div>
        </div>
        
        <Separator />
        
        {/* 辅助功能按钮 */}
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

      <ScrollArea className="flex-1">
        <Table>
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
                  <div className="w-16 h-16 bg-muted rounded flex items-center justify-center">
                    <span className="text-xs text-muted-foreground">IMG</span>
                  </div>
                </TableCell>
                <TableCell className="text-sm">{entry.originalPath}</TableCell>
                <TableCell>
                  <Input
                    value={entry.intent}
                    onChange={(e) => onUpdateIntent(entry.id, e.target.value)}
                    placeholder="AI intent..."
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
