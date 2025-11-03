import { 
  X, 
  ChevronLeft, 
  ChevronRight,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { Switch } from './ui/switch';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from './ui/sheet';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from './ui/tabs';
import { ImageWithFallback } from './figma/ImageWithFallback';
import type { ImageEntry } from '../App';
import { toast } from 'sonner@2.0.3';

interface CandidateItem {
  name: string;
  strategy: string;
  confidence: number;
  reason?: string;
}

interface ImageReviewPanelProps {
  image: ImageEntry;
  isOpen: boolean;
  onClose: () => void;
  onApply: (newName: string) => void;
  onSkip: () => void;
  onNext: () => void;
  onPrevious: () => void;
  language: 'zh' | 'en';
  totalImages?: number;
  previousImage?: ImageEntry;
  nextImage?: ImageEntry;
}

const t = {
  zh: {
    reviewTitle: '单图复审',
    status: {
      pending: '待确认',
      skipped: '已跳过',
      completed: '已写回',
      processing: '生成中',
    },
    markSkipped: '标记跳过',
    close: '关闭',
    previous: '上一个',
    next: '下一个',
    
    imageTitle: '图片',
    source: '来源',
    document: '文档',
    adjacentImages: '邻接图片',
    previousImageLabel: '上一张',
    nextImageLabel: '下一张',
    noImage: '暂无图片',
    
    previousContext: '上文',
    nextContext: '下文',
    characterCount: '字符',
    translate: '翻译',
    summarize: '归纳',
    
    candidateStrategies: '候选策略',
    strategy: {
      prevContext3: '上文3候选',
      nextContext3: '下文3候选',
      directIntent: '直接意图',
      phonetic: '音意形',
    },
    confidence: '置信度',
    
    renameTo: '重命名为',
    confirmAndGenerate: '确定并生成',
    confirmAndContinue: '确定并继续',
    confirmAndClose: '确定并关闭',
    cancel: '取消',
    
    copiedToClipboard: '已复制到剪贴板',
    applied: '已应用',
    nameRequired: '命名不能为空',
  },
  en: {
    reviewTitle: 'Image Review',
    status: {
      pending: 'Pending',
      skipped: 'Skipped',
      completed: 'Completed',
      processing: 'Processing',
    },
    markSkipped: 'Mark as Skipped',
    close: 'Close',
    previous: 'Previous',
    next: 'Next',
    
    imageTitle: 'Image',
    source: 'Source',
    document: 'Document',
    adjacentImages: 'Adjacent Images',
    previousImageLabel: 'Previous',
    nextImageLabel: 'Next',
    noImage: 'No Image',
    
    previousContext: 'Previous Context',
    nextContext: 'Next Context',
    characterCount: 'chars',
    translate: 'Translate',
    summarize: 'Summarize',
    
    candidateStrategies: 'Candidate Strategies',
    strategy: {
      prevContext3: 'Prev Context 3',
      nextContext3: 'Next Context 3',
      directIntent: 'Direct Intent',
      phonetic: 'Phonetic',
    },
    confidence: 'Confidence',
    
    renameTo: 'Rename to',
    confirmAndGenerate: 'Confirm & Generate',
    confirmAndContinue: 'Confirm & Continue',
    confirmAndClose: 'Confirm & Close',
    cancel: 'Cancel',
    
    copiedToClipboard: 'Copied to clipboard',
    applied: 'Applied',
    nameRequired: 'Name cannot be empty',
  },
};

export function ImageReviewPanel({
  image,
  isOpen,
  onClose,
  onApply,
  onSkip,
  onNext,
  onPrevious,
  language,
  totalImages = 0,
  previousImage,
  nextImage,
}: ImageReviewPanelProps) {
  const text = t[language];
  
  // State management
  const [customName, setCustomName] = useState('');
  const [isSkipped, setIsSkipped] = useState(image.skipped);
  const [selectedCandidate, setSelectedCandidate] = useState('');
  
  // Mock data
  const [previousContextText] = useState('Once again, I spent more time on an addendum than on the main blog post, last Friday\'s _. First I thought I would compose a list of amusing domain names using new web address endings. After starting, I realized that I had already provided enough for you to amuse yourself better than I could. Then I considered expanding on expired_ domain names, summarizing how thousands of domain names expire every day and are eventually offered for sale. After plowing through different sources, I decided there would be little interest--unless, of course, someone wanted to buy this blog\' s domain name. (Contact me directly.) And then I came across a book');
  const [nextContextText] = useState('Orb webs are generally associated with spiders in the Araneoidea superfamily, particularly those in the Araneidae and Tetragnathidae families, but there are orb-weaver spiders in the Uloboridae superfamily whose webs are quite different. (Photo from smithsonianscience.si.edu)');
  
  const [candidates] = useState<CandidateItem[]>([
    { name: 'domain_name_humor', strategy: 'prevContext3', confidence: 0.4, reason: '上文关于域名的有趣内容，这篇幽默笔记本域名的%domain_choose%pain.com图像题裁，这句题主白痴，估计您已知悉我另外配置' },
    { name: 'orb_web_spider', strategy: 'nextContext3', confidence: 0.95, reason: '由内容关于一个"蜘蛛网"的科学时的，下文全部围绕"orb web spider"蜘蛛网主题非常密切相符，得随由它包括完全坚持某种毕毕' },
    { name: 'spider_web_structure', strategy: 'nextContext3', confidence: 0.65, reason: '结合内容下文候选，作意互动代表性的相关作为属于不同，估计共包含简单到高木后本' },
    { name: 'Orb-weaver_spider_webs', strategy: 'directIntent', confidence: 0, reason: '' },
  ]);
  
  // Initialize state when image changes
  useEffect(() => {
    setCustomName(image.finalName || '');
    setIsSkipped(image.skipped);
    setSelectedCandidate('');
  }, [image.id]);
  
  // Keyboard shortcuts
  useEffect(() => {
    if (!isOpen) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        handleConfirmAndContinue();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, customName]);
  
  // Handlers
  const handleToggleSkip = () => {
    setIsSkipped(!isSkipped);
    if (!isSkipped) {
      onSkip();
    }
  };
  
  const handleConfirmAndContinue = () => {
    const finalName = customName.trim();
    if (!finalName) {
      toast.error(text.nameRequired);
      return;
    }
    onApply(finalName);
    onNext();
    toast.success(text.applied);
  };
  
  const handleConfirmAndClose = () => {
    const finalName = customName.trim();
    if (!finalName) {
      toast.error(text.nameRequired);
      return;
    }
    onApply(finalName);
    onClose();
    toast.success(text.applied);
  };
  
  const getStatusBadge = () => {
    if (isSkipped) {
      return <Badge variant="secondary">{text.status.skipped}</Badge>;
    }
    if (image.status === 'completed') {
      return <Badge variant="default">{text.status.completed}</Badge>;
    }
    if (image.status === 'processing') {
      return <Badge variant="default">{text.status.processing}</Badge>;
    }
    return <Badge variant="outline">{text.status.pending}</Badge>;
  };
  
  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[98vw] max-w-[1800px] p-0 flex flex-col">
        {/* Header - 参照参考图设计 */}
        <SheetHeader className="px-6 py-3 border-b flex-shrink-0">
          <div className="flex items-center justify-between">
            {/* 左侧：标题和状态 */}
            <div className="flex items-center gap-3">
              <SheetTitle className="text-lg">
                {text.reviewTitle} #{image.index} / {totalImages}
              </SheetTitle>
              {getStatusBadge()}
            </div>
            
            {/* 中间：标记跳过开关 */}
            <div className="flex items-center gap-2">
              <Label htmlFor="skip-toggle" className="text-sm cursor-pointer">
                {text.markSkipped}
              </Label>
              <Switch
                checked={isSkipped}
                onCheckedChange={handleToggleSkip}
                id="skip-toggle"
              />
            </div>
            
            {/* 右侧：导航按钮 */}
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={onPrevious}>
                <ChevronLeft className="w-4 h-4 mr-1" />
                {text.previous}
              </Button>
              <Button variant="ghost" size="sm" onClick={onNext}>
                {text.next}
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <SheetDescription className="sr-only">
            Review and edit image naming for {image.originalPath}
          </SheetDescription>
        </SheetHeader>
        
        {/* Main Content - 两列布局 */}
        <div className="flex-1 flex overflow-hidden">
          {/* 左侧：图片预览区域 */}
          <div className="w-[45%] border-r flex flex-col bg-muted/30">
            <div className="p-4 space-y-3">
              {/* 图片信息 */}
              <div className="space-y-2">
                <h3 className="font-medium">{text.imageTitle} #{image.index}</h3>
                <div className="text-sm space-y-1">
                  <div className="flex gap-2">
                    <span className="text-muted-foreground min-w-12">{text.source}:</span>
                    <span className="font-mono text-xs break-all">{image.originalPath}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-muted-foreground min-w-12">{text.document}:</span>
                    <span className="text-xs">Redired--Now_What_Web_Addresses_Addendum</span>
                  </div>
                </div>
              </div>
              
              <Separator />
              
              {/* 图片预览 */}
              <div className="bg-background rounded-lg border p-4">
                <div className="aspect-square bg-muted/50 rounded flex items-center justify-center overflow-hidden">
                  <ImageWithFallback
                    src={image.thumbnail || '/placeholder-image.png'}
                    alt={image.originalPath}
                    className="w-full h-full object-contain"
                  />
                </div>
              </div>
              
              <Separator />
              
              {/* 邻接图片 */}
              <div className="space-y-2">
                <Label className="text-sm">{text.adjacentImages}</Label>
                <div className="grid grid-cols-2 gap-3">
                  {/* 上一张 */}
                  <div className="space-y-1">
                    <Label className="text-xs text-muted-foreground">{text.previousImageLabel}</Label>
                    <div 
                      className="aspect-video bg-muted rounded border cursor-pointer hover:border-primary transition-colors overflow-hidden"
                      onClick={onPrevious}
                    >
                      {previousImage ? (
                        <ImageWithFallback
                          src={previousImage.thumbnail || '/placeholder-image.png'}
                          alt={previousImage.originalPath}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xs text-muted-foreground">
                          {text.noImage}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* 下一张 */}
                  <div className="space-y-1">
                    <Label className="text-xs text-muted-foreground">{text.nextImageLabel}</Label>
                    <div 
                      className="aspect-video bg-muted rounded border cursor-pointer hover:border-primary transition-colors overflow-hidden"
                      onClick={onNext}
                    >
                      {nextImage ? (
                        <ImageWithFallback
                          src={nextImage.thumbnail || '/placeholder-image.png'}
                          alt={nextImage.originalPath}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-xs text-muted-foreground">
                          {text.noImage}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* 右侧：上下文和候选区域 */}
          <div className="flex-1 flex flex-col">
            <Tabs defaultValue="prev" className="flex-1 flex flex-col">
              {/* Tab 切换 */}
              <div className="border-b px-4 pt-3">
                <TabsList className="w-full grid grid-cols-2">
                  <TabsTrigger value="prev">{text.previousContext}</TabsTrigger>
                  <TabsTrigger value="next">{text.nextContext}</TabsTrigger>
                </TabsList>
              </div>
              
              {/* 上文内容 */}
              <TabsContent value="prev" className="flex-1 flex flex-col m-0 overflow-hidden">
                <div className="p-4 space-y-3 flex-1 flex flex-col overflow-hidden">
                  {/* 字符统计和操作按钮 */}
                  <div className="flex items-center justify-between flex-shrink-0">
                    <span className="text-sm text-muted-foreground">
                      {text.characterCount}: {previousContextText.length}
                    </span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        {text.translate}
                      </Button>
                      <Button variant="outline" size="sm">
                        {text.summarize}
                      </Button>
                    </div>
                  </div>
                  
                  {/* 上文文本内容 */}
                  <ScrollArea className="flex-1 border rounded-lg">
                    <div className="p-3 text-sm whitespace-pre-wrap">
                      {previousContextText}
                    </div>
                  </ScrollArea>
                </div>
              </TabsContent>
              
              {/* 下文内容 */}
              <TabsContent value="next" className="flex-1 flex flex-col m-0 overflow-hidden">
                <div className="p-4 space-y-3 flex-1 flex flex-col overflow-hidden">
                  {/* 字符统计和操作按钮 */}
                  <div className="flex items-center justify-between flex-shrink-0">
                    <span className="text-sm text-muted-foreground">
                      {text.characterCount}: {nextContextText.length}
                    </span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        {text.translate}
                      </Button>
                      <Button variant="outline" size="sm">
                        {text.summarize}
                      </Button>
                    </div>
                  </div>
                  
                  {/* 下文文本内容 */}
                  <ScrollArea className="flex-1 border rounded-lg">
                    <div className="p-3 text-sm whitespace-pre-wrap">
                      {nextContextText}
                    </div>
                  </ScrollArea>
                </div>
              </TabsContent>
            </Tabs>
            
            <Separator />
            
            {/* 候选策略列表 */}
            <div className="p-4 space-y-3 max-h-[40vh] overflow-hidden flex flex-col">
              <Label className="text-sm">{text.candidateStrategies}</Label>
              <ScrollArea className="flex-1">
                <div className="space-y-2 pr-4">
                  {candidates.map((candidate, idx) => (
                    <div
                      key={idx}
                      className={`p-3 border rounded-lg cursor-pointer hover:bg-accent transition-colors ${
                        selectedCandidate === candidate.name ? 'border-primary bg-accent' : ''
                      }`}
                      onClick={() => {
                        setSelectedCandidate(candidate.name);
                        setCustomName(candidate.name);
                      }}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="text-xs">
                              {text.strategy[candidate.strategy as keyof typeof text.strategy] || candidate.strategy}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {text.confidence}: {candidate.confidence.toFixed(2)}
                            </span>
                          </div>
                          <code className="text-sm font-mono">{candidate.name}</code>
                        </div>
                      </div>
                      {candidate.reason && (
                        <p className="text-xs text-muted-foreground mt-2">{candidate.reason}</p>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
            
            <Separator />
            
            {/* 重命名输入和操作按钮 */}
            <div className="p-4 space-y-3 flex-shrink-0 bg-muted/30">
              <div className="space-y-2">
                <Label className="text-sm">{text.renameTo}</Label>
                <Input
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="domain_name_humor"
                  className="font-mono"
                />
              </div>
              
              <div className="flex gap-2">
                <Button className="flex-1" onClick={handleConfirmAndContinue}>
                  {text.confirmAndContinue}
                </Button>
                <Button variant="outline" className="flex-1" onClick={handleConfirmAndClose}>
                  {text.confirmAndClose}
                </Button>
                <Button variant="outline" onClick={onClose}>
                  {text.cancel}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
