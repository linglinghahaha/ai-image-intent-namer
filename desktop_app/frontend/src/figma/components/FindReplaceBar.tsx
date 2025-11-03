import { X, Search, Replace } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Checkbox } from './ui/checkbox';
import { Label } from './ui/label';
import { Badge } from './ui/badge';

interface FindReplaceBarProps {
  onClose: () => void;
  language: 'zh' | 'en';
}

const t = {
  zh: {
    find: '查找',
    replace: '替换',
    replaceAll: '全部替换',
    caseSensitive: '区分大小写',
    regex: '正则表达式',
    wholeWord: '全字匹配',
    matches: '个匹配',
    close: '关闭',
  },
  en: {
    find: 'Find',
    replace: 'Replace',
    replaceAll: 'Replace All',
    caseSensitive: 'Case Sensitive',
    regex: 'Regex',
    wholeWord: 'Whole Word',
    matches: 'matches',
    close: 'Close',
  },
};

export function FindReplaceBar({ onClose, language }: FindReplaceBarProps) {
  const text = t[language];

  return (
    <div className="border-t bg-card p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-sm">{text.find} & {text.replace}</h3>
            <Badge variant="outline">0 {text.matches}</Badge>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-3">
          <div>
            <Input placeholder={text.find} />
          </div>
          <div>
            <Input placeholder={text.replace} />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Checkbox id="case" />
              <Label htmlFor="case" className="text-sm cursor-pointer">
                {text.caseSensitive}
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox id="regex" />
              <Label htmlFor="regex" className="text-sm cursor-pointer">
                {text.regex}
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox id="whole" />
              <Label htmlFor="whole" className="text-sm cursor-pointer">
                {text.wholeWord}
              </Label>
            </div>
          </div>

          <div className="flex gap-2">
            <Button size="sm" variant="outline">
              {text.replace}
            </Button>
            <Button size="sm">
              <Replace className="w-4 h-4 mr-2" />
              {text.replaceAll}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
