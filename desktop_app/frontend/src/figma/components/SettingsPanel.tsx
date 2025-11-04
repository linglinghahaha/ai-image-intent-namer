import { useState } from 'react';
import { X, Upload, Download, RotateCcw, Settings as SettingsIcon, FileText, Zap } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Switch } from './ui/switch';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';
import { i18n } from '../../i18n';
import { usePresets } from '@figma/hooks/usePresets';
import { useBackend } from '@desktop/hooks/useBackend';
import type { AIPreset, NamingPreset, RuntimePreset } from '@figma/types/presets';

interface SettingsPanelProps { isOpen: boolean; onClose: () => void; language: 'zh' | 'en'; }

export function SettingsPanel({ isOpen, onClose, language }: SettingsPanelProps) {
  const { client, backendReachable } = useBackend();
  const { presets, importPresets, resetAllPresets, updateAIPreset, updateNamingPreset, updateRuntimePreset, duplicateAIPreset, duplicateNamingPreset, duplicateRuntimePreset, deleteAIPreset, deleteNamingPreset, deleteRuntimePreset } = usePresets();
  const [activeTab, setActiveTab] = useState<'ai'|'naming'|'runtime'>('ai');
  const [selectedAiId, setSelectedAiId] = useState<string>(() => presets.ai[0]?.id || '');
  const [selectedNamingId, setSelectedNamingId] = useState<string>(() => presets.naming[0]?.id || '');
  const [selectedRuntimeId, setSelectedRuntimeId] = useState<string>(() => presets.runtime[0]?.id || '');

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
      const rawStrategy = (typeof val === 'object' && val) ? (val.strategy ?? val.naming_strategy ?? val.mode) : undefined;
      const strategyMap: Record<string, NamingPreset['strategy']> = {
        seq: 'seq',
        above: 'above',
        below: 'below',
        between: 'above',
        intent: 'vision',
        hybrid: 'hybrid',
        sci: 'sci',
        context: 'above',
        vision: 'vision',
      };
      const strategy = strategyMap[String(rawStrategy || 'above').toLowerCase()] || 'above';
      const seqWidth = (typeof val === 'object' && val) ? (val.seq_width ?? val.seqWidth ?? 2) : 2;
      const maxLength = (typeof val === 'object' && val) ? (val.max_name_len ?? val.maxLength ?? 100) : 100;
      const separator = (typeof val === 'object' && val) ? (val.separator ?? '_') : '_';
      const caseSensitive = (typeof val === 'object' && val) ? Boolean(val.case_sensitive ?? val.caseSensitive ?? false) : false;
      const removeSpecialChars = (typeof val === 'object' && val) ? Boolean(val.remove_special_chars ?? val.removeSpecialChars ?? true) : true;
      return {
        id: `naming-import-${idx}`,
        name,
        template: String(tpl),
        strategy,
        seqWidth: Number(seqWidth) || 2,
        separator: String(separator || '_'),
        caseSensitive,
        removeSpecialChars,
        maxLength: Number(maxLength) || 100,
      } as NamingPreset;
    });

    importPresets({ ai, naming });
  }

  async function handleTestConnection() {
    try {
      const p = presets.ai.find(x => x.id === selectedAiId) as AIPreset | undefined;
      if (!p) return;
      const resp = await client.processText({
        prompt_template: 'ping {text}',
        content: 'hello',
        ai: {
          base_url: p.mainApi.baseUrl,
          api_key: p.mainApi.apiKey,
          model: p.mainApi.model,
          timeout: 15,
          max_retries: 1,
          rate_limit: 0.5,
          vision: false,
          batch_size: 1,
        },
        verbose: false,
      });
      if (resp && typeof resp.result === 'string') {
        toast.success(text.ai.connectionSuccess);
      } else {
        toast.error(text.ai.connectionFailed);
      }
    } catch (e) {
      toast.error(text.ai.connectionFailed);
    }
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

          {/* AI Presets */}
          {activeTab === 'ai' && (
            <div className="mt-4 space-y-4">
              <div className="flex items-end gap-2">
                <div className="grow">
                  <Label className="text-xs">{text.actions.selectPreset}</Label>
                  <Select value={selectedAiId} onValueChange={setSelectedAiId}>
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.ai.map(p => (
                        <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button size="sm" variant="outline" onClick={() => { const np = duplicateAIPreset(selectedAiId); if (np) setSelectedAiId(np.id); }}>
                  {text.actions.duplicate}
                </Button>
                <Button size="sm" variant="outline" onClick={() => { const name = window.prompt(text.ai.presetName); if (name) updateAIPreset(selectedAiId, { name }); }}>
                  {text.actions.saveAs}
                </Button>
                <Button size="sm" variant="destructive" onClick={() => { deleteAIPreset(selectedAiId); setSelectedAiId(presets.ai[0]?.id || ''); }}>
                  {text.actions.delete}
                </Button>
                <Button size="sm" onClick={handleTestConnection}>{text.ai.testConnection}</Button>
              </div>

              {(() => {
                const p = presets.ai.find(x => x.id === selectedAiId) as AIPreset | undefined;
                if (!p) return null;
                const updateGroup = (group: 'mainApi'|'translationApi'|'summaryApi', field: keyof AIPreset['mainApi'], value: string) => {
                  updateAIPreset(selectedAiId, { [group]: { ...p[group], [field]: value } } as unknown as Partial<AIPreset>);
                };
                return (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label className="text-xs">{text.sections.main}</Label>
                      <Input value={p.mainApi.baseUrl} onChange={e => updateGroup('mainApi','baseUrl', e.target.value)} placeholder={text.ai.baseUrl} />
                      <Input value={p.mainApi.apiKey} onChange={e => updateGroup('mainApi','apiKey', e.target.value)} placeholder={text.ai.apiKey} />
                      <Input value={p.mainApi.model} onChange={e => updateGroup('mainApi','model', e.target.value)} placeholder={text.ai.model} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">{text.sections.translation}</Label>
                      <Input value={p.translationApi.baseUrl} onChange={e => updateGroup('translationApi','baseUrl', e.target.value)} placeholder={text.ai.baseUrl} />
                      <Input value={p.translationApi.apiKey} onChange={e => updateGroup('translationApi','apiKey', e.target.value)} placeholder={text.ai.apiKey} />
                      <Input value={p.translationApi.model} onChange={e => updateGroup('translationApi','model', e.target.value)} placeholder={text.ai.model} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">{text.sections.summary}</Label>
                      <Input value={p.summaryApi.baseUrl} onChange={e => updateGroup('summaryApi','baseUrl', e.target.value)} placeholder={text.ai.baseUrl} />
                      <Input value={p.summaryApi.apiKey} onChange={e => updateGroup('summaryApi','apiKey', e.target.value)} placeholder={text.ai.apiKey} />
                      <Input value={p.summaryApi.model} onChange={e => updateGroup('summaryApi','model', e.target.value)} placeholder={text.ai.model} />
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* Naming Presets */}
          {activeTab === 'naming' && (
            <div className="mt-4 space-y-4">
              <div className="flex items-end gap-2">
                <div className="grow">
                  <Label className="text-xs">{text.actions.selectPreset}</Label>
                  <Select value={selectedNamingId} onValueChange={setSelectedNamingId}>
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.naming.map(p => (
                        <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button size="sm" variant="outline" onClick={() => { const np = duplicateNamingPreset(selectedNamingId); if (np) setSelectedNamingId(np.id); }}>{text.actions.duplicate}</Button>
                <Button size="sm" variant="outline" onClick={() => { const name = window.prompt(text.naming.presetName); if (name) updateNamingPreset(selectedNamingId, { name }); }}>{text.actions.saveAs}</Button>
                <Button size="sm" variant="destructive" onClick={() => { deleteNamingPreset(selectedNamingId); setSelectedNamingId(presets.naming[0]?.id || ''); }}>{text.actions.delete}</Button>
              </div>
              {(() => {
                const p = presets.naming.find(x => x.id === selectedNamingId) as NamingPreset | undefined;
                if (!p) return null;
                const up = (partial: Partial<NamingPreset>) => updateNamingPreset(selectedNamingId, partial);
                return (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label className="text-xs">{text.naming.presetName}</Label>
                      <Input value={p.name} onChange={e => up({ name: e.target.value })} />
                      <Label className="text-xs">{text.naming.template}</Label>
                      <Input value={p.template} onChange={e => up({ template: e.target.value })} placeholder={text.naming.templatePlaceholder} />
                      <Label className="text-xs">{text.naming.separator}</Label>
                      <Input value={p.separator} onChange={e => up({ separator: e.target.value })} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">{text.naming.strategy}</Label>
                      <Select value={p.strategy} onValueChange={v => up({ strategy: v as NamingPreset['strategy'] })}>
                        <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="seq">{text.naming.strategyOptions.seq}</SelectItem>
                          <SelectItem value="above">{text.naming.strategyOptions.above}</SelectItem>
                          <SelectItem value="below">{text.naming.strategyOptions.below}</SelectItem>
                          <SelectItem value="vision">{text.naming.strategyOptions.vision}</SelectItem>
                          <SelectItem value="hybrid">{text.naming.strategyOptions.hybrid}</SelectItem>
                          <SelectItem value="sci">{text.naming.strategyOptions.sci}</SelectItem>
                        </SelectContent>
                      </Select>
                      <Label className="text-xs">{text.naming.intentLanguage}</Label>
                      <Select value={p.intentLanguage ?? 'auto'} onValueChange={v => up({ intentLanguage: v as 'auto'|'zh'|'en' })}>
                        <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">{text.naming.languageOptions.auto}</SelectItem>
                          <SelectItem value="zh">{text.naming.languageOptions.zh}</SelectItem>
                          <SelectItem value="en">{text.naming.languageOptions.en}</SelectItem>
                        </SelectContent>
                      </Select>
                      <Label className="text-xs">{text.naming.reasonLanguage}</Label>
                      <Select value={p.reasonLanguage ?? 'zh'} onValueChange={v => up({ reasonLanguage: v as 'zh'|'en' })}>
                        <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="zh">{text.naming.languageOptions.zh}</SelectItem>
                          <SelectItem value="en">{text.naming.languageOptions.en}</SelectItem>
                        </SelectContent>
                      </Select>
                      <Label className="text-xs">{text.naming.seqWidth}</Label>
                      <Input type="number" value={p.seqWidth} onChange={e => up({ seqWidth: Number(e.target.value) || 0 })} />
                      <Label className="text-xs">{text.naming.maxLength}</Label>
                      <Input type="number" value={p.maxLength ?? 0} onChange={e => up({ maxLength: Number(e.target.value) || 0 })} />
                    </div>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <Label className="text-xs">{text.naming.caseSensitive}</Label>
                        <Switch checked={p.caseSensitive} onCheckedChange={v => up({ caseSensitive: Boolean(v) })} />
                      </div>
                      <div className="flex items-center justify-between">
                        <Label className="text-xs">{text.naming.removeSpecialChars}</Label>
                        <Switch checked={p.removeSpecialChars} onCheckedChange={v => up({ removeSpecialChars: Boolean(v) })} />
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* Runtime Presets */}
          {activeTab === 'runtime' && (
            <div className="mt-4 space-y-4">
              <div className="flex items-end gap-2">
                <div className="grow">
                  <Label className="text-xs">{text.actions.selectPreset}</Label>
                  <Select value={selectedRuntimeId} onValueChange={setSelectedRuntimeId}>
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.runtime.map(p => (
                        <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button size="sm" variant="outline" onClick={() => { const np = duplicateRuntimePreset(selectedRuntimeId); if (np) setSelectedRuntimeId(np.id); }}>{text.actions.duplicate}</Button>
                <Button size="sm" variant="outline" onClick={() => { const name = window.prompt(text.runtime.presetName); if (name) updateRuntimePreset(selectedRuntimeId, { name }); }}>{text.actions.saveAs}</Button>
                <Button size="sm" variant="destructive" onClick={() => { deleteRuntimePreset(selectedRuntimeId); setSelectedRuntimeId(presets.runtime[0]?.id || ''); }}>{text.actions.delete}</Button>
              </div>
              {(() => {
                const p = presets.runtime.find(x => x.id === selectedRuntimeId) as RuntimePreset | undefined;
                if (!p) return null;
                const up = (partial: Partial<RuntimePreset>) => updateRuntimePreset(selectedRuntimeId, partial);
                return (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label className="text-xs">{text.runtime.presetName}</Label>
                      <Input value={p.name} onChange={e => up({ name: e.target.value })} />
                      <Label className="text-xs">{text.runtime.attachDir}</Label>
                      <Input value={p.attachDir} onChange={e => up({ attachDir: e.target.value })} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">{text.runtime.concurrency}</Label>
                      <Input type="number" value={p.concurrency} onChange={e => up({ concurrency: Number(e.target.value) || 1 })} />
                      <Label className="text-xs">{text.runtime.retryCount}</Label>
                      <Input type="number" value={p.retryCount} onChange={e => up({ retryCount: Number(e.target.value) || 0 })} />
                      <Label className="text-xs">{text.runtime.timeout}</Label>
                      <Input type="number" value={p.timeout} onChange={e => up({ timeout: Number(e.target.value) || 30 })} />
                      <Label className="text-xs">{text.runtime.logLevel}</Label>
                      <Select value={p.logLevel} onValueChange={v => up({ logLevel: v as RuntimePreset['logLevel'] })}>
                        <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="debug">debug</SelectItem>
                          <SelectItem value="info">info</SelectItem>
                          <SelectItem value="warn">warn</SelectItem>
                          <SelectItem value="error">error</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <Label className="text-xs">{text.runtime.backup}</Label>
                        <Switch checked={p.backup} onCheckedChange={v => up({ backup: Boolean(v) })} />
                      </div>
                      <div className="flex items-center justify-between">
                        <Label className="text-xs">{text.runtime.vision}</Label>
                        <Switch checked={p.vision} onCheckedChange={v => up({ vision: Boolean(v) })} />
                      </div>
                      <div className="flex items-center justify-between">
                        <Label className="text-xs">{text.runtime.autoSave}</Label>
                        <Switch checked={p.autoSave} onCheckedChange={v => up({ autoSave: Boolean(v) })} />
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
