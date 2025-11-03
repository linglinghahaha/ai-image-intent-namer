// API配置（主/翻译/摘要）
export interface APIConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
  systemPrompt?: string;
}

// AI模型预设
export interface AIPreset {
  id: string;
  name: string;
  mainApi: APIConfig; // 主API
  translationApi: APIConfig; // 翻译API
  summaryApi: APIConfig; // 摘要API
  temperature?: number;
  maxTokens?: number;
}

// 命名规则预设
export interface NamingPreset {
  id: string;
  name: string;
  template: string; // 例如: "{title}_{seq}_{intent}"
  strategy: 'context' | 'vision' | 'hybrid'; // 命名策略
  seqWidth: number; // 序号宽度，例如 3 -> "001"
  separator: string; // 分隔符
  caseSensitive: boolean;
  removeSpecialChars: boolean;
  maxLength?: number;
}

// 运行选项预设
export interface RuntimePreset {
  id: string;
  name: string;
  backup: boolean; // 是否备份原文件
  vision: boolean; // 是否启用视觉分析
  attachDir: string; // attachments目录路径
  concurrency: number; // 并发数
  retryCount: number; // 重试次数
  timeout: number; // 超时时间（秒）
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  autoSave: boolean; // 自动保存结果
}

// 预设集合
export interface Presets {
  ai: AIPreset[];
  naming: NamingPreset[];
  runtime: RuntimePreset[];
}

// 默认预设数据
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
    name: '标题_序号_图意',
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
    name: '序号_图意',
    template: '{seq}_{intent}',
    strategy: 'context',
    seqWidth: 2,
    separator: '_',
    caseSensitive: false,
    removeSpecialChars: true,
  },
  {
    id: 'intent-only',
    name: '仅图意',
    template: '{intent}',
    strategy: 'vision',
    seqWidth: 0,
    separator: '_',
    caseSensitive: false,
    removeSpecialChars: true,
  },
  {
    id: 'title-intent',
    name: '标题-图意',
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
    name: '安全模式',
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
    name: '快速模式',
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
    name: '视觉增强',
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
    name: '调试模式',
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
