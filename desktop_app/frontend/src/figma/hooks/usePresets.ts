import { useState, useEffect, useCallback } from 'react';
import type { AIPreset, NamingPreset, RuntimePreset, Presets, APIConfig } from '../types/presets';
import { defaultAIPresets, defaultNamingPresets, defaultRuntimePresets } from '../types/presets';

const STORAGE_KEY = 'ai-image-namer-presets';

// 迁移旧格式的AI预设到新格式
function migrateAIPreset(preset: any): AIPreset {
  // 如果已经是新格式，直接返回
  if (preset.mainApi && preset.translationApi && preset.summaryApi) {
    return preset as AIPreset;
  }
  
  // 旧格式迁移到新格式
  const baseConfig: APIConfig = {
    baseUrl: preset.baseUrl || 'https://api.openai.com/v1',
    apiKey: preset.apiKey || '',
    model: preset.model || 'gpt-4',
    systemPrompt: preset.systemPrompt || 'You are a helpful assistant.',
  };
  
  return {
    id: preset.id,
    name: preset.name,
    mainApi: {
      ...baseConfig,
      systemPrompt: preset.systemPrompt || 'You are an AI assistant that helps name images based on their content and context.',
    },
    translationApi: {
      ...baseConfig,
      model: 'gpt-3.5-turbo',
      systemPrompt: 'Translate the following text to {target_language}.',
    },
    summaryApi: {
      ...baseConfig,
      model: 'gpt-3.5-turbo',
      systemPrompt: 'Summarize the following text concisely.',
    },
    temperature: preset.temperature || 0.7,
    maxTokens: preset.maxTokens || 2000,
  };
}

// 从localStorage加载预设
function loadPresets(): Presets {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      
      // 迁移AI预设
      const migratedAI = (parsed.ai || defaultAIPresets).map(migrateAIPreset);
      
      return {
        ai: migratedAI,
        naming: parsed.naming || defaultNamingPresets,
        runtime: parsed.runtime || defaultRuntimePresets,
      };
    }
  } catch (error) {
    console.error('Failed to load presets:', error);
  }
  
  return {
    ai: defaultAIPresets,
    naming: defaultNamingPresets,
    runtime: defaultRuntimePresets,
  };
}

// 保存预设到localStorage
function savePresets(presets: Presets): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(presets));
  } catch (error) {
    console.error('Failed to save presets:', error);
  }
}

export function usePresets() {
  const [presets, setPresets] = useState<Presets>(loadPresets);

  // 保存到localStorage
  useEffect(() => {
    savePresets(presets);
  }, [presets]);

  // AI预设操作
  const addAIPreset = useCallback((preset: Omit<AIPreset, 'id'>) => {
    const newPreset: AIPreset = {
      ...preset,
      id: `ai-${Date.now()}`,
    };
    setPresets(prev => ({
      ...prev,
      ai: [...prev.ai, newPreset],
    }));
    return newPreset;
  }, []);

  const updateAIPreset = useCallback((id: string, updates: Partial<AIPreset>) => {
    setPresets(prev => ({
      ...prev,
      ai: prev.ai.map(p => p.id === id ? { ...p, ...updates } : p),
    }));
  }, []);

  const deleteAIPreset = useCallback((id: string) => {
    setPresets(prev => ({
      ...prev,
      ai: prev.ai.filter(p => p.id !== id),
    }));
  }, []);

  const duplicateAIPreset = useCallback((id: string) => {
    const preset = presets.ai.find(p => p.id === id);
    if (preset) {
      const newPreset: AIPreset = {
        ...preset,
        id: `ai-${Date.now()}`,
        name: `${preset.name} (副本)`,
      };
      setPresets(prev => ({
        ...prev,
        ai: [...prev.ai, newPreset],
      }));
      return newPreset;
    }
  }, [presets.ai]);

  // 命名规则预设操作
  const addNamingPreset = useCallback((preset: Omit<NamingPreset, 'id'>) => {
    const newPreset: NamingPreset = {
      ...preset,
      id: `naming-${Date.now()}`,
    };
    setPresets(prev => ({
      ...prev,
      naming: [...prev.naming, newPreset],
    }));
    return newPreset;
  }, []);

  const updateNamingPreset = useCallback((id: string, updates: Partial<NamingPreset>) => {
    setPresets(prev => ({
      ...prev,
      naming: prev.naming.map(p => p.id === id ? { ...p, ...updates } : p),
    }));
  }, []);

  const deleteNamingPreset = useCallback((id: string) => {
    setPresets(prev => ({
      ...prev,
      naming: prev.naming.filter(p => p.id !== id),
    }));
  }, []);

  const duplicateNamingPreset = useCallback((id: string) => {
    const preset = presets.naming.find(p => p.id === id);
    if (preset) {
      const newPreset: NamingPreset = {
        ...preset,
        id: `naming-${Date.now()}`,
        name: `${preset.name} (副本)`,
      };
      setPresets(prev => ({
        ...prev,
        naming: [...prev.naming, newPreset],
      }));
      return newPreset;
    }
  }, [presets.naming]);

  // 运行选项预设操作
  const addRuntimePreset = useCallback((preset: Omit<RuntimePreset, 'id'>) => {
    const newPreset: RuntimePreset = {
      ...preset,
      id: `runtime-${Date.now()}`,
    };
    setPresets(prev => ({
      ...prev,
      runtime: [...prev.runtime, newPreset],
    }));
    return newPreset;
  }, []);

  const updateRuntimePreset = useCallback((id: string, updates: Partial<RuntimePreset>) => {
    setPresets(prev => ({
      ...prev,
      runtime: prev.runtime.map(p => p.id === id ? { ...p, ...updates } : p),
    }));
  }, []);

  const deleteRuntimePreset = useCallback((id: string) => {
    setPresets(prev => ({
      ...prev,
      runtime: prev.runtime.filter(p => p.id !== id),
    }));
  }, []);

  const duplicateRuntimePreset = useCallback((id: string) => {
    const preset = presets.runtime.find(p => p.id === id);
    if (preset) {
      const newPreset: RuntimePreset = {
        ...preset,
        id: `runtime-${Date.now()}`,
        name: `${preset.name} (副本)`,
      };
      setPresets(prev => ({
        ...prev,
        runtime: [...prev.runtime, newPreset],
      }));
      return newPreset;
    }
  }, [presets.runtime]);

  // 重置所有预设
  const resetAllPresets = useCallback(() => {
    const defaultPresets: Presets = {
      ai: defaultAIPresets,
      naming: defaultNamingPresets,
      runtime: defaultRuntimePresets,
    };
    setPresets(defaultPresets);
  }, []);

  // 导入预设
  const importPresets = useCallback((importedPresets: Partial<Presets>) => {
    setPresets(prev => ({
      ai: importedPresets.ai || prev.ai,
      naming: importedPresets.naming || prev.naming,
      runtime: importedPresets.runtime || prev.runtime,
    }));
  }, []);

  // 导出预设
  const exportPresets = useCallback(() => {
    return JSON.stringify(presets, null, 2);
  }, [presets]);

  return {
    presets,
    
    // AI预设
    addAIPreset,
    updateAIPreset,
    deleteAIPreset,
    duplicateAIPreset,
    
    // 命名规则预设
    addNamingPreset,
    updateNamingPreset,
    deleteNamingPreset,
    duplicateNamingPreset,
    
    // 运行选项预设
    addRuntimePreset,
    updateRuntimePreset,
    deleteRuntimePreset,
    duplicateRuntimePreset,
    
    // 通用操作
    resetAllPresets,
    importPresets,
    exportPresets,
  };
}
