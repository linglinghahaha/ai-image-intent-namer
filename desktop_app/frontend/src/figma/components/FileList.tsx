import { useState, useRef } from 'react';
import { Plus, Trash2, FileText, CheckCircle2, AlertCircle, Loader2, FolderOpen } from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import { cn } from './ui/utils';
import type { MarkdownFile } from '../App';

interface FileListProps {
  files: MarkdownFile[];
  selectedFileId: string | null;
  onSelectFile: (fileId: string) => void;
  onAddFiles: (files: File[]) => void;
  onRemoveFiles: (fileIds: string[]) => void;
  onClearAll: () => void;
  language: 'zh' | 'en';
}

const t = {
  zh: {
    title: '文件列表',
    addFiles: '添加文件',
    clearAll: '清空',
    remove: '移除',
    images: '张图片',
    processed: '已处理',
    status: {
      pending: '待处理',
      processing: '处理中',
      completed: '已完成',
      error: '错误',
    },
    empty: '暂无文件',
    dragDrop: '拖拽 Markdown 文件到此处',
    attachments: '附件目录',
  },
  en: {
    title: 'File List',
    addFiles: 'Add Files',
    clearAll: 'Clear All',
    remove: 'Remove',
    images: 'images',
    processed: 'processed',
    status: {
      pending: 'Pending',
      processing: 'Processing',
      completed: 'Completed',
      error: 'Error',
    },
    empty: 'No files',
    dragDrop: 'Drag Markdown files here',
    attachments: 'Attachments',
  },
};

export function FileList({
  files,
  selectedFileId,
  onSelectFile,
  onAddFiles,
  onRemoveFiles,
  onClearAll,
  language,
}: FileListProps) {
  const text = t[language];
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      file => file.name.endsWith('.md') || file.name.endsWith('.markdown')
    );
    
    if (droppedFiles.length > 0) {
      onAddFiles(droppedFiles);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length > 0) {
      onAddFiles(selectedFiles);
    }
  };

  const getStatusIcon = (status: MarkdownFile['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <FileText className="w-4 h-4 text-muted-foreground" />;
    }
  };

  return (
    <div className="w-80 border-r bg-card flex flex-col shrink-0">
      <div className="p-4 border-b">
        <h2 className="mb-3">{text.title}</h2>
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            className="flex-1"
          >
            <Plus className="w-4 h-4 mr-2" />
            {text.addFiles}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onClearAll}
            disabled={files.length === 0}
          >
            {text.clearAll}
          </Button>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".md,.markdown"
          multiple
          className="hidden"
          onChange={handleFileSelect}
        />
      </div>

      <ScrollArea className="flex-1">
        <div
          className={cn(
            'p-4',
            dragOver && 'bg-accent/50'
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {files.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p className="text-sm">{text.empty}</p>
              <p className="text-xs mt-2">{text.dragDrop}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {files.map(file => (
                <div
                  key={file.id}
                  className={cn(
                    'p-3 rounded-lg border cursor-pointer transition-colors hover:bg-accent/50',
                    selectedFileId === file.id && 'bg-accent border-primary'
                  )}
                  onClick={() => onSelectFile(file.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 flex-1 min-w-0">
                      {getStatusIcon(file.status)}
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-sm">{file.name}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-muted-foreground">
                            {file.imageCount} {text.images}
                          </span>
                          {file.processedCount > 0 && (
                            <Badge variant="secondary" className="text-xs">
                              {file.processedCount}/{file.imageCount} {text.processed}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {text.status[file.status]}
                        </p>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemoveFiles([file.id]);
                      }}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="p-4 border-t">
        <Button variant="outline" size="sm" className="w-full">
          <FolderOpen className="w-4 h-4 mr-2" />
          {text.attachments}
        </Button>
      </div>
    </div>
  );
}
