import { motion, AnimatePresence } from 'framer-motion'
import { Check, MousePointer2, Type, ArrowUpDown, CornerDownLeft, Globe, Eye } from 'lucide-react'

const actionIcons = {
  click: MousePointer2,
  type: Type,
  scroll: ArrowUpDown,
  press: CornerDownLeft,
  navigate: Globe,
  analyze: Eye,
}

function AutomationSteps({ steps, isVisible }) {
  if (!isVisible || steps.length === 0) return null

  return (
    <div className="absolute top-4 left-4 right-4 z-10">
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
        <AnimatePresence mode="popLayout">
          {steps.map((step, index) => {
            const Icon = actionIcons[step.action] || Check

            return (
              <motion.div
                key={`${step.action}-${index}`}
                initial={{ opacity: 0, scale: 0.8, x: -20 }}
                animate={{ opacity: 1, scale: 1, x: 0 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ delay: index * 0.1 }}
                className="flex-shrink-0"
              >
                <div className="bg-white/95 backdrop-blur-sm rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                  {/* Thumbnail */}
                  {step.screenshot && (
                    <div className="w-24 h-16 bg-gray-100">
                      <img
                        src={`data:image/png;base64,${step.screenshot}`}
                        alt={`Step ${index + 1}`}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}

                  {/* Step info */}
                  <div className="px-2 py-1.5 flex items-center gap-1.5">
                    <div className="w-4 h-4 rounded-full bg-green-100 flex items-center justify-center">
                      <Icon className="w-2.5 h-2.5 text-green-600" />
                    </div>
                    <span className="text-xs text-gray-600 truncate max-w-[60px]">
                      {step.message || step.action}
                    </span>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default AutomationSteps
