import { ExternalLink } from 'lucide-react'
import { motion } from 'framer-motion'

export default function CitationBadge({ citation, index }) {
  return (
    <motion.a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="glass glass-hover p-3 rounded-xl flex items-start gap-3 group"
    >
      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-comet-primary/20 flex items-center justify-center">
        <span className="text-xs font-bold text-comet-primary">{index}</span>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-sm font-medium text-comet-text group-hover:text-comet-primary transition-colors line-clamp-1">
            {citation.title}
          </h4>
          <ExternalLink className="w-3.5 h-3.5 text-comet-text-muted flex-shrink-0 group-hover:text-comet-primary transition-colors" />
        </div>

        <p className="text-xs text-comet-text-muted mt-1 line-clamp-2">
          {citation.snippet || citation.relevant_quote}
        </p>

        <p className="text-xs text-comet-text-muted/60 mt-1.5 truncate">
          {new URL(citation.url).hostname}
        </p>
      </div>
    </motion.a>
  )
}
