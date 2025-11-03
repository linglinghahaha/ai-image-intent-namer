import { Settings, Globe, HelpCircle } from 'lucide-react';
import { Button } from './ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Badge } from './ui/badge';
import type { AIPreset, NamingPreset, RuntimePreset } from '../types/presets';

interface AppBarProps {
  language: 'zh' | 'en';
  onLanguageChange: (lang: 'zh' | 'en') => void;
  onOpenSettings: () => void;
  isProcessing: boolean;
  currentFile?: string;
  
  // 预设相关
  aiPresets: AIPreset[];
  namingPresets: NamingPreset[];
  runtimePresets: RuntimePreset[];
  selectedAIPresetId: string;
  selectedNamingPresetId: string;
  selectedRuntimePresetId: string;
  onAIPresetChange: (id: string) => void;
  onNamingPresetChange: (id: string) => void;
  onRuntimePresetChange: (id: string) => void;
}

const t = {
  zh: {
    title: 'AI 图片意图批量命名',
    mode: {
      preview: '预览模式',
      write: '写入模式',
    },
    aiModel: 'AI 模型',
    namingRules: '命名规则',
    runtimeOptions: '运行选项',
    settings: '预设管理',
    help: '帮助',
    shortcuts: '快捷键',
    logs: '日志',
    version: '版本',
    processing: '处理中',
  },
  en: {
    title: 'AI Image Intent Batch Naming',
    mode: {
      preview: 'Preview Mode',
      write: 'Write Mode',
    },
    aiModel: 'AI Model',
    namingRules: 'Naming Rules',
    runtimeOptions: 'Runtime',
    settings: 'Preset Manager',
    help: 'Help',
    shortcuts: 'Shortcuts',
    logs: 'Logs',
    version: 'Version',
    processing: 'Processing',
  },
};

export function AppBar({
  language,
  onLanguageChange,
  onOpenSettings,
  isProcessing,
  currentFile,
  aiPresets,
  namingPresets,
  runtimePresets,
  selectedAIPresetId,
  selectedNamingPresetId,
  selectedRuntimePresetId,
  onAIPresetChange,
  onNamingPresetChange,
  onRuntimePresetChange,
}: AppBarProps) {
  const text = t[language];

  return (
    <div className="h-14 border-b bg-card flex items-center justify-between px-4 shrink-0 gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <h1 className="text-primary shrink-0">{text.title}</h1>
        {currentFile && (
          <Badge variant="outline" className="shrink-0">{text.mode.preview}</Badge>
        )}
        {isProcessing && (
          <Badge variant="secondary" className="shrink-0">{text.processing}</Badge>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {/* 三个预设选择器 */}
        <Select value={selectedAIPresetId} onValueChange={onAIPresetChange}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder={text.aiModel} />
          </SelectTrigger>
          <SelectContent>
            {aiPresets.map(preset => (
              <SelectItem key={preset.id} value={preset.id}>
                {preset.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={selectedNamingPresetId} onValueChange={onNamingPresetChange}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder={text.namingRules} />
          </SelectTrigger>
          <SelectContent>
            {namingPresets.map(preset => (
              <SelectItem key={preset.id} value={preset.id}>
                {preset.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={selectedRuntimePresetId} onValueChange={onRuntimePresetChange}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder={text.runtimeOptions} />
          </SelectTrigger>
          <SelectContent>
            {runtimePresets.map(preset => (
              <SelectItem key={preset.id} value={preset.id}>
                {preset.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* 预设管理按钮 */}
        <Button variant="outline" size="sm" onClick={onOpenSettings}>
          <Settings className="w-4 h-4 mr-2" />
          {text.settings}
        </Button>

        {/* 语言切换 */}
        <Select value={language} onValueChange={(val) => onLanguageChange(val as 'zh' | 'en')}>
          <SelectTrigger className="w-28">
            <Globe className="w-4 h-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="zh">中文</SelectItem>
            <SelectItem value="en">English</SelectItem>
          </SelectContent>
        </Select>

        {/* 帮助菜单 */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground h-9 px-3">
              <HelpCircle className="w-4 h-4 mr-2" />
              {text.help}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>{text.shortcuts}</DropdownMenuItem>
            <DropdownMenuItem>{text.logs}</DropdownMenuItem>
            <DropdownMenuItem>{text.version} 2.0.0</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
