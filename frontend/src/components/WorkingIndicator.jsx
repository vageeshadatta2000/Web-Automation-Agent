import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, MousePointer2, Type, ArrowUpDown, CornerDownLeft, Globe, Eye } from 'lucide-react'

const actionIcons = {
  click: MousePointer2,
  type: Type,
  scroll: ArrowUpDown,
  press: CornerDownLeft,
  navigate: Globe,
  analyze: Eye,
  done: null,
}

function WorkingIndicator({ status, isVisible }) {
  if (!isVisible || !status) return null

  const ActionIcon = status.action ? actionIcons[status.action] : null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.95 }}
        className="absolute bottom-4 left-4 right-4 z-20"
      >
        <div className="relative overflow-hidden rounded-2xl bg-white/95 backdrop-blur-xl border border-blue-200 shadow-lg shadow-blue-500/10">
          {/* Fluid animation background */}
          <motion.div
            className="absolute inset-0 opacity-20"
            style={{
              background: 'linear-gradient(90deg, transparent, #3B82F6, #60A5FA, #3B82F6, transparent)',
              backgroundSize: '200% 100%',
            }}
            animate={{
              backgroundPosition: ['0% 0%', '200% 0%'],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'linear',
            }}
          />

          {/* Content */}
          <div className="relative px-4 py-3 flex items-center gap-3">
            {/* Animated spinner/icon */}
            <div className="relative">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                className="w-10 h-10 rounded-full border-2 border-blue-200 border-t-blue-500"
              />
              <div className="absolute inset-0 flex items-center justify-center">
                {ActionIcon ? (
                  <ActionIcon className="w-4 h-4 text-blue-600" />
                ) : (
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                )}
              </div>
            </div>

            {/* Status text */}
            <div className="flex-1 min-w-0">
              <motion.p
                key={status.status}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-sm font-semibold text-blue-700"
              >
                {status.status}
              </motion.p>
              <motion.p
                key={status.message}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-xs text-blue-600/70 truncate"
              >
                {status.message}
              </motion.p>
            </div>

            {/* Step indicator */}
            {status.step && status.maxSteps && (
              <div className="flex items-center gap-1">
                {Array.from({ length: status.maxSteps }).map((_, i) => (
                  <motion.div
                    key={i}
                    className={`w-1.5 h-1.5 rounded-full ${
                      i < status.step ? 'bg-blue-500' : 'bg-blue-200'
                    }`}
                    initial={i === status.step - 1 ? { scale: 0 } : {}}
                    animate={i === status.step - 1 ? { scale: 1 } : {}}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Progress bar at bottom */}
          <motion.div
            className="h-0.5 bg-gradient-to-r from-blue-400 via-blue-500 to-blue-400"
            initial={{ scaleX: 0, originX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </motion.div>
    </AnimatePresence>
  )
}

export default WorkingIndicator
