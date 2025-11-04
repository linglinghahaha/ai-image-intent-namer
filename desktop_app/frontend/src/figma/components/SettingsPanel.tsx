import { useState } from 'react';
            <Button variant="outline" size="sm" onClick={handleImportFromBackend}>
              <Download className="w-4 h-4 mr-2" />
              {language === "en" ? "Pull From Backend" : "浠庡悗绔鍙?}
            </Button>
            <Button variant="outline" size="sm" onClick={handleSaveAllToBackend}>
              <Upload className="w-4 h-4 mr-2" />
              {language === "en" ? "Save To Backend" : "淇濆瓨鍒板悗绔?}
            </Button>
}
          <Button variant="outline" size="sm" onClick={handleImportFromBackend}>
            <Button variant="outline" size="sm" onClick={handleImportFromBackend}>
              <Download className="w-4 h-4 mr-2" />
              {language === "en" ? "Pull From Backend" : "娴犲骸鎮楃粩顖濐嚢閸?}
            </Button>
            <Button variant="outline" size="sm" onClick={handleSaveAllToBackend}>
              <Upload className="w-4 h-4 mr-2" />
              {language === "en" ? "Save To Backend" : "娣囨繂鐡ㄩ崚鏉挎倵缁?}
            </Button>
            <Download className="w-4 h-4 mr-2" />
            {language === "en" ? "Pull From Backend" : "濞寸姴楠搁幃妤冪博椤栨繍鍤㈤柛?}
          </Button>
          <Button variant="outline" size="sm" onClick={handleSaveAllToBackend}>
            <Upload className="w-4 h-4 mr-2" />
            {language === "en" ? "Save To Backend" : "濞ｅ洦绻傞悺銊╁礆閺夋寧鍊电紒?}
          </Button>
import { useState } from 'react';
import { X, Save, Copy, Trash2, Plus, Settings as SettingsIcon, FileText, Zap, Upload, Download, RotateCcw, CheckCircle, XCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Switch } from './ui/switch';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from './ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';
import { usePresets } from '../hooks/usePresets';
import { useBackend } from '@desktop/hooks/useBackend';
import type { AIPreset, NamingPreset, RuntimePreset, APIConfig } from '../types/presets';
import { toast } from 'sonner';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  language: 'zh' | 'en';
}

const t = {
  zh: {
    title: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮悩鍏哥瑝闂佹寧绋戠€氼參宕?,
    close: '闂備胶顭堢换鎴炵箾婵犲伣?,
    
    // 闂佽绨肩徊缁樼珶閸儱鏄?
    aiModel: 'AI 婵犵妲呴崹顏堝焵椤掆偓绾绢參鍩€?,
    namingRules: '闂備礁鎲＄粙鏍涢崟顖氱畺闁哄洨濮甸崰鍡涙煕閺囥劌浜滈柣?,
    runtimeOptions: '闂佸搫顦弲婊堝礉濮椻偓閵嗕線骞嬮敂鐣屽姷婵犮垼鍩栭崝鎴﹀焵?,
    
    // 闂傚倷绶￠崑鍛潩閵娾晛鏋侀柕鍫濐槸缁犺偐鈧箍鍎辩€氼喚绮?
    selectPreset: '闂傚倷绶￠崑鍕囬幍顔瑰亾濮樸儱濡介柨娑欏姍瀹曠喖顢氶崨顓熸珬',
    saveAs: '闂備礁鎲￠悷杈╃不閹达附鍋ら柕濠忓閳?..',
    duplicate: '濠电姰鍨煎▔娑氱矓閹绢喖鏄?,
    delete: '闂備礁鎲＄敮鐐寸箾閳ь剚绻?,
    reset: '闂傚倷鐒﹁ぐ鍐矓閸洘鍋柛鈩冪☉缁€鍌炴煏婵炵偓娅呴柛?,
    import: '闂佽娴烽弫鎼佸储瑜斿畷?,
    export: '闂佽娴烽弫鎼佸储瑜斿畷?,
    save: '濠电儑绲藉ú锔炬崲閸岀偞鍋?,
    cancel: '闂備礁鎲￠悷锕傛偋濡ゅ啰鐭?,
    
    // AI婵犵妲呴崹顏堝焵椤掆偓绾绢參鍩€椤掑嫷妫戦柟宄邦儔瀹曟粏顦撮柡?
    aiPresetName: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮姀鐘盒曢悗骞垮劚濞?,
    mainApi: '濠?API',
    translationApi: '缂傚倸鍊搁悧濠偽ｉ幒妤佸剨?API',
    summaryApi: '闂備胶顢婃慨銈夆€﹂崼銉ｂ偓?API',
    baseUrl: 'Base URL',
    apiKey: 'API Key',
    model: '婵犵妲呴崹顏堝焵椤掆偓绾绢參鍩€?,
    temperature: 'Temperature',
    maxTokens: '闂備礁鎼悧鍐磻閹炬剚鐔嗛柛顐㈡閸婅鎱ㄩ姀銈嗙厽婵°倐鍋撻柡鍫墴瀵?,
    systemPrompt: '缂傚倷绶￠崹闈涚暦閻㈤潧鍨濇繛宸簻缁犵敻鏌熼柇锕€鏋斿ù鐘崇洴閹?,
    testConnection: '婵犵數鍋炲娆擃敄閸儲鍎婃い鏍ㄧ⊕娴溿倝鏌ｉ幇顓熺稇濠?,
    testing: '婵犵數鍋炲娆擃敄閸儲鍎婃い鏍ㄧ〒閳?..',
    connectionSuccess: '闂佸搫顦弲婵嬪磻閻愬灚鏆滈柟缁㈠枛缁狅綁鏌熼柇锕€澧い?,
    connectionFailed: '闂佸搫顦弲婵嬪磻閻愬灚鏆滈悗娑櫭欢鐐哄级閸偄浜悮?,
    
    // 闂備礁鎲＄粙鏍涢崟顖氱畺闁哄洨濮甸崰鍡涙煕閺囥劌浜滈柣蹇曞枛閹鎷呯粙搴撴寖闂?
    namingPresetName: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮姀鐘盒曢悗骞垮劚濞?,
    template: '闂備礁鎲＄粙鏍涢崟顖氱畺闁哄洨鍊ｉ悢鐓庣労闁告劏鏅濋崙?,
    templatePlaceholder: '濠电偞鎸婚懝楣冾敄閸涙番鈧? {title}_{seq}_{intent}',
    availablePlaceholders: '闂備礁鎲￠悷顖炲垂閹惰棄鏋侀柕鍫濐槸绾偓闂佺粯顭堟禍顒傜矓鐎靛摜纾?,
    templatePresets: '婵犵妲呴崹顏堝礈濠靛棭鐔嗘俊顖欑串缁憋綁鏌涢弴銊ユ珮闁?,
    strategy: '闂備礁鎲＄粙鏍涢崟顖氱畺闁哄洨濮锋す鎶芥煛瀹ュ骸浜濇繛?,
    strategyContext: '闂備胶纭堕弲鐐差浖閵娧嗗С妞ゆ帊鑳堕埢鏂库攽閻樿精鍏岄柣鐔告崌閺?,
    strategyVision: '闂備胶纭堕弲鐐差浖閵娧嗗С妞ゆ帒鍊归崰鍡涙煕閳╁啫鍤繛?,
    strategyHybrid: '婵犵數鍎戠徊浠嬪床閺屻儱绠栭幖绮瑰灳閻旂厧鐏崇€规洖娲ㄩ、?,
    seqWidth: '闂佺懓鍚嬪娆戞崲閹邦垬浜归悹鎭掑妷閸嬫挾娑甸崨顕呮闁?,
    separator: '闂備礁鎲＄敮鎺懳涘┑鍡忔灁鐟滃繒鍒?,
    caseSensitive: '闂備礁鎲￠悧鏇㈠箹椤愶箑鍨傞幖娣灩缁剁偟鎲稿澶嬪剭妞ゆ帒瀚粈?,
    removeSpecialChars: '缂傚倷绀侀ˇ顖炩€﹀畡鎵虫瀺閹兼番鍔嶉崑瀣偡濞嗗繐顏柡鍡樻礋閹鈽夊▎妯荤暭濡?,
    maxLength: '闂備礁鎼悧鍐磻閹炬剚鐔嗛柛顐㈡濞诧箑袙閹版澘绠?,
    preview: '濠碘槅鍋呭妯尖偓姘煎灦閿?,
    insertPlaceholder: '闂備胶绮崝妤呭箠閹捐鍚规い鏇楀亾妤犵偞鎹囬獮鎺楀箣濠靛棙杈?,
    
    // 闂佸搫顦弲婊堝礉濮椻偓閵嗕線骞嬮敂鐣屽姷婵犮垼鍩栭崝鎴﹀焵椤掆偓缁夊爼骞忕€ｎ喖绀堢憸蹇涘几?
    runtimePresetName: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮姀鐘盒曢悗骞垮劚濞?,
    backup: '濠电姰鍨煎▔娑樏洪敐澶婅埞闁靛牆顦崒銊╂煟閺傛寧鍟為柣搴枛闇?,
    vision: '闂備礁鎲￠崙褰掑垂閹惰棄鏋侀柕鍫濇处閸犲棝鏌涢埄鍐ㄥ毈婵炲吋娲熼弻娑㈠箳閹寸儐妫￠梺?,
    attachDir: 'Attachments 闂備胶鍎甸弲鈺呭窗閺嶎偆绀?,
    concurrency: '婵°倗濮烽崑鐘测枖濞戞嚎浜归柛宀€鍋涢弸?,
    retryCount: '闂傚倷鐒﹁ぐ鍐矓閻戣姤鍎婃い鏍ㄥ焹閺嬪酣鏌嶉埡浣告殲婵?,
    timeout: '闂佺儵鍓濈敮鎺楀箠韫囨搩娓婚柛宀€鍋涚猾宥夋煕椤愶絾绀冮柨娑氬枛閺屻劌鈽夊Ο鐓庘叡濡炪値鍋呴〃濠囧极?,
    logLevel: '闂備礁鎼崯銊╁磿鏉堚晜宕查柡鍐ㄥ€诲Λ顖滄喐瀹ュ鏄?,
    autoSave: '闂備胶鍘ч〃搴㈢濠婂嫭鍙忛柍鍝勫€婚埞宥嗙節闂堟稒顥犻柟?,
    
    // 闂佽娴烽弫鎼併€佹繝鍥ㄥ剨闁芥ê顦藉ù?
    saveAsTitle: '闂備礁鎲￠悷杈╃不閹达附鍋ら柕濠忓閳绘棃鏌ｉ幋鐐嗘垿鎮￠埀顒佷繆椤愶絾绶查悗姘煎灦椤?,
    saveAsDescription: '闂佽崵濮村ú銊╁蓟婢跺本顐芥い鎾卞灩缁€鍌炴煏婢舵盯妾柣鎾亾濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮姀鈥冲壄闂佸憡娲﹂崑鍛村磹瀹曞洨纾?,
    presetName: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮姀鐘盒曢悗骞垮劚濞?,
    
    deleteTitle: '缂備胶铏庨崣搴ㄥ窗濞戙埄鏁囧┑鐘宠壘缁€鍡涙煟濡偐甯涢柣?,
    deleteDescription: '缂備胶铏庨崣搴ㄥ窗閺嶎厽鍋╅柛鎾楀嫬鏆繛杈剧悼椤牓鎮橀埡鍛拻闁告洍鏅涢埀顒佺墵椤㈡鈹戦崶椋庣煑闂佸憡娲﹂崳顕€宕惔銊︾厱婵﹩鍙庡▓锝囩磼闁秵娑фい顐犲灲婵″爼宕卞Ο璇插妼濠电偠鎻徊鍓у垝閸垻绠斿鑸靛姇閻銇勯弽銊р姇閻庣數鏁诲鐑樻償閹惧厖澹曢梻?,
    
    resetTitle: '缂備胶铏庨崣搴ㄥ窗濞戙埄鏁囧┑鐘崇閻撳倻鈧箍鍎卞ú銊╁几?,
    resetDescription: '缂備胶铏庨崣搴ㄥ窗閺嶎厽鍋╅柛鎾楀嫬鏆繛鎾村焹閸嬫捇鏌涢敐鍛喐缂佽鲸妫冮、娆撴寠婢舵ɑ娈归梻浣告惈閻楀棝藝閻㈡悶鈧倿鍩￠崘鈺侇€涢梺璇″瀻閸愵亜甯撳┑顔藉笚缁嬫帡鈥﹂崼銉晣濠电姵鑹剧壕褰掓煟閹惧啿顒㈤柛瀣儔閺屻劌鈽夊顒佺€惧銈嗗笚缁诲牓鐛▎蹇ｅ悑闁告洦鍘鹃埢鏇熺箾閹寸偞灏紒澶岊棎閵囨劙寮婚妷銉ь啋闂侀潧鐗嗛ˇ浼村极濮椻偓閺?,
    
    importTitle: '闂佽娴烽弫鎼佸储瑜斿畷锝夊幢濮楀牏鐭楅梺鍛婃处閸ｎ噣宕?,
    importDescription: '缂傚倷绶￠崰妤呪€﹂崼銉ョ婵炴垶鐟辩槐锝夋煕閺囥劌娅橀柛鐔蜂笢SON闂備浇妗ㄩ懗鑸垫櫠濡も偓閻?,
    
    // 闂備礁婀辩划顖炲礉濡ゅ懎桅婵﹩鍘鹃埞宥夋煃閳轰礁鏆曠紒?
    saved: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮悜鍡楁櫊闂傚鍋掗崢鍓х不娴犲鍊?,
    deleted: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮悜鍡楁櫊闂佸湱绮敮鎺楁倶閳哄懏鈷?,
    duplicated: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮悜鍡楁櫊闂佸湱绮敮鈺佄ｆ繝姘厱?,
    resetSuccess: '闂備礁婀遍。浠嬪磻閹剧粯鐓涢柛顐ｇ箥濡偓濡炪倧绲洪弲婵嬪箯鐎ｎ喖绠氱憸宥夊吹閹烘鈷戦柟缁樺笧鑲栭梺?,
    importSuccess: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮悜鍡楁櫊闂佸湱绮敮鈺呭吹閵堝鐓?,
    exportSuccess: '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮悜鍡楁櫊闂佸湱绮敮鈺佄ｆ繝姘厱闁圭儤娲樼涵楣冩煕閳轰胶鐒哥€规洘绮撻、鏃堝炊瑜嶉悘锟犳⒑?,
    invalidJson: '闂備礁鎼崯鐗堟叏閻㈢鐤鹃柕澶嗘櫆閸庡秹鏌涢幋顓熺ON闂備礁鎼粔鍫曞储瑜忓Σ?,
  },
  en: {
    title: 'Preset Manager',
    close: 'Close',
    
    // Navigation
    aiModel: 'AI Model',
    namingRules: 'Naming Rules',
    runtimeOptions: 'Runtime Options',
    
    // Common operations
    selectPreset: 'Select Preset',
    saveAs: 'Save As...',
    duplicate: 'Duplicate',
    delete: 'Delete',
    reset: 'Reset All',
    import: 'Import',
    export: 'Export',
    save: 'Save',
    cancel: 'Cancel',
    
    // AI model settings
    aiPresetName: 'Preset Name',
    mainApi: 'Main API',
    translationApi: 'Translation API',
    summaryApi: 'Summary API',
    baseUrl: 'Base URL',
    apiKey: 'API Key',
    model: 'Model',
    temperature: 'Temperature',
    maxTokens: 'Max Tokens',
    systemPrompt: 'System Prompt',
    testConnection: 'Test Connection',
    testing: 'Testing...',
    connectionSuccess: 'Connection successful',
    connectionFailed: 'Connection failed',
    
    // Naming rules settings
    namingPresetName: 'Preset Name',
    template: 'Template',
    templatePlaceholder: 'e.g., {title}_{seq}_{intent}',
    availablePlaceholders: 'Available Placeholders',
    templatePresets: 'Template Presets',
    strategy: 'Strategy',
    strategyContext: 'Context-based',
    strategyVision: 'Vision-based',
    strategyHybrid: 'Hybrid',
    seqWidth: 'Sequence Width',
    separator: 'Separator',
    caseSensitive: 'Case Sensitive',
    removeSpecialChars: 'Remove Special Chars',
    maxLength: 'Max Length',
    preview: 'Preview',
    insertPlaceholder: 'Click to insert',
    
    // Runtime options settings
    runtimePresetName: 'Preset Name',
    backup: 'Backup Files',
    vision: 'Enable Vision',
    attachDir: 'Attachments Directory',
    concurrency: 'Concurrency',
    retryCount: 'Retry Count',
    timeout: 'Timeout (seconds)',
    logLevel: 'Log Level',
    autoSave: 'Auto Save',
    
    // Dialogs
    saveAsTitle: 'Save as New Preset',
    saveAsDescription: 'Enter a name for the new preset',
    presetName: 'Preset Name',
    
    deleteTitle: 'Confirm Delete',
    deleteDescription: 'Are you sure you want to delete this preset? This action cannot be undone.',
    
    resetTitle: 'Confirm Reset',
    resetDescription: 'Are you sure you want to reset all presets to default? This action cannot be undone.',
    
    importTitle: 'Import Presets',
    importDescription: 'Paste preset JSON data',
    
    // Messages
    saved: 'Preset saved',
    deleted: 'Preset deleted',
    duplicated: 'Preset duplicated',
    resetSuccess: 'All presets reset',
    importSuccess: 'Presets imported',
    exportSuccess: 'Presets copied to clipboard',
    invalidJson: 'Invalid JSON format',
  },
};

// 闂備礁鎲￠〃鍫熸叏瀹曞洨绀婇柛娑卞灣缁犳棃鏌ㄩ弴妤€浜鹃梺浼欑悼閸嬫挾绮?
const placeholders = [
  { key: '{intent}', descZh: 'AI 闂備焦鐪归崹濠氬窗閹版澘鍨傛慨妯垮煐閸庡秹鏌涢弴銊ュ濠㈢懓鐗撻弻?, descEn: 'AI generated intent' },
  { key: '{seq}', descZh: '闂佺懓鍚嬪娆戞崲閹邦垬浜?, descEn: 'Sequence number' },
  { key: '{title}', descZh: '闂備礁鎼崐绋棵洪敃鍌毼ラ柛宀€鍋涢崘鈧梺鎼炲労閸擄箓寮?, descEn: 'Document title' },
  { key: '{date}', descZh: '闂備礁鎼崯銊╁磿閹绘帪鑰?(YYYY-MM-DD)', descEn: 'Date (YYYY-MM-DD)' },
  { key: '{time}', descZh: '闂備礁鎼崯顐︽偉閻撳宫?(HH-MM-SS)', descEn: 'Time (HH-MM-SS)' },
  { key: '{context}', descZh: '濠电偞鍨堕幐鎼佹晝閿濆洨绠旈柛娑欐綑濡﹢鏌涢妷锝呭闁哥姴鎳橀幃?, descEn: 'Context summary' },
  { key: '{file}', descZh: '婵犵數濮嶉崟顐㈩潔闂佸搫顑呴崯顖滅矉閹烘梹宕夐柣鎴灻埀?, descEn: 'Source file name' },
  { key: '{original}', descZh: '闂備礁鎲￠…鍥窗鎼搭煉缍栭柟鐗堟緲閻愬﹪鏌涢幘妤€鍠氶弳顒勬⒑?, descEn: 'Original image name' },
];

// 婵犵妲呴崹顏堝礈濠靛棭鐔嗘俊顖欑串缁憋綁鏌涢弴銊ユ珮闁?
const templatePresets = [
  { nameZh: '闂備浇顫夊妯兼崲閹邦優鐟邦潡閹达箑绠归柡澶嬪灩缁犳壆鎲?, nameEn: 'Intent + Seq', template: '{intent}_{seq}', exampleZh: '闂備線娼绘俊鍥磿閵堝應鏋嶆繛鍡樻尭缁犵敻鐓崶銊ㄥ闁绘鐡?01.png', exampleEn: 'scene_description_001.png' },
  { nameZh: '闂備礁鎼粔鏉懨洪顫偓鍌滃緤閺嶎厼绠归柡澶嬪灩缁犳壆鎲搁幍顔剧懝闂備浇顫夊妯兼崲閹邦優?, nameEn: 'Title + Seq + Intent', template: '{title}_{seq}_{intent}', exampleZh: '闂備礁鎼崐绋棵洪敃鍌毼ュǎ?01_闂備線娼绘俊鍥磿閵堝應鏋嶆繛鍡樻尭缁犵敻鐓崶銊ㄥ闁?png', exampleEn: 'document_001_scene_description.png' },
  { nameZh: '闂備礁鎼崯銊╁磿閹绘帪鑰挎い掳鍎甸弻鐔煎级鐠恒劎顔囧┑?, nameEn: 'Date + Intent', template: '{date}_{intent}', exampleZh: '2025-11-02_闂備線娼绘俊鍥磿閵堝應鏋嶆繛鍡樻尭缁犵敻鐓崶銊ㄥ闁?png', exampleEn: '2025-11-02_scene_description.png' },
  { nameZh: '濠电偞鍨堕幐鎼佹晝閿濆洨绠旈柛娑欐綑濡﹢鏌涢姀銈嗘暠闁诡垱妫佺粻娑㈠箻閸愭祴鏋?, nameEn: 'Context + Seq', template: '{context}_{seq}', exampleZh: '缂傚倷鐒﹂〃蹇涘礂濞戞氨鍗氶悗闈涙憸閸楁岸鏌ｅΟ澶稿惈闁活厽鐟х槐鎾存媴閸濄儯鈧?01.png', exampleEn: 'chapter1_intro_001.png' },
];

type Tab = 'ai' | 'naming' | 'runtime';

export function SettingsPanel({ isOpen, onClose, language }: SettingsPanelProps) {
  const text = t[language];
  const {
    presets,
    addAIPreset,
    updateAIPreset,
    deleteAIPreset,
    duplicateAIPreset,
    addNamingPreset,
    updateNamingPreset,
    deleteNamingPreset,
    duplicateNamingPreset,
    addRuntimePreset,
    updateRuntimePreset,
    deleteRuntimePreset,
    duplicateRuntimePreset,
    resetAllPresets,
    importPresets,
    exportPresets,
  } = usePresets();
  const { client, backendReachable } = useBackend();
  const { client, backendReachable } = useBackend();

  const [activeTab, setActiveTab] = useState<Tab>('ai');
  
  // 闁荤喐绮庢晶妤呭箰閸涘﹥娅犻柣妯肩帛閻掕顭跨捄渚Ъ闁告﹩鍓熼弻锝夊Ω閵夈儺浼冨銈忕岛閺呮繈骞忕€ｎ剛绀婃い?- 缂備胶铏庨崣搴ㄥ窗閺囩姵宕叉慨妯挎硾鐎氬顭块懜闈涘閻㈩垱鐩幃瑙勬媴闂堟稈鍋撻弴銏犵劦?
  const [selectedAIPresetId, setSelectedAIPresetId] = useState(() => {
    return presets.ai.length > 0 ? presets.ai[0].id : '';
  });
  const [selectedNamingPresetId, setSelectedNamingPresetId] = useState(() => {
    return presets.naming.length > 0 ? presets.naming[0].id : '';
  });
  const [selectedRuntimePresetId, setSelectedRuntimePresetId] = useState(() => {
    return presets.runtime.length > 0 ? presets.runtime[0].id : '';
  });
  
  // 闂佽娴烽弫鎼併€佹繝鍥ㄥ剨闁芥ê顦藉ù鏍煕閳╁啰鎳冪粭鎴︽⒑?
  const [saveAsDialogOpen, setSaveAsDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');
  const [importJson, setImportJson] = useState('');
  
  // 缂傚倸鍊搁崐褰掓偋閻愬灚顐芥い鎰剁悼閳绘梹銇勯幘璺盒ｉ柣锝呭船铻為柡澶婄仢椤忣剚銇勯弮鈧ú鐔奉嚕椤愶附鍋嬮柛顐ｇ箘閵?- 缂備胶铏庨崣搴ㄥ窗閺囩姵宕叉慨妯挎硾缁€鍡樼節闂堟稒锛嶆繛鍏碱殜閺屾盯寮介妸褍顫у銈嗗笚缁骸鈽?
  const [editingAIPreset, setEditingAIPreset] = useState<AIPreset | null>(() => {
    const preset = presets.ai.find(p => p.id === (presets.ai[0]?.id || ''));
    return preset || null;
  });
  const [editingNamingPreset, setEditingNamingPreset] = useState<NamingPreset | null>(() => {
    const preset = presets.naming.find(p => p.id === (presets.naming[0]?.id || ''));
    return preset || null;
  });
  const [editingRuntimePreset, setEditingRuntimePreset] = useState<RuntimePreset | null>(() => {
    const preset = presets.runtime.find(p => p.id === (presets.runtime[0]?.id || ''));
    return preset || null;
  });

  // 闁荤喐绮庢晶妤呭箲閸ヮ剙鐒垫い鎺嗗亾妞わ附澹嗛埀顒佸搸閸旀垵顕ｉ妸鈺傚仭闁哄娉曠粔顕€姊洪崫鍕殺闁糕晜鐗曠叅闁秆勵殔濡﹢鏌熷▓鍨灓婵＄偘绮欏鍫曞醇閻旈浠梺鐓庣仛閸ㄥ潡骞嗛崘顔肩妞ゆ帊鐒﹂宥夋⒑?
  const handleAIPresetSelect = (id: string) => {
    setSelectedAIPresetId(id);
    const preset = presets.ai.find(p => p.id === id);
    if (preset) setEditingAIPreset(preset);
  };

  const handleNamingPresetSelect = (id: string) => {
    setSelectedNamingPresetId(id);
    const preset = presets.naming.find(p => p.id === id);
    if (preset) setEditingNamingPreset(preset);
  };

  const handleRuntimePresetSelect = (id: string) => {
    setSelectedRuntimePresetId(id);
    const preset = presets.runtime.find(p => p.id === id);
    if (preset) setEditingRuntimePreset(preset);
  };

  // 濠电姰鍨煎▔娑氣偓姘煎櫍楠炲啯绻濋崶褏鐓戦梺鎸庢磵閸嬫捇鏌ｆ幊閸斿秶绮?
  const handleSaveAs = () => {
    if (!newPresetName.trim()) return;
    
    if (activeTab === 'ai' && editingAIPreset) {
      const { id, ...preset } = editingAIPreset;
      const newPreset = addAIPreset({ ...preset, name: newPresetName });
      setSelectedAIPresetId(newPreset.id);
      setEditingAIPreset(newPreset);
    } else if (activeTab === 'naming' && editingNamingPreset) {
      const { id, ...preset } = editingNamingPreset;
      const newPreset = addNamingPreset({ ...preset, name: newPresetName });
      setSelectedNamingPresetId(newPreset.id);
      setEditingNamingPreset(newPreset);
    } else if (activeTab === 'runtime' && editingRuntimePreset) {
      const { id, ...preset } = editingRuntimePreset;
      const newPreset = addRuntimePreset({ ...preset, name: newPresetName });
      setSelectedRuntimePresetId(newPreset.id);
      setEditingRuntimePreset(newPreset);
    }
    
    setSaveAsDialogOpen(false);
    setNewPresetName('');
    toast.success(text.saved);
  };

  // 濠电姰鍨煎▔娑氣偓姘煎櫍楠炲啯绻濋崶褏顦梺缁橆焽缁垶鎮?
  const handleDelete = () => {
    if (activeTab === 'ai' && selectedAIPresetId) {
      deleteAIPreset(selectedAIPresetId);
      const remaining = presets.ai.filter(p => p.id !== selectedAIPresetId);
      if (remaining.length > 0) {
        setSelectedAIPresetId(remaining[0].id);
        setEditingAIPreset(remaining[0]);
      }
    } else if (activeTab === 'naming' && selectedNamingPresetId) {
      deleteNamingPreset(selectedNamingPresetId);
      const remaining = presets.naming.filter(p => p.id !== selectedNamingPresetId);
      if (remaining.length > 0) {
        setSelectedNamingPresetId(remaining[0].id);
        setEditingNamingPreset(remaining[0]);
      }
    } else if (activeTab === 'runtime' && selectedRuntimePresetId) {
      deleteRuntimePreset(selectedRuntimePresetId);
      const remaining = presets.runtime.filter(p => p.id !== selectedRuntimePresetId);
      if (remaining.length > 0) {
        setSelectedRuntimePresetId(remaining[0].id);
        setEditingRuntimePreset(remaining[0]);
      }
    }
    
    setDeleteDialogOpen(false);
    toast.success(text.deleted);
  };

  // 濠电姰鍨煎▔娑氣偓姘煎櫍楠炲啯绻濋崘銊х獮閻庡箍鍎遍幊搴ㄦ偂?
  const handleDuplicate = () => {
    if (activeTab === 'ai' && selectedAIPresetId) {
      const newPreset = duplicateAIPreset(selectedAIPresetId);
      if (newPreset) {
        setSelectedAIPresetId(newPreset.id);
        setEditingAIPreset(newPreset);
      }
    } else if (activeTab === 'naming' && selectedNamingPresetId) {
      const newPreset = duplicateNamingPreset(selectedNamingPresetId);
      if (newPreset) {
        setSelectedNamingPresetId(newPreset.id);
        setEditingNamingPreset(newPreset);
      }
    } else if (activeTab === 'runtime' && selectedRuntimePresetId) {
      const newPreset = duplicateRuntimePreset(selectedRuntimePresetId);
      if (newPreset) {
        setSelectedRuntimePresetId(newPreset.id);
        setEditingRuntimePreset(newPreset);
      }
    }
    
    toast.success(text.duplicated);
  };

  // 濠电姰鍨煎▔娑氣偓姘煎櫍楠炲啯绻濋崟銊ヤ壕闁汇垽娼х敮鍫曟煕?
  const handleExport = () => {
    const json = exportPresets();
    navigator.clipboard.writeText(json);
    toast.success(text.exportSuccess);
  };

  // Backend profiles/templates sync
  function aiPresetFromProfile(name: string, p: any): AIPreset {
    const baseUrl = String(p?.base_url ?? p?.baseUrl ?? '');
    const apiKey = String(p?.api_key ?? p?.apiKey ?? '');
    const model = String(p?.model ?? 'gpt-4');
    const temperature = Number(p?.temperature ?? 0.7);
    const maxTokens = Number(p?.max_tokens ?? p?.maxTokens ?? 2000);
    const base: APIConfig = {
      baseUrl,
      apiKey,
      model,
      systemPrompt: 'You are an AI assistant that helps name images based on their content and context.',
    };
    return {
      id: `ai-backend-${name}`,
      name,
      mainApi: base,
      translationApi: { ...base },
      summaryApi: { ...base },
      temperature,
      maxTokens,
    } as AIPreset;
  }

  function namingPresetFromTemplate(name: string, t: any): NamingPreset {
    const template = String(t?.template ?? '{title}_{index:02d}_{intent}');
    return {
      id: `naming-backend-${name}`,
      name,
      template,
      strategy: 'context',
      seqWidth: 2,
      separator: '_',
      caseSensitive: false,
      removeSpecialChars: true,
      maxLength: 100,
    } as NamingPreset;
  }

  async function handleImportFromBackend() {
    if (!backendReachable) {
      toast.warning(language === 'en' ? 'Backend not connected' : '后端未连接');
      return;
    }
    try {
      const profiles = await client.listProfiles();
      const templates = await client.listTemplates();
      const ai: AIPreset[] = Object.entries(profiles || {}).map(([k, v]) => aiPresetFromProfile(k, v));
      const naming: NamingPreset[] = Object.entries(templates || {}).map(([k, v]) => namingPresetFromTemplate(k, v));
      importPresets({ ai, naming });
      toast.success(language === 'en' ? 'Imported from backend' : '已从后端导入');
    } catch (e) {
      toast.error((language === 'en' ? 'Import failed: ' : '导入失败：') + (e as Error).message);
    }
  }

  function profilePayloadFromAIPreset(p: AIPreset) {
    return {
      base_url: p.mainApi.baseUrl,
      api_key: p.mainApi.apiKey,
      model: p.mainApi.model,
      temperature: p.temperature ?? 0.7,
      max_tokens: p.maxTokens ?? 2000,
      timeout: 30,
      attach_dir: './attachments',
    } as Record<string, unknown>;
  }
  function templatePayloadFromNamingPreset(n: NamingPreset) {
    return { template: n.template, description: n.name } as Record<string, unknown>;
  }

  async function handleSaveAllToBackend() {
    if (!backendReachable) {
      toast.warning(language === 'en' ? 'Backend not connected' : '后端未连接');
      return;
    }
    try {
      for (const p of presets.ai) {
        const name = p.name?.trim() || p.id;
        await client.saveProfile(name, profilePayloadFromAIPreset(p));
      }
      for (const n of presets.naming) {
        const name = n.name?.trim() || n.id;
        await client.saveTemplate(name, templatePayloadFromNamingPreset(n));
      }
      toast.success(language === 'en' ? 'Saved to backend' : '已保存到后端');
    } catch (e) {
      toast.error((language === 'en' ? 'Save failed: ' : '保存失败：') + (e as Error).message);
    }
  }

  // 濠电姰鍨煎▔娑氣偓姘煎櫍楠炲啯绻濋崟銊ヤ壕闁汇垽娼х敮鍫曟煕?
  const handleImport = () => {
    try {
      const parsed = JSON.parse(importJson);
      importPresets(parsed);
      setImportDialogOpen(false);
      setImportJson('');
      toast.success(text.importSuccess);
      
      // 闂傚倷鐒﹁ぐ鍐矓閻㈢钃熷┑鐘叉处閻掕顭跨捄渚剰妞ゅ繈鍎崇槐鎺懳旀繝鍌氬箰缂備焦鏌ㄩ悺銊х矙婢舵劦鏁傞柛顐亝濞堛劑鏌?
      if (presets.ai.length > 0) {
        setSelectedAIPresetId(presets.ai[0].id);
        setEditingAIPreset(presets.ai[0]);
      }
      if (presets.naming.length > 0) {
        setSelectedNamingPresetId(presets.naming[0].id);
        setEditingNamingPreset(presets.naming[0]);
      }
      if (presets.runtime.length > 0) {
        setSelectedRuntimePresetId(presets.runtime[0].id);
        setEditingRuntimePreset(presets.runtime[0]);
      }
    } catch (error) {
      toast.error(text.invalidJson);
    }
  };

  // 濠电姰鍨煎▔娑氣偓姘煎櫍楠炲啯绻濋崶銊у帓閻庡箍鍎卞ú銊╁几?
  const handleReset = () => {
    resetAllPresets();
    setResetDialogOpen(false);
    
    // 闂傚倷鐒﹁ぐ鍐矓閻㈢钃熷┑鐘叉处閻掕顭跨捄渚剰妞ゅ繈鍎崇槐鎺懳旀繝鍌氬箰缂備焦鏌ㄩ悺銊х矙婢舵劦鏁傞柛顐亝濞堛劑鏌?
    if (presets.ai.length > 0) {
      setSelectedAIPresetId(presets.ai[0].id);
      setEditingAIPreset(presets.ai[0]);
    }
    if (presets.naming.length > 0) {
      setSelectedNamingPresetId(presets.naming[0].id);
      setEditingNamingPreset(presets.naming[0]);
    }
    if (presets.runtime.length > 0) {
      setSelectedRuntimePresetId(presets.runtime[0].id);
      setEditingRuntimePreset(presets.runtime[0]);
    }
    
    toast.success(text.resetSuccess);
  };

  // 濠电儑绲藉ú锔炬崲閸岀偞鍋ら柕濞垮妸娴滃綊鏌熼幆褍鏆辨い銈呮噽缁辨捇宕掑☉姘拪缂?
  const handleSaveCurrent = () => {
    if (activeTab === 'ai' && editingAIPreset) {
      updateAIPreset(editingAIPreset.id, editingAIPreset);
    } else if (activeTab === 'naming' && editingNamingPreset) {
      updateNamingPreset(editingNamingPreset.id, editingNamingPreset);
    } else if (activeTab === 'runtime' && editingRuntimePreset) {
      updateRuntimePreset(editingRuntimePreset.id, editingRuntimePreset);
    }
    toast.success(text.saved);
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-full max-w-5xl bg-background border-l shadow-lg z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl">{text.title}</h2>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleImportFromBackend}>
              <Download className="w-4 h-4 mr-2" />
              {language === "en" ? "Pull From Backend" : "从后端读取"}
            </Button>
            <Button variant="outline" size="sm" onClick={handleSaveAllToBackend}>
              <Upload className="w-4 h-4 mr-2" />
              {language === "en" ? "Save To Backend" : "保存到后端"}
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="w-4 h-4 mr-2" />
              {text.export}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setImportDialogOpen(true)}>
              <Upload className="w-4 h-4 mr-2" />
              {text.import}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setResetDialogOpen(true)}>
              <RotateCcw className="w-4 h-4 mr-2" />
              {text.reset}
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs Navigation */}
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as Tab)} className="flex-1 flex flex-col">
            <div className="border-b px-6">
              <TabsList className="w-full justify-start">
                <TabsTrigger value="ai" className="flex items-center gap-2">
                  <SettingsIcon className="w-4 h-4" />
                  {text.aiModel}
                </TabsTrigger>
                <TabsTrigger value="naming" className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  {text.namingRules}
                </TabsTrigger>
                <TabsTrigger value="runtime" className="flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  {text.runtimeOptions}
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Preset Selector and Actions */}
            <div className="px-6 py-4 border-b">
              <div className="flex gap-2">
                {activeTab === 'ai' && (
                  <Select value={selectedAIPresetId} onValueChange={handleAIPresetSelect}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder={text.selectPreset} />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.ai.map(preset => (
                        <SelectItem key={preset.id} value={preset.id}>
                          {preset.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                {activeTab === 'naming' && (
                  <Select value={selectedNamingPresetId} onValueChange={handleNamingPresetSelect}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder={text.selectPreset} />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.naming.map(preset => (
                        <SelectItem key={preset.id} value={preset.id}>
                          {preset.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                {activeTab === 'runtime' && (
                  <Select value={selectedRuntimePresetId} onValueChange={handleRuntimePresetSelect}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder={text.selectPreset} />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.runtime.map(preset => (
                        <SelectItem key={preset.id} value={preset.id}>
                          {preset.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                
                <Button variant="default" size="sm" onClick={handleSaveCurrent}>
                  <Save className="w-4 h-4 mr-2" />
                  {text.save}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setSaveAsDialogOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  {text.saveAs}
                </Button>
                <Button variant="outline" size="sm" onClick={handleDuplicate}>
                  <Copy className="w-4 h-4 mr-2" />
                  {text.duplicate}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setDeleteDialogOpen(true)}>
                  <Trash2 className="w-4 h-4 mr-2" />
                  {text.delete}
                </Button>
              </div>
            </div>

            {/* Tab Content */}
            <TabsContent value="ai" className="flex-1 m-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-6">
                  {editingAIPreset && (
                    <AIPresetForm
                      preset={editingAIPreset}
                      onChange={setEditingAIPreset}
                      language={language}
                    />
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="naming" className="flex-1 m-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-6">
                  {editingNamingPreset && (
                    <NamingPresetForm
                      preset={editingNamingPreset}
                      onChange={setEditingNamingPreset}
                      language={language}
                    />
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="runtime" className="flex-1 m-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-6">
                  {editingRuntimePreset && (
                    <RuntimePresetForm
                      preset={editingRuntimePreset}
                      onChange={setEditingRuntimePreset}
                      language={language}
                    />
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Dialogs */}
      <Dialog open={saveAsDialogOpen} onOpenChange={setSaveAsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{text.saveAsTitle}</DialogTitle>
            <DialogDescription>{text.saveAsDescription}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{text.presetName}</Label>
              <Input
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
                placeholder={text.presetName}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveAsDialogOpen(false)}>
              {text.cancel}
            </Button>
            <Button onClick={handleSaveAs}>
              {text.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{text.deleteTitle}</AlertDialogTitle>
            <AlertDialogDescription>{text.deleteDescription}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{text.cancel}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>{text.delete}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{text.resetTitle}</AlertDialogTitle>
            <AlertDialogDescription>{text.resetDescription}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{text.cancel}</AlertDialogCancel>
            <AlertDialogAction onClick={handleReset}>{text.reset}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{text.importTitle}</DialogTitle>
            <DialogDescription>{text.importDescription}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Textarea
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              placeholder='{"ai": [...], "naming": [...], "runtime": [...]}'
              className="font-mono text-sm min-h-[300px]"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setImportDialogOpen(false)}>
              {text.cancel}
            </Button>
            <Button onClick={handleImport}>
              {text.import}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// AI濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮悩鍐蹭粧闂侀潧顭堥崕杈╃矆?- 闂備浇妗ㄩ悞锕€顭囧▎鎾崇畺閹兼番鍨婚々鏌ユ煕濠婂孩鐝婭闂傚倷鐒﹀妯肩矓閸洘鍋柛鈩冾焽閳绘梹銇勯幘璺轰户濠碘€虫喘閺岋綁濡搁妷銉还缂備焦銇為悞锔剧矙婢舵劖鍋戞繝鏇炲剱
function AIPresetForm({ preset, onChange, language }: {
  preset: AIPreset;
  onChange: (preset: AIPreset) => void;
  language: 'zh' | 'en';
}) {
  const text = t[language];
  const [testingApi, setTestingApi] = useState<'main' | 'translation' | 'summary' | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<{[key: string]: 'idle' | 'success' | 'error'}>({});
  
  // 缂備胶铏庨崣搴ㄥ窗閺囩姵宕叉慨婵堟箷eset闂備礁鎼悧鍡浰囨导鎼晢婵犲﹤鎳忛崗婊勩亜閺冨倸浜鹃柣锝堜含缁辨挻鎷呯憴鍕瀺闂?
  if (!preset || !preset.mainApi || !preset.translationApi || !preset.summaryApi) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        {language === 'zh' ? '濠碘槅鍋呭妯尖偓姘煎灦椤㈡瑩寮撮姀鐘崇€梺缁橆殔閻楀棛绮婇敃鍌涚厸闁告劦浜滄牎闂佸搫鎳岄崕鐢稿极瀹ュ懐鏆嗛柛鎰劤濞堟煡姊绘担鐟扮祷缂佸鐖奸幃鍧楀幢濮楀牏鐭楅梺鍛婃处閸ｎ噣宕惔銊︾厪? : 'Invalid preset data, please reset presets.'}
      </div>
    );
  }
  
  const handleTestConnection = async (apiType: 'main' | 'translation' | 'summary') => {
    setTestingApi(apiType);
    
    // 婵犵妲呴崹顏堝礈濠靛牃鍋撳顓犳噧闂囧鎮楅敐搴″箻婵″弶鎮傚鍫曞煛閸愩劋娌柣?
    setTimeout(() => {
      const success = Math.random() > 0.3; // 70% 闂備胶鎳撻悺銊╁礉閺囩喐鍙忔繛鎴欏灪閸?
      setConnectionStatus(prev => ({ ...prev, [apiType]: success ? 'success' : 'error' }));
      setTestingApi(null);
      
      if (success) {
        toast.success(text.connectionSuccess);
      } else {
        toast.error(text.connectionFailed);
      }
    }, 2000);
  };

  const updateAPIConfig = (apiType: 'mainApi' | 'translationApi' | 'summaryApi', updates: Partial<APIConfig>) => {
    onChange({
      ...preset,
      [apiType]: { ...preset[apiType], ...updates }
    });
  };
  
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>{text.aiPresetName}</Label>
        <Input
          value={preset.name}
          onChange={(e) => onChange({ ...preset, name: e.target.value })}
        />
      </div>
      
      <Separator />

      {/* 濠电偞鍨堕幐楣冩儑閻闂備線娼уΛ鏃堟嚄閸洘鍊烽柡鍥╁У鐎氭岸鏌熼崡鐑嗘晢I闂備線娼уΛ鏃堟倿閿曞倸绠熺€规洖娲﹂崯鍝勨槈閹惧啿娈糏 濠电偞鍨堕幐鎼佀囬鈧弻灞角庨悹顩?*/}
      <Tabs defaultValue="main" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="main">{text.mainApi}</TabsTrigger>
          <TabsTrigger value="translation">{text.translationApi}</TabsTrigger>
          <TabsTrigger value="summary">{text.summaryApi}</TabsTrigger>
        </TabsList>

        {/* 濠电偞鍨堕幐楣冩儑閻 */}
        <TabsContent value="main" className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label>{text.baseUrl}</Label>
            <Input
              value={preset.mainApi.baseUrl}
              onChange={(e) => updateAPIConfig('mainApi', { baseUrl: e.target.value })}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.apiKey}</Label>
            <Input
              type="password"
              value={preset.mainApi.apiKey}
              onChange={(e) => updateAPIConfig('mainApi', { apiKey: e.target.value })}
              placeholder="sk-..."
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.model}</Label>
            <Input
              value={preset.mainApi.model}
              onChange={(e) => updateAPIConfig('mainApi', { model: e.target.value })}
              placeholder="gpt-4"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.systemPrompt}</Label>
            <Textarea
              value={preset.mainApi.systemPrompt || ''}
              onChange={(e) => updateAPIConfig('mainApi', { systemPrompt: e.target.value })}
              placeholder="You are a helpful assistant..."
              rows={6}
            />
          </div>
          
          <Button 
            onClick={() => handleTestConnection('main')} 
            disabled={testingApi === 'main'}
            variant="outline"
            className="w-full"
          >
            {testingApi === 'main' ? (
              <>
                <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                {text.testing}
              </>
            ) : connectionStatus.main === 'success' ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                {text.connectionSuccess}
              </>
            ) : connectionStatus.main === 'error' ? (
              <>
                <XCircle className="w-4 h-4 mr-2 text-red-500" />
                {text.connectionFailed}
              </>
            ) : (
              <>
                <SettingsIcon className="w-4 h-4 mr-2" />
                {text.testConnection}
              </>
            )}
          </Button>
        </TabsContent>

        {/* 缂傚倸鍊搁悧濠偽ｉ幒妤佸剨妞ゎ亜妲 */}
        <TabsContent value="translation" className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label>{text.baseUrl}</Label>
            <Input
              value={preset.translationApi.baseUrl}
              onChange={(e) => updateAPIConfig('translationApi', { baseUrl: e.target.value })}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.apiKey}</Label>
            <Input
              type="password"
              value={preset.translationApi.apiKey}
              onChange={(e) => updateAPIConfig('translationApi', { apiKey: e.target.value })}
              placeholder="sk-..."
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.model}</Label>
            <Input
              value={preset.translationApi.model}
              onChange={(e) => updateAPIConfig('translationApi', { model: e.target.value })}
              placeholder="gpt-3.5-turbo"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.systemPrompt}</Label>
            <Textarea
              value={preset.translationApi.systemPrompt || ''}
              onChange={(e) => updateAPIConfig('translationApi', { systemPrompt: e.target.value })}
              placeholder="Translate the following text to {target_language}."
              rows={6}
            />
          </div>
          
          <Button 
            onClick={() => handleTestConnection('translation')} 
            disabled={testingApi === 'translation'}
            variant="outline"
            className="w-full"
          >
            {testingApi === 'translation' ? (
              <>
                <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                {text.testing}
              </>
            ) : connectionStatus.translation === 'success' ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                {text.connectionSuccess}
              </>
            ) : connectionStatus.translation === 'error' ? (
              <>
                <XCircle className="w-4 h-4 mr-2 text-red-500" />
                {text.connectionFailed}
              </>
            ) : (
              <>
                <SettingsIcon className="w-4 h-4 mr-2" />
                {text.testConnection}
              </>
            )}
          </Button>
        </TabsContent>

        {/* 闂備胶顢婃慨銈夆€﹂崼銉ｂ偓鍛淬€冮—鏈?*/}
        <TabsContent value="summary" className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label>{text.baseUrl}</Label>
            <Input
              value={preset.summaryApi.baseUrl}
              onChange={(e) => updateAPIConfig('summaryApi', { baseUrl: e.target.value })}
              placeholder="https://api.openai.com/v1"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.apiKey}</Label>
            <Input
              type="password"
              value={preset.summaryApi.apiKey}
              onChange={(e) => updateAPIConfig('summaryApi', { apiKey: e.target.value })}
              placeholder="sk-..."
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.model}</Label>
            <Input
              value={preset.summaryApi.model}
              onChange={(e) => updateAPIConfig('summaryApi', { model: e.target.value })}
              placeholder="gpt-3.5-turbo"
            />
          </div>
          
          <div className="space-y-2">
            <Label>{text.systemPrompt}</Label>
            <Textarea
              value={preset.summaryApi.systemPrompt || ''}
              onChange={(e) => updateAPIConfig('summaryApi', { systemPrompt: e.target.value })}
              placeholder="Summarize the following text concisely."
              rows={6}
            />
          </div>
          
          <Button 
            onClick={() => handleTestConnection('summary')} 
            disabled={testingApi === 'summary'}
            variant="outline"
            className="w-full"
          >
            {testingApi === 'summary' ? (
              <>
                <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                {text.testing}
              </>
            ) : connectionStatus.summary === 'success' ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                {text.connectionSuccess}
              </>
            ) : connectionStatus.summary === 'error' ? (
              <>
                <XCircle className="w-4 h-4 mr-2 text-red-500" />
                {text.connectionFailed}
              </>
            ) : (
              <>
                <SettingsIcon className="w-4 h-4 mr-2" />
                {text.testConnection}
              </>
            )}
          </Button>
        </TabsContent>
      </Tabs>

      <Separator />
      
      {/* 闂傚倷绶￠崑鍛潩閵娾晛鏋侀柕鍫濐槸閻鏌涚仦鍓р姇婵?*/}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{text.temperature}</Label>
          <Input
            type="number"
            step="0.1"
            min="0"
            max="2"
            value={preset.temperature || 0.7}
            onChange={(e) => onChange({ ...preset, temperature: parseFloat(e.target.value) })}
          />
        </div>
        
        <div className="space-y-2">
          <Label>{text.maxTokens}</Label>
          <Input
            type="number"
            value={preset.maxTokens || 2000}
            onChange={(e) => onChange({ ...preset, maxTokens: parseInt(e.target.value) })}
          />
        </div>
      </div>
    </div>
  );
}

// 闂備礁鎲＄粙鏍涢崟顖氱畺闁哄洨濮甸崰鍡涙煕閺囥劌浜滈柣蹇曞枎铻為柡澶婄仢椤忣剚銇勯弮鈧ú婊堝箖娴兼潙惟闁靛鍎抽ˇ?- 闂備浇妗ㄩ悞锕€顭囧▎鎾崇畺閹兼番鍨婚々鏌ユ煕閳╁啠妫╁〒姘ｅ亾鐎殿喖鐖煎畷褰掝敊婢惰锕㈤弻?
function NamingPresetForm({ preset, onChange, language }: {
  preset: NamingPreset;
  onChange: (preset: NamingPreset) => void;
  language: 'zh' | 'en';
}) {
  const text = t[language];
  
  const handleInsertPlaceholder = (placeholder: string) => {
    const currentTemplate = preset.template || '';
    onChange({ ...preset, template: currentTemplate + placeholder });
  };
  
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>{text.namingPresetName}</Label>
        <Input
          value={preset.name}
          onChange={(e) => onChange({ ...preset, name: e.target.value })}
        />
      </div>
      
      <Separator />
      
      <div className="grid grid-cols-3 gap-6">
        {/* 闁诲骸缍婂鑽ょ磽濮樿泛鐤鹃柛顐ｆ礃閺咁剚鎱ㄥ鍡楀Ш濞撴埃鍋撶€殿喖澧庨幑鍕Ω瑜庨妵婵嬫煛?*/}
        <div className="col-span-2 space-y-4">
          <div className="space-y-2">
            <Label>{text.template}</Label>
            <Textarea
              value={preset.template}
              onChange={(e) => onChange({ ...preset, template: e.target.value })}
              placeholder={text.templatePlaceholder}
              rows={3}
            />
          </div>
          
          {/* 闂備礁鎲￠〃鍫熸叏瀹曞洨绀婇柛娑卞灣缁犳棃鏌ㄩ弴妤€浜鹃梺鍓茬厛娴滅偤骞?*/}
          <div>
            <Label className="mb-2 block">{text.availablePlaceholders}</Label>
            <p className="text-xs text-muted-foreground mb-2">{text.insertPlaceholder}</p>
            <div className="grid grid-cols-2 gap-2">
              {placeholders.map((ph) => (
                <Card 
                  key={ph.key} 
                  className="p-2 hover:bg-accent/50 cursor-pointer transition-colors" 
                  onClick={() => handleInsertPlaceholder(ph.key)}
                >
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <code className="text-xs bg-muted px-2 py-1 rounded block truncate">
                        {ph.key}
                      </code>
                      <p className="text-xs text-muted-foreground mt-1">
                        {language === 'zh' ? ph.descZh : ph.descEn}
                      </p>
                    </div>
                    <Plus className="w-3 h-3 shrink-0 mt-1" />
                  </div>
                </Card>
              ))}
            </div>
          </div>
          
          {/* 闂備胶顭堢换鎴濓耿閸︻厼鍨濇い鎺戝€规刊濂告煕閹炬鎳忛悗?*/}
          <div className="space-y-2">
            <Label>{text.strategy}</Label>
            <Select 
              value={preset.strategy} 
              onValueChange={(value: any) => onChange({ ...preset, strategy: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="context">{text.strategyContext}</SelectItem>
                <SelectItem value="vision">{text.strategyVision}</SelectItem>
                <SelectItem value="hybrid">{text.strategyHybrid}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{text.seqWidth}</Label>
              <Input
                type="number"
                min="0"
                max="10"
                value={preset.seqWidth}
                onChange={(e) => onChange({ ...preset, seqWidth: parseInt(e.target.value) })}
              />
            </div>
            
            <div className="space-y-2">
              <Label>{text.separator}</Label>
              <Input
                value={preset.separator}
                onChange={(e) => onChange({ ...preset, separator: e.target.value })}
                maxLength={3}
              />
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>{text.caseSensitive}</Label>
              <Switch
                checked={preset.caseSensitive}
                onCheckedChange={(checked) => onChange({ ...preset, caseSensitive: checked })}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <Label>{text.removeSpecialChars}</Label>
              <Switch
                checked={preset.removeSpecialChars}
                onCheckedChange={(checked) => onChange({ ...preset, removeSpecialChars: checked })}
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label>{text.maxLength}</Label>
            <Input
              type="number"
              min="0"
              value={preset.maxLength || ''}
              onChange={(e) => onChange({ ...preset, maxLength: e.target.value ? parseInt(e.target.value) : undefined })}
              placeholder="100"
            />
          </div>
        </div>
        
        {/* 闂備礁鎲￠悷銉╁储閺嶎厼鐤鹃柛顐ｆ礃閺咁剚鎱ㄥ鍡楀Ш濞撴埃鍋撶€殿喖鐖煎畷绋课旀繝鍐╊吙闂?*/}
        <div className="space-y-4">
          <div>
            <Label className="mb-2 block">{text.templatePresets}</Label>
            <ScrollArea className="h-[600px]">
              <div className="space-y-2 pr-4">
                {templatePresets.map((tp, idx) => (
                  <Card 
                    key={idx} 
                    className="p-3 hover:bg-accent/50 cursor-pointer transition-colors"
                    onClick={() => onChange({ ...preset, template: tp.template })}
                  >
                    <h4 className="text-sm mb-2">{language === 'zh' ? tp.nameZh : tp.nameEn}</h4>
                    <Badge variant="secondary" className="text-xs mb-2 w-full justify-start">
                      {tp.template}
                    </Badge>
                    <p className="text-xs text-muted-foreground">
                      {text.preview}: {language === 'zh' ? tp.exampleZh : tp.exampleEn}
                    </p>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </div>
  );
}

// 闂佸搫顦弲婊堝礉濮椻偓閵嗕線骞嬮敂鐣屽姷婵犮垼鍩栭崝鎴﹀焵椤掆偓缁夌敻鏁嶉幇鏉跨妞ゆ洖鎳庨弲顓㈡煟閻愬鈼ら柛鏂胯嫰閻?
function RuntimePresetForm({ preset, onChange, language }: {
  preset: RuntimePreset;
  onChange: (preset: RuntimePreset) => void;
  language: 'zh' | 'en';
}) {
  const text = t[language];
  
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>{text.runtimePresetName}</Label>
        <Input
          value={preset.name}
          onChange={(e) => onChange({ ...preset, name: e.target.value })}
        />
      </div>
      
      <Separator />
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label>{text.backup}</Label>
          <Switch
            checked={preset.backup}
            onCheckedChange={(checked) => onChange({ ...preset, backup: checked })}
          />
        </div>
        
        <div className="flex items-center justify-between">
          <Label>{text.vision}</Label>
          <Switch
            checked={preset.vision}
            onCheckedChange={(checked) => onChange({ ...preset, vision: checked })}
          />
        </div>
        
        <div className="flex items-center justify-between">
          <Label>{text.autoSave}</Label>
          <Switch
            checked={preset.autoSave}
            onCheckedChange={(checked) => onChange({ ...preset, autoSave: checked })}
          />
        </div>
      </div>
      
      <Separator />
      
      <div className="space-y-2">
        <Label>{text.attachDir}</Label>
        <Input
          value={preset.attachDir}
          onChange={(e) => onChange({ ...preset, attachDir: e.target.value })}
          placeholder="./attachments"
        />
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{text.concurrency}</Label>
          <Input
            type="number"
            min="1"
            max="10"
            value={preset.concurrency}
            onChange={(e) => onChange({ ...preset, concurrency: parseInt(e.target.value) })}
          />
        </div>
        
        <div className="space-y-2">
          <Label>{text.retryCount}</Label>
          <Input
            type="number"
            min="0"
            max="10"
            value={preset.retryCount}
            onChange={(e) => onChange({ ...preset, retryCount: parseInt(e.target.value) })}
          />
        </div>
      </div>
      
      <div className="space-y-2">
        <Label>{text.timeout}</Label>
        <Input
          type="number"
          min="5"
          max="300"
          value={preset.timeout}
          onChange={(e) => onChange({ ...preset, timeout: parseInt(e.target.value) })}
        />
      </div>
      
      <div className="space-y-2">
        <Label>{text.logLevel}</Label>
        <Select 
          value={preset.logLevel} 
          onValueChange={(value: any) => onChange({ ...preset, logLevel: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="debug">Debug</SelectItem>
            <SelectItem value="info">Info</SelectItem>
            <SelectItem value="warn">Warning</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
