import { useState } from 'react';
import { X, Upload, Download, RotateCcw, Settings as SettingsIcon, FileText, Zap } from 'lucide-react';
import { Button } from './ui/button';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';
import { i18n } from '../../i18n';
import { usePresets } from '../hooks/usePresets';
import { useBackend } from '../../hooks/useBackend';
import type { AIPreset, NamingPreset } from '../types/presets';

interface SettingsPanelProps { isOpen: boolean; onClose: () => void; language: 'zh' | 'en'; }

export function SettingsPanel({ isOpen, onClose, language }: SettingsPanelProps) {
  const { client, backendReachable } = useBackend();
  const { presets, importPresets, resetAllPresets } = usePresets();
  const [activeTab, setActiveTab] = useState<'ai'|'naming'|'runtime'>('ai');

  if (!isOpen) return null;

  async function handleImportFromBackend() {
    if (!backendReachable) return;
    const profiles: Record<string, any> = await client.listProfiles();
    const templates: Record<string, any> = await client.listTemplates();

    const ai: AIPreset[] = Object.entries(profiles || {}).map(([name, cfg], idx) => {
      const baseUrl = cfg?.base_url ?? cfg?.baseUrl ?? '';
      const apiKey = cfg?.api_key ?? cfg?.apiKey ?? '';
      const model = cfg?.model ?? '';
      return {
        id: `ai-import-${idx}`,
        name,
        mainApi: { baseUrl, apiKey, model },
        translationApi: { baseUrl, apiKey, model },
        summaryApi: { baseUrl, apiKey, model },
        temperature: 0.7,
        maxTokens: 2000,
      } as AIPreset;
    });

    const naming: NamingPreset[] = Object.entries(templates || {}).map(([name, val], idx) => {
      const tpl = typeof val === 'string' ? val : (val?.template ?? '{title}_{seq}_{intent}');
      return {
        id: `naming-import-${idx}`,
        name,
        template: String(tpl),
        strategy: 'context',
        seqWidth: 2,
        separator: '_',
        caseSensitive: false,
        removeSpecialChars: true,
        maxLength: 100,
      } as NamingPreset;
    });

    importPresets({ ai, naming });
  }

  async function handleSaveAllToBackend() {
    if (!backendReachable) return;
    for (const p of presets.ai) {
      await client.saveProfile(p.name || p.id, {
        base_url: p.mainApi.baseUrl,
        api_key: p.mainApi.apiKey,
        model: p.mainApi.model,
      });
    }
    for (const n of presets.naming) {
      await client.saveTemplate(n.name || n.id, { template: n.template });
    }
  }

  const text = i18n(language).settings;
  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-background/80" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full max-w-4xl bg-background border-l flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <SettingsIcon className="w-4 h-4" />
            <FileText className="w-4 h-4" />
            <Zap className="w-4 h-4" />
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleImportFromBackend}>
              <Download className="w-4 h-4 mr-2" />{text.actions.pullFromBackend}
            </Button>
            <Button variant="outline" size="sm" onClick={handleSaveAllToBackend}>
              <Upload className="w-4 h-4 mr-2" />{text.actions.saveToBackend}
            </Button>
            <Button variant="outline" size="sm" onClick={resetAllPresets}>
              <RotateCcw className="w-4 h-4 mr-2" />{text.actions.reset}
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose} aria-label={text.close}>
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>
        <div className="p-4">
          <Tabs value={activeTab}>
            <TabsList>
              <TabsTrigger value="ai" onClick={() => setActiveTab('ai')}>{text.nav.aiModel}</TabsTrigger>
              <TabsTrigger value="naming" onClick={() => setActiveTab('naming')}>{text.nav.namingRules}</TabsTrigger>
              <TabsTrigger value="runtime" onClick={() => setActiveTab('runtime')}>{text.nav.runtimeOptions}</TabsTrigger>
            </TabsList>
          </Tabs>
          <div className="text-sm text-muted-foreground mt-4">Active: {activeTab}</div>
        </div>
      </div>
    </div>
  );
}
