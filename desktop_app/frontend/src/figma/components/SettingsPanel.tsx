import { useState } from 'react';
import { X, Upload, Download, RotateCcw, Settings as SettingsIcon, FileText, Zap } from 'lucide-react';
import { Button } from './ui/button';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';
import { usePresets } from '../hooks/usePresets';
import { useBackend } from '../../hooks/useBackend';

interface SettingsPanelProps { isOpen: boolean; onClose: () => void; language: 'zh' | 'en'; }

export function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const { presets, importPresets } = usePresets();
  const { client, backendReachable } = useBackend();
  const [activeTab, setActiveTab] = useState<'ai'|'naming'|'runtime'>('ai');

  if (!isOpen) return null;

  async function handleImportFromBackend() {
    if (!backendReachable) return;
    const profiles = await client.listProfiles();
    const templates = await client.listTemplates();
    importPresets({ ai: presets.ai, naming: presets.naming, runtime: presets.runtime });
    // Mapping kept simple for this minimal stub
  }
  async function handleSaveAllToBackend() {
    if (!backendReachable) return;
    for (const p of presets.ai) await client.saveProfile(p.name || p.id, {});
    for (const n of presets.naming) await client.saveTemplate(n.name || n.id, { template: n.template });
  }

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-background/80" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full max-w-4xl bg-background border-l flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <SettingsIcon className="w-4 h-4" /> <FileText className="w-4 h-4" /> <Zap className="w-4 h-4" />
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleImportFromBackend}><Download className="w-4 h-4 mr-2" />Pull</Button>
            <Button variant="outline" size="sm" onClick={handleSaveAllToBackend}><Upload className="w-4 h-4 mr-2" />Save</Button>
            <Button variant="outline" size="sm"><RotateCcw className="w-4 h-4 mr-2" />Reset</Button>
            <Button variant="ghost" size="icon" onClick={onClose}><X className="w-5 h-5" /></Button>
          </div>
        </div>
        <div className="p-4">
          <TabsList>
            <TabsTrigger value="ai" onClick={() => setActiveTab('ai')}>AI</TabsTrigger>
            <TabsTrigger value="naming" onClick={() => setActiveTab('naming')}>Naming</TabsTrigger>
            <TabsTrigger value="runtime" onClick={() => setActiveTab('runtime')}>Runtime</TabsTrigger>
          </TabsList>
          <div className="text-sm text-muted-foreground mt-4">Active: {activeTab}</div>
        </div>
      </div>
    </div>
  );
}