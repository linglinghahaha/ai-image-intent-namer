import { ChevronLeft, ChevronRight, Save, RotateCcw } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Textarea } from './ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from './ui/accordion';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { Card } from './ui/card';

interface ConfigurationDrawerProps {
  isOpen: boolean;
  onToggle: () => void;
  language: 'zh' | 'en';
}

const t = {
  zh: {
    configuration: '配置',
    profile: 'Profile',
    currentProfile: '当前配置',
    saveProfile: '保存配置',
    model: '模型',
    selectModel: '选择模型',
    strategy: '策略',
    batchStrategy: '批次策略',
    sequential: '顺序处理',
    contextBased: '基于上下文',
    mixed: '混合模式',
    research: '科研模式',
    batchSize: '批次大小',
    timeout: '超时时间 (秒)',
    retry: '重试次数',
    template: '模板',
    namingTemplate: '命名模板',
    placeholders: '占位符',
    preview: '预览',
    language: '语言',
    uiLanguage: 'UI 语言',
    intentLanguage: '意图语言',
    reasonLanguage: '原因语言',
    advanced: '高级选项',
    verboseLog: '详细日志',
    backupOriginal: '备份原文',
    downloadAttachments: '下载附件',
    enableVLM: '启用视觉模型',
    normalizeHTML: 'HTML 规范化',
    attachmentDir: '附件目录',
    maxNameLength: '最大名称长度',
    planReuse: 'Plan 重用',
    resetDefaults: '还原默认',
  },
  en: {
    configuration: 'Configuration',
    profile: 'Profile',
    currentProfile: 'Current Profile',
    saveProfile: 'Save Profile',
    model: 'Model',
    selectModel: 'Select Model',
    strategy: 'Strategy',
    batchStrategy: 'Batch Strategy',
    sequential: 'Sequential',
    contextBased: 'Context-based',
    mixed: 'Mixed',
    research: 'Research',
    batchSize: 'Batch Size',
    timeout: 'Timeout (seconds)',
    retry: 'Retry Count',
    template: 'Template',
    namingTemplate: 'Naming Template',
    placeholders: 'Placeholders',
    preview: 'Preview',
    language: 'Language',
    uiLanguage: 'UI Language',
    intentLanguage: 'Intent Language',
    reasonLanguage: 'Reason Language',
    advanced: 'Advanced',
    verboseLog: 'Verbose Logging',
    backupOriginal: 'Backup Original',
    downloadAttachments: 'Download Attachments',
    enableVLM: 'Enable Vision Model',
    normalizeHTML: 'Normalize HTML',
    attachmentDir: 'Attachment Directory',
    maxNameLength: 'Max Name Length',
    planReuse: 'Plan Reuse',
    resetDefaults: 'Reset Defaults',
  },
};

export function ConfigurationDrawer({ isOpen, onToggle, language }: ConfigurationDrawerProps) {
  const text = t[language];

  if (!isOpen) {
    return (
      <div className="w-12 border-l bg-card flex flex-col items-center py-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggle}
          className="rotate-0"
        >
          <ChevronLeft className="w-4 h-4" />
        </Button>
      </div>
    );
  }

  return (
    <div className="w-96 border-l bg-card flex flex-col shrink-0">
      <div className="p-4 border-b flex items-center justify-between">
        <h2>{text.configuration}</h2>
        <Button variant="ghost" size="sm" onClick={onToggle}>
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          <Accordion type="multiple" defaultValue={['profile', 'model', 'template']} className="space-y-2">
            <AccordionItem value="profile">
              <AccordionTrigger>{text.profile}</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <div>
                  <Label>{text.currentProfile}</Label>
                  <Select defaultValue="default">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">Default</SelectItem>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="claude">Claude</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button size="sm" className="w-full">
                  <Save className="w-4 h-4 mr-2" />
                  {text.saveProfile}
                </Button>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="model">
              <AccordionTrigger>{text.model}</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <div>
                  <Label>{text.selectModel}</Label>
                  <Select defaultValue="gpt-4">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="gpt-4">GPT-4</SelectItem>
                      <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                      <SelectItem value="claude-3">Claude 3</SelectItem>
                      <SelectItem value="gemini-pro">Gemini Pro</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="strategy">
              <AccordionTrigger>{text.strategy}</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <div>
                  <Label>{text.batchStrategy}</Label>
                  <Select defaultValue="sequential">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sequential">{text.sequential}</SelectItem>
                      <SelectItem value="context">{text.contextBased}</SelectItem>
                      <SelectItem value="mixed">{text.mixed}</SelectItem>
                      <SelectItem value="research">{text.research}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>{text.batchSize}</Label>
                  <Input type="number" defaultValue="5" min="1" max="20" />
                </div>
                <div>
                  <Label>{text.timeout}</Label>
                  <Input type="number" defaultValue="30" min="10" max="300" />
                </div>
                <div>
                  <Label>{text.retry}</Label>
                  <Input type="number" defaultValue="3" min="0" max="10" />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="template">
              <AccordionTrigger>{text.template}</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <div>
                  <Label>{text.namingTemplate}</Label>
                  <Textarea
                    defaultValue="{intent}_{index}"
                    placeholder="e.g., {intent}_{index}"
                    rows={3}
                  />
                </div>
                <Card className="p-3 bg-muted/50">
                  <p className="text-xs mb-2">{text.placeholders}:</p>
                  <div className="flex flex-wrap gap-1">
                    {['{intent}', '{index}', '{date}', '{context}'].map(ph => (
                      <code key={ph} className="text-xs bg-background px-2 py-1 rounded">
                        {ph}
                      </code>
                    ))}
                  </div>
                </Card>
                <div>
                  <Label>{text.preview}</Label>
                  <Input value="scene_description_1.png" disabled />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="language">
              <AccordionTrigger>{text.language}</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <div>
                  <Label>{text.uiLanguage}</Label>
                  <Select defaultValue="zh">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="zh">中文</SelectItem>
                      <SelectItem value="en">English</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>{text.intentLanguage}</Label>
                  <Select defaultValue="en">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="zh">中文</SelectItem>
                      <SelectItem value="en">English</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>{text.reasonLanguage}</Label>
                  <Select defaultValue="zh">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="zh">中文</SelectItem>
                      <SelectItem value="en">English</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="advanced">
              <AccordionTrigger>{text.advanced}</AccordionTrigger>
              <AccordionContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>{text.verboseLog}</Label>
                  <Switch />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <Label>{text.backupOriginal}</Label>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <Label>{text.downloadAttachments}</Label>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <Label>{text.enableVLM}</Label>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <Label>{text.normalizeHTML}</Label>
                  <Switch />
                </div>
                <Separator />
                <div>
                  <Label>{text.attachmentDir}</Label>
                  <Input defaultValue="./attachments" />
                </div>
                <div>
                  <Label>{text.maxNameLength}</Label>
                  <Input type="number" defaultValue="255" min="50" max="500" />
                </div>
                <div className="flex items-center justify-between">
                  <Label>{text.planReuse}</Label>
                  <Switch />
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </ScrollArea>

      <div className="p-4 border-t">
        <Button variant="outline" size="sm" className="w-full">
          <RotateCcw className="w-4 h-4 mr-2" />
          {text.resetDefaults}
        </Button>
      </div>
    </div>
  );
}
