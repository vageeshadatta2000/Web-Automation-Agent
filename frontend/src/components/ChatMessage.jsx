import { motion } from 'framer-motion'
import { User, Sparkles, Copy, Check, ExternalLink, Lightbulb, Brain } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import CitationBadge from './CitationBadge'
import SuggestedActions from './SuggestedActions'

export default function ChatMessage({ message }) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getModeColor = (mode) => {
    switch (mode) {
      case 'research': return 'from-blue-500 to-purple-500'
      case 'assist': return 'from-green-500 to-emerald-500'
      case 'automate': return 'from-orange-500 to-red-500'
      default: return 'from-comet-primary to-comet-accent'
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`flex gap-4 max-w-3xl ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${
          isUser
            ? 'bg-gradient-to-br from-comet-primary to-comet-primary-dark'
            : `bg-gradient-to-br ${getModeColor(message.mode)}`
        }`}>
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Sparkles className="w-5 h-5 text-white" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 space-y-3">
          <div className={`glass p-5 rounded-2xl ${
            isUser
              ? 'bg-comet-primary/10 border-comet-primary/20'
              : ''
          }`}>
            {/* Mode Badge */}
            {!isUser && message.mode && (
              <div className="flex items-center gap-2 mb-3">
                <span className={`text-xs font-medium px-2.5 py-1 rounded-full bg-gradient-to-r ${getModeColor(message.mode)} text-white`}>
                  {message.mode === 'research' && '🔍 Research'}
                  {message.mode === 'assist' && '💬 Assist'}
                  {message.mode === 'automate' && '🤖 Automate'}
                </span>
                {message.confidence && (
                  <span className="text-xs text-comet-text-muted">
                    {(message.confidence * 100).toFixed(0)}% confident
                  </span>
                )}
              </div>
            )}

            {/* Message Content */}
            <div className={`prose prose-invert max-w-none ${isUser ? 'text-comet-text' : ''}`}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ node, ...props }) => (
                    <a
                      {...props}
                      className="text-comet-primary hover:text-comet-primary-light underline inline-flex items-center gap-1"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {props.children}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ),
                  code: ({ node, inline, ...props }) =>
                    inline ? (
                      <code className="bg-comet-bg px-1.5 py-0.5 rounded text-comet-accent font-mono text-sm" {...props} />
                    ) : (
                      <code className="block bg-comet-bg p-4 rounded-lg font-mono text-sm overflow-x-auto" {...props} />
                    ),
                  p: ({ node, ...props }) => (
                    <p className="text-comet-text leading-relaxed mb-3 last:mb-0" {...props} />
                  ),
                  ul: ({ node, ...props }) => (
                    <ul className="list-disc list-inside space-y-1 text-comet-text" {...props} />
                  ),
                  ol: ({ node, ...props }) => (
                    <ol className="list-decimal list-inside space-y-1 text-comet-text" {...props} />
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>

            {/* Reasoning Chain */}
            {message.reasoning && message.reasoning.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mt-4 pt-4 border-t border-comet-border"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-comet-accent" />
                  <span className="text-xs font-medium text-comet-text-secondary">
                    Reasoning Process
                  </span>
                </div>
                <div className="space-y-2">
                  {message.reasoning.map((step, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="flex items-start gap-2 text-sm text-comet-text-muted"
                    >
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-comet-accent/20 flex items-center justify-center text-xs text-comet-accent">
                        {i + 1}
                      </span>
                      <span>{step}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Copy Button */}
            {!isUser && (
              <div className="flex items-center justify-between mt-4 pt-3 border-t border-comet-border-light">
                <span className="text-xs text-comet-text-muted">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </span>
                <button
                  onClick={handleCopy}
                  className="text-comet-text-secondary hover:text-comet-text transition-colors p-1.5 rounded-lg hover:bg-comet-bg-hover"
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-comet-accent" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Citations */}
          {message.citations && message.citations.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-2"
            >
              <div className="flex items-center gap-2 text-xs text-comet-text-secondary">
                <ExternalLink className="w-3.5 h-3.5" />
                <span className="font-medium">Sources</span>
              </div>
              <div className="grid grid-cols-1 gap-2">
                {message.citations.map((citation, i) => (
                  <CitationBadge key={i} citation={citation} index={i + 1} />
                ))}
              </div>
            </motion.div>
          )}

          {/* Suggested Actions */}
          {message.suggestedActions && message.suggestedActions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <SuggestedActions actions={message.suggestedActions} />
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
