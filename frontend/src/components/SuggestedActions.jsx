import { motion } from 'framer-motion'
import { Lightbulb, ArrowRight } from 'lucide-react'
import { useStore } from '../store'

export default function SuggestedActions({ actions }) {
  const { addMessage, setMode } = useStore()

  const handleActionClick = (action) => {
    // Add action as user message
    const message = {
      id: Date.now(),
      role: 'user',
      content: action.label,
      timestamp: new Date()
    }
    addMessage(message)

    // Switch to automate mode if needed
    if (action.action === 'click' || action.action === 'type') {
      setMode('automate')
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs text-comet-text-secondary">
        <Lightbulb className="w-3.5 h-3.5" />
        <span className="font-medium">Suggested Actions</span>
      </div>

      <div className="space-y-2">
        {actions.map((action, i) => (
          <motion.button
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            whileHover={{ scale: 1.02, x: 4 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleActionClick(action)}
            className="w-full glass glass-hover p-3 rounded-xl flex items-start gap-3 text-left group"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-medium text-comet-text group-hover:text-comet-primary transition-colors">
                  {action.label}
                </h4>
                <ArrowRight className="w-4 h-4 text-comet-text-muted group-hover:text-comet-primary group-hover:translate-x-1 transition-all" />
              </div>
              {action.reasoning && (
                <p className="text-xs text-comet-text-muted mt-1">
                  {action.reasoning}
                </p>
              )}
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  )
}
