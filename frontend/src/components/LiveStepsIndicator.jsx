import { motion, AnimatePresence } from 'framer-motion'
import { Settings2, MousePointer2, Type, ArrowUpDown, CornerDownLeft, Globe, Eye, Check, AlertCircle } from 'lucide-react'

const actionIcons = {
  click: MousePointer2,
  type: Type,
  scroll: ArrowUpDown,
  press: CornerDownLeft,
  navigate: Globe,
  analyze: Eye,
  done: Check,
  error: AlertCircle,
}

function LiveStepsIndicator({ status, steps, isVisible }) {
  if (!isVisible) return null

  const ActionIcon = status?.action ? actionIcons[status.action] : Settings2

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="glass rounded-2xl p-4 max-w-md"
    >
      {/* Header with spinning indicator */}
      <div className="flex items-center gap-3 mb-3">
        <div className="relative">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            className="w-8 h-8 rounded-full border-2 border-blue-200 border-t-blue-500"
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <Settings2 className="w-3.5 h-3.5 text-blue-600" />
          </div>
        </div>
        <span className="text-sm font-medium text-gray-800">
          {status?.status || 'Working...'}
        </span>
      </div>

      {/* Steps list */}
      <div className="space-y-2">
        {/* Current step */}
        {status?.message && (
          <motion.div
            key={status.message}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-start gap-2"
          >
            <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
              <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            </div>
            <span className="text-sm text-gray-600">{status.message}</span>
          </motion.div>
        )}

        {/* Completed steps with thumbnails */}
        {steps.slice(-3).map((step, index) => (
          <motion.div
            key={`${step.action}-${index}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-start gap-2"
          >
            <div className="flex items-center gap-2 flex-shrink-0">
              {step.screenshot && (
                <div className="w-16 h-10 rounded-md overflow-hidden border border-gray-200">
                  <img
                    src={`data:image/png;base64,${step.screenshot}`}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              {!step.screenshot && (
                <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
                  {actionIcons[step.action] ? (
                    (() => {
                      const Icon = actionIcons[step.action]
                      return <Icon className="w-3 h-3 text-green-600" />
                    })()
                  ) : (
                    <Check className="w-3 h-3 text-green-600" />
                  )}
                </div>
              )}
            </div>
            <span className="text-sm text-gray-500 truncate">
              {step.message}
            </span>
          </motion.div>
        ))}
      </div>

      {/* Current action indicator */}
      {status?.action && status.action !== 'done' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-3 pt-3 border-t border-gray-100"
        >
          <div className="flex items-center gap-2 text-xs text-blue-600">
            <ActionIcon className="w-3.5 h-3.5" />
            <span className="font-medium">
              {status.action === 'click' && 'Clicking'}
              {status.action === 'type' && 'Typing'}
              {status.action === 'scroll' && 'Scrolling'}
              {status.action === 'navigate' && 'Navigating'}
              {status.action === 'analyze' && 'Reading page'}
              {status.action === 'press' && 'Pressing key'}
            </span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

export default LiveStepsIndicator
