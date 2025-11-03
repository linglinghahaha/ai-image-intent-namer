import { useState } from 'react';
import { Copy, Filter, Trash2, ChevronUp, ChevronDown, Square } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Progress } from './ui/progress';
import type { LogEntry } from '../App';
import { toast } from 'sonner@2.0.3';

interface LogPanelProps {
  logs: LogEntry[];
  isProcessing: boolean;
  onStop: () => void;
  language: 'zh' | 'en';
}

const t = {
  zh: {
    logs: '日志',
    clearLogs: '清空',
    copyAll: '复制全部',
    filter: '过滤',
    collapse: '收起',
    expand: '展开',
    stop: '停止',
    info: '信息',
    warning: '警告',
    error: '错误',
    llmCalls: 'LLM 调用',
    tokens: 'Tokens',
    progress: '进度',
    copiedToClipboard: '已复制到剪贴板',
    copyFailed: '复制失败',
  },
  en: {
    logs: 'Logs',
    clearLogs: 'Clear',
    copyAll: 'Copy All',
    filter: 'Filter',
    collapse: 'Collapse',
    expand: 'Expand',
    stop: 'Stop',
    info: 'Info',
    warning: 'Warning',
    error: 'Error',
    llmCalls: 'LLM Calls',
    tokens: 'Tokens',
    progress: 'Progress',
    copiedToClipboard: 'Copied to clipboard',
    copyFailed: 'Failed to copy',
  },
};

export function LogPanel({ logs, isProcessing, onStop, language }: LogPanelProps) {
  const text = t[language];
  const [isExpanded, setIsExpanded] = useState(true);
  const [filters, setFilters] = useState({
    info: true,
    warning: true,
    error: true,
  });

  const filteredLogs = logs.filter(log => filters[log.level]);

  const handleCopyAll = async () => {
    const logText = filteredLogs
      .map(log => `[${log.timestamp.toLocaleTimeString()}] [${log.level.toUpperCase()}] ${log.message}`)
      .join('\n');
    try {
      await navigator.clipboard.writeText(logText);
      toast.success(text.copiedToClipboard);
    } catch (error) {
      // Fallback: Create a textarea and copy
      const textarea = document.createElement('textarea');
      textarea.value = logText;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        toast.success(text.copiedToClipboard);
      } catch (err) {
        toast.error(text.copyFailed);
      }
      document.body.removeChild(textarea);
    }
  };

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return 'text-red-500';
      case 'warning':
        return 'text-yellow-500';
      default:
        return 'text-blue-500';
    }
  };

  const getLevelBadgeVariant = (level: LogEntry['level']): 'default' | 'destructive' | 'secondary' => {
    switch (level) {
      case 'error':
        return 'destructive';
      case 'warning':
        return 'secondary';
      default:
        return 'default';
    }
  };

  return (
    <div className="border-t bg-card shrink-0">
      <div className="px-4 py-2 border-b flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <h3 className="text-sm">{text.logs}</h3>
            <Badge variant="outline">{filteredLogs.length}</Badge>
          </div>

          {isProcessing && (
            <div className="flex items-center gap-2">
              <div className="w-32">
                <Progress value={33} />
              </div>
              <span className="text-xs text-muted-foreground">
                {text.progress}: 10/30
              </span>
            </div>
          )}

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{text.llmCalls}: 25</span>
            <span>{text.tokens}: 12,345</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isProcessing && (
            <Button size="sm" variant="destructive" onClick={onStop}>
              <Square className="w-3 h-3 mr-2" />
              {text.stop}
            </Button>
          )}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="ghost">
                <Filter className="w-4 h-4 mr-2" />
                {text.filter}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuCheckboxItem
                checked={filters.info}
                onCheckedChange={(checked) => setFilters(f => ({ ...f, info: checked }))}
              >
                {text.info}
              </DropdownMenuCheckboxItem>
              <DropdownMenuCheckboxItem
                checked={filters.warning}
                onCheckedChange={(checked) => setFilters(f => ({ ...f, warning: checked }))}
              >
                {text.warning}
              </DropdownMenuCheckboxItem>
              <DropdownMenuCheckboxItem
                checked={filters.error}
                onCheckedChange={(checked) => setFilters(f => ({ ...f, error: checked }))}
              >
                {text.error}
              </DropdownMenuCheckboxItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button size="sm" variant="ghost" onClick={handleCopyAll}>
            <Copy className="w-4 h-4 mr-2" />
            {text.copyAll}
          </Button>

          <Button size="sm" variant="ghost">
            <Trash2 className="w-4 h-4 mr-2" />
            {text.clearLogs}
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <>
                <ChevronDown className="w-4 h-4 mr-2" />
                {text.collapse}
              </>
            ) : (
              <>
                <ChevronUp className="w-4 h-4 mr-2" />
                {text.expand}
              </>
            )}
          </Button>
        </div>
      </div>

      {isExpanded && (
        <ScrollArea className="h-48">
          <div className="p-4 space-y-1 font-mono text-xs">
            {filteredLogs.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">
                No logs yet...
              </p>
            ) : (
              filteredLogs.map(log => (
                <div key={log.id} className="flex items-start gap-2">
                  <span className="text-muted-foreground shrink-0">
                    {log.timestamp.toLocaleTimeString()}
                  </span>
                  <Badge variant={getLevelBadgeVariant(log.level)} className="shrink-0">
                    {log.level}
                  </Badge>
                  <span className={getLevelColor(log.level)}>{log.message}</span>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
