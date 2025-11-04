// Types for presets and API configurations
export interface APIConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
  systemPrompt?: string;
}

export interface AIPreset {
  id: string;
  name: string;
  mainApi: APIConfig;
  translationApi: APIConfig;
  summaryApi: APIConfig;
  temperature?: number;
  maxTokens?: number;
}

export interface NamingPreset {
  id: string;
  name: string;
  template: string;
  strategy: 'context' | 'vision' | 'hybrid';
  seqWidth: number;
  separator: string;
  caseSensitive: boolean;
  removeSpecialChars: boolean;
  maxLength?: number;
}

export interface RuntimePreset {
  id: string;
  name: string;
  backup: boolean;
  vision: boolean;
  attachDir: string;
  concurrency: number;
  retryCount: number;
  timeout: number;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  autoSave: boolean;
}

export interface Presets {
  ai: AIPreset[];
  naming: NamingPreset[];
  runtime: RuntimePreset[];
}

// Defaults
export const defaultAIPresets: AIPreset[] = [
  {
    id: 'siliconflow-qwen',
    name: 'Siliconflow - Qwen',
    mainApi: {
      baseUrl: 'https://api.siliconflow.cn/v1',
      apiKey: '',
      model: 'Qwen/Qwen2.5-7B-Instruct',
      systemPrompt: 'You are an AI assistant that helps name images based on their content and context.',
    },
    translationApi: {
      baseUrl: 'https://api.siliconflow.cn/v1',
      apiKey: '',
      model: 'Qwen/Qwen2.5-7B-Instruct',
      systemPrompt: 'Translate the following text to {target_language}.',
    },
    summaryApi: {
      baseUrl: 'https://api.siliconflow.cn/v1',
      apiKey: '',
      model: 'Qwen/Qwen2.5-7B-Instruct',
      systemPrompt: 'Summarize the following text concisely.',
    },
    temperature: 0.7,
    maxTokens: 2000,
  },
  {
    id: 'openai-gpt4',
    name: 'OpenAI - GPT-4',
    mainApi: {
      baseUrl: 'https://api.openai.com/v1',
      apiKey: '',
      model: 'gpt-4',
      systemPrompt: 'You are an AI assistant that helps name images based on their content and context.',
    },
    translationApi: {
      baseUrl: 'https://api.openai.com/v1',
      apiKey: '',
      model: 'gpt-3.5-turbo',
      systemPrompt: 'Translate the following text to {target_language}.',
    },
    summaryApi: {
      baseUrl: 'https://api.openai.com/v1',
      apiKey: '',
      model: 'gpt-3.5-turbo',
      systemPrompt: 'Summarize the following text concisely.',
    },
    temperature: 0.7,
    maxTokens: 2000,
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    mainApi: {
      baseUrl: 'https://api.deepseek.com/v1',
      apiKey: '',
      model: 'deepseek-chat',
      systemPrompt: 'You are an AI assistant that helps name images based on their content and context.',
    },
    translationApi: {
      baseUrl: 'https://api.deepseek.com/v1',
      apiKey: '',
      model: 'deepseek-chat',
      systemPrompt: 'Translate the following text to {target_language}.',
    },
    summaryApi: {
      baseUrl: 'https://api.deepseek.com/v1',
      apiKey: '',
      model: 'deepseek-chat',
      systemPrompt: 'Summarize the following text concisely.',
    },
    temperature: 0.7,
    maxTokens: 2000,
  },
];

export const defaultNamingPresets: NamingPreset[] = [
  {
    id: 'title-seq-intent',
    name: 'Title_Seq_Intent',
    template: '{title}_{seq}_{intent}',
    strategy: 'context',
    seqWidth: 3,
    separator: '_',
    caseSensitive: false,
    removeSpecialChars: true,
    maxLength: 100,
  },
  {
    id: 'seq-intent',
    name: 'Seq_Intent',
    template: '{seq}_{intent}',
    strategy: 'context',
    seqWidth: 2,
    separator: '_',
    caseSensitive: false,
    removeSpecialChars: true,
  },
  {
    id: 'intent-only',
    name: 'Intent_Only',
    template: '{intent}',
    strategy: 'vision',
    seqWidth: 0,
    separator: '_',
    caseSensitive: false,
    removeSpecialChars: true,
  },
  {
    id: 'title-intent',
    name: 'Title-Intent',
    template: '{title}-{intent}',
    strategy: 'hybrid',
    seqWidth: 0,
    separator: '-',
    caseSensitive: false,
    removeSpecialChars: true,
  },
];

export const defaultRuntimePresets: RuntimePreset[] = [
  {
    id: 'safe',
    name: 'Safe Mode',
    backup: true,
    vision: false,
    attachDir: './attachments',
    concurrency: 1,
    retryCount: 3,
    timeout: 30,
    logLevel: 'info',
    autoSave: true,
  },
  {
    id: 'fast',
    name: 'Fast Mode',
    backup: false,
    vision: false,
    attachDir: './attachments',
    concurrency: 5,
    retryCount: 1,
    timeout: 15,
    logLevel: 'warn',
    autoSave: false,
  },
  {
    id: 'vision-enabled',
    name: 'Vision Enhanced',
    backup: true,
    vision: true,
    attachDir: './attachments',
    concurrency: 2,
    retryCount: 2,
    timeout: 60,
    logLevel: 'info',
    autoSave: true,
  },
  {
    id: 'debug',
    name: 'Debug Mode',
    backup: true,
    vision: true,
    attachDir: './attachments',
    concurrency: 1,
    retryCount: 5,
    timeout: 120,
    logLevel: 'debug',
    autoSave: true,
  },
];
