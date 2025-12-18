# 🎨 Perplexity Assistant - Beautiful Frontend

A stunning, modern React interface inspired by Comet browser with smooth animations, elegant design, and seamless user experience.

## ✨ Quick Start

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

**Note**: Backend must be running on port 8000

## 🎭 Features

- ✅ **Dark Comet-style Theme** with glassmorphism
- ✅ **Smooth Animations** powered by Framer Motion
- ✅ **Three Modes**: Assist, Research, Automate
- ✅ **Real-time Updates** via WebSocket
- ✅ **Citation Display** with source attribution
- ✅ **Suggested Actions** cards
- ✅ **Markdown Rendering** with syntax highlighting
- ✅ **Responsive Design** for all devices

## 🛠️ Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **Zustand** - State management
- **Lucide React** - Icons
- **React Markdown** - Markdown rendering

## 📦 Project Structure

```
src/
├── components/
│   ├── ChatMessage.jsx       # Message bubbles
│   ├── ModeSelector.jsx      # Mode switcher
│   ├── CitationBadge.jsx     # Source citations
│   ├── SuggestedActions.jsx  # Action suggestions
│   └── BrowserView.jsx       # Browser preview
├── App.jsx                   # Main app
├── App.css                   # Custom styles
├── index.css                 # Global styles
├── main.jsx                  # Entry point
└── store.js                  # State management
```

## 🎨 Customization

### Change Colors

Edit `tailwind.config.js`:
```javascript
colors: {
  'comet': {
    primary: '#6366F1',  // Your color
    accent: '#10B981',   // Your color
    // ...
  }
}
```

### Add Animations

Edit `src/index.css`:
```css
@layer components {
  .your-animation {
    animation: pulse 2s infinite;
  }
}
```

## 🚀 Development

```bash
# Install dependencies
npm install

# Start dev server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 📝 Environment

The frontend proxies API requests to the backend:

```javascript
// vite.config.js
proxy: {
  '/api': 'http://localhost:8000',
  '/ws': 'ws://localhost:8000'
}
```

## 🎯 Usage

1. **Start backend**: `python api_server.py`
2. **Start frontend**: `npm run dev`
3. **Open browser**: http://localhost:3000

## 📚 Documentation

- [FRONTEND_GUIDE.md](../FRONTEND_GUIDE.md) - Complete guide
- [SETUP_GUIDE.md](../SETUP_GUIDE.md) - Setup instructions

## 🐛 Troubleshooting

**Issue**: Module not found
```bash
npm install
```

**Issue**: API connection failed
- Ensure backend is running on port 8000
- Check CORS settings

**Issue**: Build fails
```bash
rm -rf node_modules package-lock.json
npm install
```

## ✨ Features in Detail

### Chat Interface
- User and assistant message bubbles
- Mode-colored avatars
- Confidence indicators
- Timestamp display

### Citations
- Source cards with links
- Title and snippet preview
- Domain display
- External link icons

### Suggested Actions
- Action suggestion cards
- Reasoning display
- Click to execute
- Hover animations

### Mode Switching
- Beautiful dropdown
- Gradient mode icons
- Active indicator
- Smooth transitions

## 🎨 Design System

### Colors
- Background: `#0A0A0F`
- Primary: `#6366F1`
- Accent: `#10B981`
- Text: `#E5E7EB`

### Typography
- Sans: Inter
- Mono: JetBrains Mono

### Animations
- Fade in/out
- Slide up/down
- Pulse glow
- Shimmer loading

## 🚢 Production

Build and deploy:

```bash
# Build
npm run build

# Output in dist/
# Serve with your backend or CDN
```

## 📄 License

Part of Perplexity Web Assistant project.

## 🙏 Credits

- Design inspired by Comet browser
- Icons by Lucide
- Fonts by Google Fonts
