import { useState } from 'react';
import { X, Save, Copy, Trash2, Plus, Settings as SettingsIcon, FileText, Zap, Upload, Download, RotateCcw, CheckCircle, XCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Switch } from './ui/switch';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from './ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';
import { usePresets } from '../hooks/usePresets';
import type { AIPreset, NamingPreset, RuntimePreset, APIConfig } from '../types/presets';
import { toast } from 'sonner@2.0.3';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  language: 'zh' | 'en';
}

const t = {
  zh: {
    title: '预设管理',
    close: '关闭',
    
    // 导航
    aiModel: 'AI 模型',
    namingRules: '命名规则',
    runtimeOptions: '运行选项',
    
    // 通用操作
    selectPreset: '选择预设',
    saveAs: '另存为...',
    duplicate: '复制',
    delete: '删除',
    reset: '重置全部',
    import: '导入',
    export: '导出',
    save: '保存',
    cancel: '取消',
    
    // AI模型设置
    aiPresetName: '预设名称',
    mainApi: '主 API',
    translationApi: '翻译 API',
    summaryApi: '摘要 API',
    baseUrl: 'Base URL',
    apiKey: 'API Key',
    model: '模型',
    temperature: 'Temperature',
    maxTokens: '最大令牌数',
    systemPrompt: '系统提示词',
    testConnection: '测试连接',
    testing: '测试中...',
    connectionSuccess: '连接成功',
    connectionFailed: '连接失败',
    
    // 命名规则设置
    namingPresetName: '预设名称',
    template: '命名模板',
    templatePlaceholder: '例如: {title}_{seq}_{intent}',
    availablePlaceholders: '可用占位符',
    templatePresets: '模板预设',
    strategy: '命名策略',
    strategyContext: '基于上下文',
    strategyVision: '基于视觉',
    strategyHybrid: '混合模式',
    seqWidth: '序号宽度',
    separator: '分隔符',
    caseSensitive: '区分大小写',
    removeSpecialChars: '移除特殊字符',
    maxLength: '最大长度',
    preview: '预览',
    insertPlaceholder: '点击插入',
    
    // 运行选项设置
    runtimePresetName: '预设名称',
    backup: '备份原文件',
    vision: '启用视觉分析',
    attachDir: 'Attachments 目录',
    concurrency: '并发数',
    retryCount: '重试次数',
    timeout: '超时时间（秒）',
    logLevel: '日志级别',
    autoSave: '自动保存',
    
    // 对话框
    saveAsTitle: '另存为新预设',
    saveAsDescription: '请输入新预设的名称',
    presetName: '预设名称',
    
    deleteTitle: '确认删除',
    deleteDescription: '确定要删除此预设吗？此操作不可撤销。',
    
    resetTitle: '确认重置',
    resetDescription: '确定要重置所有预设到默认值吗？此操作不可撤销。',
    
    importTitle: '导入预设',
    importDescription: '粘贴预设JSON数据',
    
    // 提示信息
    saved: '预设已保存',
    deleted: '预设已删除',
    duplicated: '预设已复制',
    resetSuccess: '所有预设已重置',
    importSuccess: '预设已导入',
    exportSuccess: '预设已复制到剪贴板',
    invalidJson: '无效的JSON格式',
  },
  en: {
    title: 'Preset Manager',
    close: 'Close',
    
    // Navigation
    aiModel: 'AI Model',
    namingRules: 'Naming Rules',
    runtimeOptions: 'Runtime Options',
    
    // Common operations
    selectPreset: 'Select Preset',
    saveAs: 'Save As...',
    duplicate: 'Duplicate',
    delete: 'Delete',
    reset: 'Reset All',
    import: 'Import',
    export: 'Export',
    save: 'Save',
    cancel: 'Cancel',
    
    // AI model settings
    aiPresetName: 'Preset Name',
    mainApi: 'Main API',
    translationApi: 'Translation API',
    summaryApi: 'Summary API',
    baseUrl: 'Base URL',
    apiKey: 'API Key',
    model: 'Model',
    temperature: 'Temperature',
    maxTokens: 'Max Tokens',
    systemPrompt: 'System Prompt',
    testConnection: 'Test Connection',
    testing: 'Testing...',
    connectionSuccess: 'Connection successful',
    connectionFailed: 'Connection failed',
    
    // Naming rules settings
    namingPresetName: 'Preset Name',
    template: 'Template',
    templatePlaceholder: 'e.g., {title}_{seq}_{intent}',
    availablePlaceholders: 'Available Placeholders',
    templatePresets: 'Template Presets',
    strategy: 'Strategy',
    strategyContext: 'Context-based',
    strategyVision: 'Vision-based',
    strategyHybrid: 'Hybrid',
    seqWidth: 'Sequence Width',
    separator: 'Separator',
    caseSensitive: 'Case Sensitive',
    removeSpecialChars: 'Remove Special Chars',
    maxLength: 'Max Length',
    preview: 'Preview',
    insertPlaceholder: 'Click to insert',
    
    // Runtime options settings
    runtimePresetName: 'Preset Name',
    backup: 'Backup Files',
    vision: 'Enable Vision',
    attachDir: 'Attachments Directory',
    concurrency: 'Concurrency',
    retryCount: 'Retry Count',
    timeout: 'Timeout (seconds)',
    logLevel: 'Log Level',
    autoSave: 'Auto Save',
    
    // Dialogs
    saveAsTitle: 'Save as New Preset',
    saveAsDescription: 'Enter a name for the new preset',
    presetName: 'Preset Name',
    
    deleteTitle: 'Confirm Delete',
    deleteDescription: 'Are you sure you want to delete this preset? This action cannot be undone.',
    
    resetTitle: 'Confirm Reset',
    resetDescription: 'Are you sure you want to reset all presets to default? This action cannot be undone.',
    
    importTitle: 'Import Presets',
    importDescription: 'Paste preset JSON data',
    
    // Messages
    saved: 'Preset saved',
    deleted: 'Preset deleted',
    duplicated: 'Preset duplicated',
    resetSuccess: 'All presets reset',
    importSuccess: 'Presets imported',
    exportSuccess: 'Presets copied to clipboard',
    invalidJson: 'Invalid JSON format',
  },
};

// 占位符定义
const placeholders = [
  { key: '{intent}', descZh: 'AI 生成的意图', descEn: 'AI generated intent' },
  { key: '{seq}', descZh: '序号', descEn: 'Sequence number' },
  { key: '{title}', descZh: '文档标题', descEn: 'Document title' },
  { key: '{date}', descZh: '日期 (YYYY-MM-DD)', descEn: 'Date (YYYY-MM-DD)' },
  { key: '{time}', descZh: '时间 (HH-MM-SS)', descEn: 'Time (HH-MM-SS)' },
  { key: '{context}', descZh: '上下文摘要', descEn: 'Context summary' },
  { key: '{file}', descZh: '源文件名', descEn: 'Source file name' },
  { key: '{original}', descZh: '原始图片名', descEn: 'Original image name' },
];

// 模板预设
const templatePresets = [
  { nameZh: '意图_序号', nameEn: 'Intent + Seq', template: '{intent}_{seq}', exampleZh: '场景描述_001.png', exampleEn: 'scene_description_001.png' },
  { nameZh: '标题_序号_意图', nameEn: 'Title + Seq + Intent', template: '{title}_{seq}_{intent}', exampleZh: '文档_001_场景描述.png', exampleEn: 'document_001_scene_description.png' },
  { nameZh: '日期_意图', nameEn: 'Date + Intent', template: '{date}_{intent}', exampleZh: '2025-11-02_场景描述.png', exampleEn: '2025-11-02_scene_description.png' },
  { nameZh: '上下文_序号', nameEn: 'Context + Seq', template: '{context}_{seq}', exampleZh: '第一章介绍_001.png', exampleEn: 'chapter1_intro_001.png' },
];

type Tab = 'ai' | 'naming' | 'runtime';

export function SettingsPanel({ isOpen, onClose, language }: SettingsPanelProps) {
  const text = t[language];
  const {
    presets,
    addAIPreset,
    updateAIPreset,
    deleteAIPreset,
    duplicateAIPreset,
    addNamingPreset,
    updateNamingPreset,
    deleteNamingPreset,
    duplicateNamingPreset,
    addRuntimePreset,
    updateRuntimePreset,
    deleteRuntimePreset,
    duplicateRuntimePreset,
    resetAllPresets,
    importPresets,
    exportPresets,
  } = usePresets();

  const [activeTab, setActiveTab] = useState<Tab>('ai');
  
  // 当前选中的预设ID - 确保有默认值
  const [selectedAIPresetId, setSelectedAIPresetId] = useState(() => {
    return presets.ai.length > 0 ? presets.ai[0].id : '';
  });
  const [selectedNamingPresetId, setSelectedNamingPresetId] = useState(() => {
    return presets.naming.length > 0 ? presets.naming[0].id : '';
  });
  const [selectedRuntimePresetId, setSelectedRuntimePresetId] = useState(() => {
    return presets.runtime.length > 0 ? presets.runtime[0].id : '';
  });
  
  // 对话框状态
  const [saveAsDialogOpen, setSaveAsDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');
  const [importJson, setImportJson] = useState('');
  
  // 编辑中的预设数据 - 确保初始化正确
  const [editingAIPreset, setEditingAIPreset] = useState<AIPreset | null>(() => {
    const preset = presets.ai.find(p => p.id === (presets.ai[0]?.id || ''));
    return preset || null;
  });
  const [editingNamingPreset, setEditingNamingPreset] = useState<NamingPreset | null>(() => {
    const preset = presets.naming.find(p => p.id === (presets.naming[0]?.id || ''));
    return preset || null;
  });
  const [editingRuntimePreset, setEditingRuntimePreset] = useState<RuntimePreset | null>(() => {
    const preset = presets.runtime.find(p => p.id === (presets.runtime[0]?.id || ''));
    return preset || null;
  });

  // 当选择改变时更新编辑中的数据
  const handleAIPresetSelect = (id: string) => {
    setSelectedAIPresetId(id);
    const preset = presets.ai.find(p => p.id === id);
    if (preset) setEditingAIPreset(preset);
  };

  const handleNamingPresetSelect = (id: string) => {
    setSelectedNamingPresetId(id);
    const preset = presets.naming.find(p => p.id === id);
    if (preset) setEditingNamingPreset(preset);
  };

  const handleRuntimePresetSelect = (id: string) => {
    setSelectedRuntimePresetId(id);
    const preset = presets.runtime.find(p => p.id === id);
    if (preset) setEditingRuntimePreset(preset);
  };

  // 处理另存为
  const handleSaveAs = () => {
    if (!newPresetName.trim()) return;
    
    if (activeTab === 'ai' && editingAIPreset) {
      const { id, ...preset } = editingAIPreset;
      const newPreset = addAIPreset({ ...preset, name: newPresetName });
      setSelectedAIPresetId(newPreset.id);
      setEditingAIPreset(newPreset);
    } else if (activeTab === 'naming' && editingNamingPreset) {
      const { id, ...preset } = editingNamingPreset;
      const newPreset = addNamingPreset({ ...preset, name: newPresetName });
      setSelectedNamingPresetId(newPreset.id);
      setEditingNamingPreset(newPreset);
    } else if (activeTab === 'runtime' && editingRuntimePreset) {
      const { id, ...preset } = editingRuntimePreset;
      const newPreset = addRuntimePreset({ ...preset, name: newPresetName });
      setSelectedRuntimePresetId(newPreset.id);
      setEditingRuntimePreset(newPreset);
    }
    
    setSaveAsDialogOpen(false);
    setNewPresetName('');
    toast.success(text.saved);
  };

  // 处理删除
  const handleDelete = () => {
    if (activeTab === 'ai' && selectedAIPresetId) {
      deleteAIPreset(selectedAIPresetId);
      const remaining = presets.ai.filter(p => p.id !== selectedAIPresetId);
      if (remaining.length > 0) {
        setSelectedAIPresetId(remaining[0].id);
        setEditingAIPreset(remaining[0]);
      }
    } else if (activeTab === 'naming' && selectedNamingPresetId) {
      deleteNamingPreset(selectedNamingPresetId);
      const remaining = presets.naming.filter(p => p.id !== selectedNamingPresetId);
      if (remaining.length > 0) {
        setSelectedNamingPresetId(remaining[0].id);
        setEditingNamingPreset(remaining[0]);
      }
    } else if (activeTab === 'runtime' && selectedRuntimePresetId) {
      deleteRuntimePreset(selectedRuntimePresetId);
      const remaining = presets.runtime.filter(p => p.id !== selectedRuntimePresetId);
      if (remaining.length > 0) {
        setSelectedRuntimePresetId(remaining[0].id);
        setEditingRuntimePreset(remaining[0]);
      }
    }
    
    setDeleteDialogOpen(false);
    toast.success(text.deleted);
  };

  // 处理复制
  const handleDuplicate = () => {
    if (activeTab === 'ai' && selectedAIPresetId) {
      const newPreset = duplicateAIPreset(selectedAIPresetId);
      if (newPreset) {
        setSelectedAIPresetId(newPreset.id);
        setEditingAIPreset(newPreset);
      }
    } else if (activeTab === 'naming' && selectedNamingPresetId) {
      const newPreset = duplicateNamingPreset(selectedNamingPresetId);
      if (newPreset) {
        setSelectedNamingPresetId(newPreset.id);
        setEditingNamingPreset(newPreset);
      }
    } else if (activeTab === 'runtime' && selectedRuntimePresetId) {
      const newPreset = duplicateRuntimePreset(selectedRuntimePresetId);
      if (newPreset) {
        setSelectedRuntimePresetId(newPreset.id);
        setEditingRuntimePreset(newPreset);
      }
    }
    
    toast.success(text.duplicated);
  };

  // 处理导出
  const handleExport = () => {
    const json = exportPresets();
    navigator.clipboard.writeText(json);
    toast.success(text.exportSuccess);
  };

  // 处理导入
  const handleImport = () => {
    try {
      const parsed = JSON.parse(importJson);
      importPresets(parsed);
      setImportDialogOpen(false);
      setImportJson('');
      toast.success(text.importSuccess);
      
      // 重新选择第一个预设
      if (presets.ai.length > 0) {
        setSelectedAIPresetId(presets.ai[0].id);
        setEditingAIPreset(presets.ai[0]);
      }
      if (presets.naming.length > 0) {
        setSelectedNamingPresetId(presets.naming[0].id);
        setEditingNamingPreset(presets.naming[0]);
      }
      if (presets.runtime.length > 0) {
        setSelectedRuntimePresetId(presets.runtime[0].id);
        setEditingRuntimePreset(presets.runtime[0]);
      }
    } catch (error) {
      toast.error(text.invalidJson);
    }
  };

  // 处理重置
  const handleReset = () => {
    resetAllPresets();
    setResetDialogOpen(false);
    
    // 重新选择第一个预设
    if (presets.ai.length > 0) {
      setSelectedAIPresetId(presets.ai[0].id);
      setEditingAIPreset(presets.ai[0]);
    }
    if (presets.naming.length > 0) {
      setSelectedNamingPresetId(presets.naming[0].id);
      setEditingNamingPreset(presets.naming[0]);
    }
    if (presets.runtime.length > 0) {
      setSelectedRuntimePresetId(presets.runtime[0].id);
      setEditingRuntimePreset(presets.runtime[0]);
    }
    
    toast.success(text.resetSuccess);
  };

  // 保存当前编辑
  const handleSaveCurrent = () => {
    if (activeTab === 'ai' && editingAIPreset) {
      updateAIPreset(editingAIPreset.id, editingAIPreset);
    } else if (activeTab === 'naming' && editingNamingPreset) {
      updateNamingPreset(editingNamingPreset.id, editingNamingPreset);
    } else if (activeTab === 'runtime' && editingRuntimePreset) {
      updateRuntimePreset(editingRuntimePreset.id, editingRuntimePreset);
    }
    toast.success(text.saved);
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-full max-w-5xl bg-background border-l shadow-lg z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl">{text.title}</h2>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="w-4 h-4 mr-2" />
              {text.export}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setImportDialogOpen(true)}>
              <Upload className="w-4 h-4 mr-2" />
              {text.import}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setResetDialogOpen(true)}>
              <RotateCcw className="w-4 h-4 mr-2" />
              {text.reset}
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs Navigation */}
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as Tab)} className="flex-1 flex flex-col">
            <div className="border-b px-6">
              <TabsList className="w-full justify-start">
                <TabsTrigger value="ai" className="flex items-center gap-2">
                  <SettingsIcon className="w-4 h-4" />
                  {text.aiModel}
                </TabsTrigger>
                <TabsTrigger value="naming" className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  {text.namingRules}
                </TabsTrigger>
                <TabsTrigger value="runtime" className="flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  {text.runtimeOptions}
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Preset Selector and Actions */}
            <div className="px-6 py-4 border-b">
              <div className="flex gap-2">
                {activeTab === 'ai' && (
                  <Select value={selectedAIPresetId} onValueChange={handleAIPresetSelect}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder={text.selectPreset} />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.ai.map(preset => (
                        <SelectItem key={preset.id} value={preset.id}>
                          {preset.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                {activeTab === 'naming' && (
                  <Select value={selectedNamingPresetId} onValueChange={handleNamingPresetSelect}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder={text.selectPreset} />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.naming.map(preset => (
                        <SelectItem key={preset.id} value={preset.id}>
                          {preset.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                {activeTab === 'runtime' && (
                  <Select value={selectedRuntimePresetId} onValueChange={handleRuntimePresetSelect}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder={text.selectPreset} />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.runtime.map(preset => (
                        <SelectItem key={preset.id} value={preset.id}>
                          {preset.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                
                <Button variant="default" size="sm" onClick={handleSaveCurrent}>
                  <Save className="w-4 h-4 mr-2" />
                  {text.save}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setSaveAsDialogOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  {text.saveAs}
                </Button>
                <Button variant="outline" size="sm" onClick={handleDuplicate}>
                  <Copy className="w-4 h-4 mr-2" />
                  {text.duplicate}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setDeleteDialogOpen(true)}>
                  <Trash2 className="w-4 h-4 mr-2" />
                  {text.delete}
                </Button>
              </div>
            </div>

            {/* Tab Content */}
            <TabsContent value="ai" className="flex-1 m-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-6">
                  {editingAIPreset && (
                    <AIPresetForm
                      preset={editingAIPreset}
                      onChange={setEditingAIPreset}
                      language={language}
                    />
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="naming" className="flex-1 m-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-6">
                  {editingNamingPreset && (
                    <NamingPresetForm
                      preset={editingNamingPreset}
                      onChange={setEditingNamingPreset}
                      language={language}
                    />
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="runtime" className="flex-1 m-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-6">
                  {editingRuntimePreset && (
                    <RuntimePresetForm
                      preset={editingRuntimePreset}
                      onChange={setEditingRuntimePreset}
                      language={language}
                    />
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Dialogs */}
      <Dialog open={saveAsDialogOpen} onOpenChange={setSaveAsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{text.saveAsTitle}</DialogTitle>
            <DialogDescription>{text.saveAsDescription}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{text.presetName}</Label>
              <Input
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
                placeholder={text.presetName}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveAsDialogOpen(false)}>
              {text.cancel}
            </Button>
            <Button onClick={handleSaveAs}>
              {text.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{text.deleteTitle}</AlertDialogTitle>
            <AlertDialogDescription>{text.deleteDescription}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{text.cancel}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>{text.delete}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{text.resetTitle}</AlertDialogTitle>
            <AlertDialogDescription>{text.resetDescription}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{text.cancel}</AlertDialogCancel>
            <AlertDialogAction onClick={handleReset}>{text.reset}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{text.importTitle}</DialogTitle>
            <DialogDescription>{text.importDescription}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Textarea
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              placeholder='{"ai": [...], "naming": [...], "runtime": [...]}'
              className="font-mono text-sm min-h-[300px]"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setImportDialogOpen(false)}>
              {text.cancel}
            </Button>
            <Button onClick={handleImport}>
              {text.import}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// AI预设表单 - 整合了API配置中心的三个API
function AIPresetForm({ preset, onChange, language }: {
  preset: AIPreset;
  onChange: (preset: AIPreset) => void;
  language: 'zh' | 'en';
}) {
  const text = t[language];
  const [testingApi, setTestingApi] = useState<'main' | 'translation' | 'summary' | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<{[key: string]: 'idle' | 'success' | 'error'}>({});
  
  // 确保preset有正确的结构
  if (!preset || !preset.mainApi || !preset.translationApi || !preset.summaryApi) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        {language === 'zh' ? '预设数据无效，请重置预设。' : 'Invalid preset data, please reset presets.'}
      </div>
    );
  }
  
  const handleTestConnection = async (apiType: 'main' | 'translation' | 'summary') => {
    setTestingApi(apiType);
    
    // 模拟测试连接
    setTimeout(() => {
      const success = Math.random() > 0.3; // 70% 成功率
      setConnectionStatus(prev => ({ ...prev, [apiType]: success ? 'success' : 'error' }));
      setTestingApi(null);
      
      if (success) {
        toast.success(text.connectionSuccess);
      } else {
        toast.error(text.connectionFailed);
      }
    }, 2000);
  };

  const updateAPIConfig = (apiType: 'mainApi' | 'translationApi' | 'summaryApi', updates: Partial<APIConfig>) => {
    onChange({
      ...preset,
      [apiType]: { ...preset[apiType], ...updates }
    });
  };
  
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>{text.aiPresetName}</Label>
        <Input
          value={preset.name}
          onChange={(e) => onChange({ ...preset, name: e.target.value })}
        />
      </div>
      
      <Separator />

      {/* 主API、翻译API、摘要API 三个Tab */}
      <Tabs defaultValue="main" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="main">{text.mainApi}</TabsTrigger>
          <TabsTrigger value="translation">{text.translationApi}</TabsTrigger>
          <TabsTrigger value="summary">{text.summaryApi}</TabsTrigger>
        </TabsList>

        {/* 主API */}
        <TabsContent value="main" className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label>{text.baseUrl}</Label>
            <Input
              value={preset.mainApi.baseUrl}
              onChange={(e) => updateAPIConfig('mainApi', { baseUrl: e.target.value })}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.apiKey}</Label>
            <Input
              type="password"
              value={preset.mainApi.apiKey}
              onChange={(e) => updateAPIConfig('mainApi', { apiKey: e.target.value })}
              placeholder="sk-..."
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.model}</Label>
            <Input
              value={preset.mainApi.model}
              onChange={(e) => updateAPIConfig('mainApi', { model: e.target.value })}
              placeholder="gpt-4"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.systemPrompt}</Label>
            <Textarea
              value={preset.mainApi.systemPrompt || ''}
              onChange={(e) => updateAPIConfig('mainApi', { systemPrompt: e.target.value })}
              placeholder="You are a helpful assistant..."
              rows={6}
            />
          </div>
          
          <Button 
            onClick={() => handleTestConnection('main')} 
            disabled={testingApi === 'main'}
            variant="outline"
            className="w-full"
          >
            {testingApi === 'main' ? (
              <>
                <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                {text.testing}
              </>
            ) : connectionStatus.main === 'success' ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                {text.connectionSuccess}
              </>
            ) : connectionStatus.main === 'error' ? (
              <>
                <XCircle className="w-4 h-4 mr-2 text-red-500" />
                {text.connectionFailed}
              </>
            ) : (
              <>
                <SettingsIcon className="w-4 h-4 mr-2" />
                {text.testConnection}
              </>
            )}
          </Button>
        </TabsContent>

        {/* 翻译API */}
        <TabsContent value="translation" className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label>{text.baseUrl}</Label>
            <Input
              value={preset.translationApi.baseUrl}
              onChange={(e) => updateAPIConfig('translationApi', { baseUrl: e.target.value })}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.apiKey}</Label>
            <Input
              type="password"
              value={preset.translationApi.apiKey}
              onChange={(e) => updateAPIConfig('translationApi', { apiKey: e.target.value })}
              placeholder="sk-..."
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.model}</Label>
            <Input
              value={preset.translationApi.model}
              onChange={(e) => updateAPIConfig('translationApi', { model: e.target.value })}
              placeholder="gpt-3.5-turbo"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.systemPrompt}</Label>
            <Textarea
              value={preset.translationApi.systemPrompt || ''}
              onChange={(e) => updateAPIConfig('translationApi', { systemPrompt: e.target.value })}
              placeholder="Translate the following text to {target_language}."
              rows={6}
            />
          </div>
          
          <Button 
            onClick={() => handleTestConnection('translation')} 
            disabled={testingApi === 'translation'}
            variant="outline"
            className="w-full"
          >
            {testingApi === 'translation' ? (
              <>
                <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                {text.testing}
              </>
            ) : connectionStatus.translation === 'success' ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                {text.connectionSuccess}
              </>
            ) : connectionStatus.translation === 'error' ? (
              <>
                <XCircle className="w-4 h-4 mr-2 text-red-500" />
                {text.connectionFailed}
              </>
            ) : (
              <>
                <SettingsIcon className="w-4 h-4 mr-2" />
                {text.testConnection}
              </>
            )}
          </Button>
        </TabsContent>

        {/* 摘要API */}
        <TabsContent value="summary" className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label>{text.baseUrl}</Label>
            <Input
              value={preset.summaryApi.baseUrl}
              onChange={(e) => updateAPIConfig('summaryApi', { baseUrl: e.target.value })}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.apiKey}</Label>
            <Input
              type="password"
              value={preset.summaryApi.apiKey}
              onChange={(e) => updateAPIConfig('summaryApi', { apiKey: e.target.value })}
              placeholder="sk-..."
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.model}</Label>
            <Input
              value={preset.summaryApi.model}
              onChange={(e) => updateAPIConfig('summaryApi', { model: e.target.value })}
              placeholder="gpt-3.5-turbo"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.systemPrompt}</Label>
            <Textarea
              value={preset.summaryApi.systemPrompt || ''}
              onChange={(e) => updateAPIConfig('summaryApi', { systemPrompt: e.target.value })}
              placeholder="Summarize the following text concisely."
              rows={6}
            />
          </div>
          
          <Button 
            onClick={() => handleTestConnection('summary')} 
            disabled={testingApi === 'summary'}
            variant="outline"
            className="w-full"
          >
            {testingApi === 'summary' ? (
              <>
                <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                {text.testing}
              </>
            ) : connectionStatus.summary === 'success' ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                {text.connectionSuccess}
              </>
            ) : connectionStatus.summary === 'error' ? (
              <>
                <XCircle className="w-4 h-4 mr-2 text-red-500" />
                {text.connectionFailed}
              </>
            ) : (
              <>
                <SettingsIcon className="w-4 h-4 mr-2" />
                {text.testConnection}
              </>
            )}
          </Button>
        </TabsContent>
      </Tabs>

      <Separator />
      
      {/* 通用参数 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{text.temperature}</Label>
          <Input
            type="number"
            step="0.1"
            min="0"
            max="2"
            value={preset.temperature || 0.7}
            onChange={(e) => onChange({ ...preset, temperature: parseFloat(e.target.value) })}
          />
        </div>
        
        <div className="space-y-2">
          <Label>{text.maxTokens}</Label>
          <Input
            type="number"
            value={preset.maxTokens || 2000}
            onChange={(e) => onChange({ ...preset, maxTokens: parseInt(e.target.value) })}
          />
        </div>
      </div>
    </div>
  );
}

// 命名规则预设表单 - 整合了模板助手
function NamingPresetForm({ preset, onChange, language }: {
  preset: NamingPreset;
  onChange: (preset: NamingPreset) => void;
  language: 'zh' | 'en';
}) {
  const text = t[language];
  
  const handleInsertPlaceholder = (placeholder: string) => {
    const currentTemplate = preset.template || '';
    onChange({ ...preset, template: currentTemplate + placeholder });
  };
  
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>{text.namingPresetName}</Label>
        <Input
          value={preset.name}
          onChange={(e) => onChange({ ...preset, name: e.target.value })}
        />
      </div>
      
      <Separator />
      
      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：模板编辑 */}
        <div className="col-span-2 space-y-4">
          <div className="space-y-2">
            <Label>{text.template}</Label>
            <Textarea
              value={preset.template}
              onChange={(e) => onChange({ ...preset, template: e.target.value })}
              placeholder={text.templatePlaceholder}
              rows={3}
            />
          </div>
          
          {/* 占位符列表 */}
          <div>
            <Label className="mb-2 block">{text.availablePlaceholders}</Label>
            <p className="text-xs text-muted-foreground mb-2">{text.insertPlaceholder}</p>
            <div className="grid grid-cols-2 gap-2">
              {placeholders.map((ph) => (
                <Card 
                  key={ph.key} 
                  className="p-2 hover:bg-accent/50 cursor-pointer transition-colors" 
                  onClick={() => handleInsertPlaceholder(ph.key)}
                >
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <code className="text-xs bg-muted px-2 py-1 rounded block truncate">
                        {ph.key}
                      </code>
                      <p className="text-xs text-muted-foreground mt-1">
                        {language === 'zh' ? ph.descZh : ph.descEn}
                      </p>
                    </div>
                    <Plus className="w-3 h-3 shrink-0 mt-1" />
                  </div>
                </Card>
              ))}
            </div>
          </div>
          
          {/* 其他设置 */}
          <div className="space-y-2">
            <Label>{text.strategy}</Label>
            <Select 
              value={preset.strategy} 
              onValueChange={(value: any) => onChange({ ...preset, strategy: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="context">{text.strategyContext}</SelectItem>
                <SelectItem value="vision">{text.strategyVision}</SelectItem>
                <SelectItem value="hybrid">{text.strategyHybrid}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{text.seqWidth}</Label>
              <Input
                type="number"
                min="0"
                max="10"
                value={preset.seqWidth}
                onChange={(e) => onChange({ ...preset, seqWidth: parseInt(e.target.value) })}
              />
            </div>
            
            <div className="space-y-2">
              <Label>{text.separator}</Label>
              <Input
                value={preset.separator}
                onChange={(e) => onChange({ ...preset, separator: e.target.value })}
                maxLength={3}
              />
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>{text.caseSensitive}</Label>
              <Switch
                checked={preset.caseSensitive}
                onCheckedChange={(checked) => onChange({ ...preset, caseSensitive: checked })}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <Label>{text.removeSpecialChars}</Label>
              <Switch
                checked={preset.removeSpecialChars}
                onCheckedChange={(checked) => onChange({ ...preset, removeSpecialChars: checked })}
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label>{text.maxLength}</Label>
            <Input
              type="number"
              min="0"
              value={preset.maxLength || ''}
              onChange={(e) => onChange({ ...preset, maxLength: e.target.value ? parseInt(e.target.value) : undefined })}
              placeholder="100"
            />
          </div>
        </div>
        
        {/* 右侧：模板预设 */}
        <div className="space-y-4">
          <div>
            <Label className="mb-2 block">{text.templatePresets}</Label>
            <ScrollArea className="h-[600px]">
              <div className="space-y-2 pr-4">
                {templatePresets.map((tp, idx) => (
                  <Card 
                    key={idx} 
                    className="p-3 hover:bg-accent/50 cursor-pointer transition-colors"
                    onClick={() => onChange({ ...preset, template: tp.template })}
                  >
                    <h4 className="text-sm mb-2">{language === 'zh' ? tp.nameZh : tp.nameEn}</h4>
                    <Badge variant="secondary" className="text-xs mb-2 w-full justify-start">
                      {tp.template}
                    </Badge>
                    <p className="text-xs text-muted-foreground">
                      {text.preview}: {language === 'zh' ? tp.exampleZh : tp.exampleEn}
                    </p>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </div>
  );
}

// 运行选项预设表单
function RuntimePresetForm({ preset, onChange, language }: {
  preset: RuntimePreset;
  onChange: (preset: RuntimePreset) => void;
  language: 'zh' | 'en';
}) {
  const text = t[language];
  
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>{text.runtimePresetName}</Label>
        <Input
          value={preset.name}
          onChange={(e) => onChange({ ...preset, name: e.target.value })}
        />
      </div>
      
      <Separator />
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label>{text.backup}</Label>
          <Switch
            checked={preset.backup}
            onCheckedChange={(checked) => onChange({ ...preset, backup: checked })}
          />
        </div>
        
        <div className="flex items-center justify-between">
          <Label>{text.vision}</Label>
          <Switch
            checked={preset.vision}
            onCheckedChange={(checked) => onChange({ ...preset, vision: checked })}
          />
        </div>
        
        <div className="flex items-center justify-between">
          <Label>{text.autoSave}</Label>
          <Switch
            checked={preset.autoSave}
            onCheckedChange={(checked) => onChange({ ...preset, autoSave: checked })}
          />
        </div>
      </div>
      
      <Separator />
      
      <div className="space-y-2">
        <Label>{text.attachDir}</Label>
        <Input
          value={preset.attachDir}
          onChange={(e) => onChange({ ...preset, attachDir: e.target.value })}
          placeholder="./attachments"
        />
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{text.concurrency}</Label>
          <Input
            type="number"
            min="1"
            max="10"
            value={preset.concurrency}
            onChange={(e) => onChange({ ...preset, concurrency: parseInt(e.target.value) })}
          />
        </div>
        
        <div className="space-y-2">
          <Label>{text.retryCount}</Label>
          <Input
            type="number"
            min="0"
            max="10"
            value={preset.retryCount}
            onChange={(e) => onChange({ ...preset, retryCount: parseInt(e.target.value) })}
          />
        </div>
      </div>
      
      <div className="space-y-2">
        <Label>{text.timeout}</Label>
        <Input
          type="number"
          min="5"
          max="300"
          value={preset.timeout}
          onChange={(e) => onChange({ ...preset, timeout: parseInt(e.target.value) })}
        />
      </div>
      
      <div className="space-y-2">
        <Label>{text.logLevel}</Label>
        <Select 
          value={preset.logLevel} 
          onValueChange={(value: any) => onChange({ ...preset, logLevel: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="debug">Debug</SelectItem>
            <SelectItem value="info">Info</SelectItem>
            <SelectItem value="warn">Warning</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
