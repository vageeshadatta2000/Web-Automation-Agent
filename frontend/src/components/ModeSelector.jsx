import { motion, AnimatePresence } from 'framer-motion'
import { Search, MessageCircle, Bot, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { useStore } from '../store'

const modes = [
  {
    id: 'assist',
    name: 'Assist',
    icon: MessageCircle,
    color: 'from-green-500 to-emerald-500',
    description: 'Ask questions about pages'
  },
  {
    id: 'research',
    name: 'Research',
    icon: Search,
    color: 'from-blue-500 to-purple-500',
    description: 'Search web with citations'
  },
  {
    id: 'automate',
    name: 'Automate',
    icon: Bot,
    color: 'from-orange-500 to-red-500',
    description: 'Execute tasks automatically'
  }
]

export default function ModeSelector() {
  const [isOpen, setIsOpen] = useState(false)
  const { currentMode, setMode } = useStore()

  const currentModeData = modes.find(m => m.id === currentMode)
  const Icon = currentModeData?.icon || MessageCircle

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="glass glass-hover px-4 py-2 rounded-lg flex items-center gap-2 min-w-[140px]"
      >
        <div className={`p-1 rounded-md bg-gradient-to-br ${currentModeData?.color}`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-medium text-comet-text">
          {currentModeData?.name}
        </span>
        <ChevronDown className={`w-4 h-4 text-comet-text-secondary transition-transform ${
          isOpen ? 'rotate-180' : ''
        }`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 z-40"
            />
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-full mt-2 right-0 bg-white border border-comet-border rounded-xl overflow-hidden shadow-xl z-50 min-w-[280px]"
            >
              {modes.map((mode) => {
                const ModeIcon = mode.icon
                const isActive = mode.id === currentMode

                return (
                  <button
                    key={mode.id}
                    onClick={() => {
                      setMode(mode.id)
                      setIsOpen(false)
                    }}
                    className={`w-full px-4 py-3 flex items-start gap-3 transition-colors ${
                      isActive
                        ? 'bg-comet-primary/10'
                        : 'hover:bg-comet-bg-hover'
                    }`}
                  >
                    <div className={`p-2 rounded-lg bg-gradient-to-br ${mode.color} flex-shrink-0`}>
                      <ModeIcon className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1 text-left">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-comet-text">
                          {mode.name}
                        </span>
                        {isActive && (
                          <div className="w-2 h-2 rounded-full bg-comet-accent" />
                        )}
                      </div>
                      <p className="text-xs text-comet-text-muted mt-0.5">
                        {mode.description}
                      </p>
                    </div>
                  </button>
                )
              })}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
