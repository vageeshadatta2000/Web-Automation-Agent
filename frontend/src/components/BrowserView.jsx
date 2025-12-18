import { motion } from 'framer-motion'
import { Globe, ExternalLink, RefreshCw } from 'lucide-react'

export default function BrowserView({ url, screenshot }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass p-4 rounded-2xl space-y-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-comet-text-secondary" />
          <span className="text-sm text-comet-text-secondary font-medium">
            Current Page
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button className="text-comet-text-secondary hover:text-comet-text p-1.5 rounded-lg hover:bg-white/5 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-comet-text-secondary hover:text-comet-text p-1.5 rounded-lg hover:bg-white/5 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* URL Bar */}
      <div className="bg-comet-bg px-3 py-2 rounded-lg">
        <p className="text-xs text-comet-text-muted truncate">{url}</p>
      </div>

      {/* Screenshot */}
      {screenshot && (
        <div className="relative rounded-lg overflow-hidden border border-white/5">
          <img
            src={screenshot}
            alt="Browser view"
            className="w-full h-auto"
          />
        </div>
      )}
    </motion.div>
  )
}
