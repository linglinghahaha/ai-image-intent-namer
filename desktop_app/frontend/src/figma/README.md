# AI 图片意图批量命名 GUI

A comprehensive desktop application for batch naming images using AI, with support for multiple AI models, languages, and naming strategies.

## Features

- **Batch Processing**: Import and process multiple Markdown files with embedded images
- **AI-Powered Naming**: Generate intelligent image names using configurable AI models
- **Multi-Language Support**: Full bilingual UI (Chinese/English) with independent output language configuration
- **Advanced Configuration**: 
  - Multiple AI model profiles (GPT-4, Claude, Gemini, etc.)
  - Configurable naming templates with placeholders
  - Various processing strategies (Sequential, Context-based, Mixed, Research)
  - Vision model support for image analysis
- **Image Review Panel**: Detailed review interface with candidate suggestions and context viewing
- **Template System**: Customizable naming templates with preset options
- **Real-Time Logging**: Comprehensive logging with filtering and export capabilities
- **TODO Management**: Built-in task tracking for workflow management

## Architecture

The application uses a modern three-panel layout:
- **Left Panel**: File queue management with drag-and-drop support
- **Central Panel**: Processing area with data table for batch operations
- **Right Panel**: Collapsible configuration drawer for all settings
- **Bottom Panel**: Log viewer with progress tracking

## Technical Stack

- React with TypeScript
- Tailwind CSS for styling
- shadcn/ui component library
- Radix UI primitives for accessible components

## Known Console Warnings

The application may display some console warnings during development:

### Ref Forwarding Warnings
```
Warning: Function components cannot be given refs. Attempts to access this ref will fail.
Did you mean to use React.forwardRef()?
```

**Status**: Known issue with Radix UI + shadcn/ui integration
**Impact**: None - These are harmless warnings that don't affect functionality
**Reason**: Some Radix UI components internally try to pass refs to function components

### Clipboard API Warnings
```
NotAllowedError: Failed to execute 'writeText' on 'Clipboard'
```

**Status**: Expected in certain browser contexts
**Impact**: None - The application includes fallback mechanisms
**Solution**: Implemented with fallback to `document.execCommand('copy')` for compatibility

All clipboard operations in the application include robust error handling and fallback mechanisms to ensure copy functionality works across different browser environments.

## Component Structure

```
components/
├── AppBar.tsx              # Top navigation with language switching
├── FileList.tsx            # Left sidebar file management
├── ProcessingArea.tsx      # Central processing table
├── ConfigurationDrawer.tsx # Right sidebar configuration
├── LogPanel.tsx            # Bottom log viewer
├── ImageReviewPanel.tsx    # Detailed image review sheet
├── ConfigurationDialog.tsx # API configuration modal
├── FindReplaceBar.tsx      # Find & replace toolbar
├── TodoDialog.tsx          # TODO list management
└── TemplateAssistant.tsx   # Template helper dialog
```

## Accessibility

- All interactive elements have proper ARIA labels
- Keyboard navigation supported throughout
- Screen reader compatible with proper semantic HTML
- Color contrast meets WCAG AA standards
- All dialogs include proper descriptions for assistive technologies

## Development Notes

The warnings mentioned above are cosmetic and don't indicate any functional issues. The application:
- Properly handles all user interactions
- Includes comprehensive error handling
- Provides fallback mechanisms for browser API limitations
- Maintains accessibility standards

## Future Enhancements

Consider connecting to Supabase for:
- Persistent storage of configurations and profiles
- File processing history tracking
- Collaborative features and team sharing
- Cloud-based template library
