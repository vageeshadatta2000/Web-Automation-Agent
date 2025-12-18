import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles, Search, Bot, Send, Loader2, Globe,
  Settings, RefreshCw, ExternalLink, Lightbulb, X, ChevronRight, ChevronLeft
} from 'lucide-react'
import ChatMessage from './components/ChatMessage'
import ModeSelector from './components/ModeSelector'
import WorkingIndicator from './components/WorkingIndicator'
import AutomationSteps from './components/AutomationSteps'
import LiveStepsIndicator from './components/LiveStepsIndicator'
import { useStore } from './store'
import './App.css'

function App() {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [browserUrl, setBrowserUrl] = useState('about:blank')
  const [browserScreenshot, setBrowserScreenshot] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const messagesEndRef = useRef(null)
  const wsRef = useRef(null)

  const {
    messages,
    currentMode,
    currentUrl,
    addMessage,
    setMode,
    setUrl,
    isAutomating,
    automationStatus,
    automationSteps,
    setIsAutomating,
    setAutomationStatus,
    addAutomationStep,
    clearAutomationSteps,
    resetAutomationState
  } = useStore()

  // WebSocket connection for real-time updates
  const reconnectTimeoutRef = useRef(null)
  const isConnectingRef = useRef(false)

  const connectWebSocket = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current || (wsRef.current && wsRef.current.readyState === WebSocket.OPEN)) {
      return wsRef.current
    }

    isConnectingRef.current = true

    // Use relative URL to work with Vite proxy, fallback to direct connection
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = import.meta.env.DEV
      ? 'ws://localhost:8000/ws'  // Direct connection in dev (Vite proxy has issues with WS)
      : `${wsProtocol}//${window.location.host}/ws`

    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
      wsRef.current = ws
      isConnectingRef.current = false

      // Clear any pending reconnect
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        switch (data.type) {
          case 'automation_start':
            setIsAutomating(true)
            clearAutomationSteps()
            setAutomationStatus({
              status: data.status,
              message: data.message
            })
            break

          case 'automation_status':
            setAutomationStatus({
              status: data.status,
              message: data.message,
              action: data.action,
              step: data.step,
              maxSteps: data.maxSteps
            })
            break

          case 'screenshot_update':
            if (data.screenshot) {
              setBrowserScreenshot(`data:image/png;base64,${data.screenshot}`)
              // Add to automation steps for visual history (limit to last 5)
              addAutomationStep({
                action: automationStatus?.action || 'update',
                message: automationStatus?.message || 'Updated',
                screenshot: data.screenshot
              })
            }
            if (data.url) {
              setBrowserUrl(data.url)
              setUrl(data.url)
            }
            break

          case 'automation_complete':
            setAutomationStatus({
              status: 'Complete',
              message: 'Task finished',
              action: 'done'
            })
            // Clear automation state after a short delay
            setTimeout(() => {
              resetAutomationState()
            }, 2000)
            break

          case 'automation_error':
            setAutomationStatus({
              status: 'Error',
              message: data.error,
              action: 'error'
            })
            setTimeout(() => {
              resetAutomationState()
            }, 3000)
            break

          case 'pong':
            // Keep-alive response
            break

          default:
            break
        }
      } catch (e) {
        console.error('Error parsing WS message:', e)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      wsRef.current = null
      isConnectingRef.current = false

      // Only reconnect if not already scheduled
      if (!reconnectTimeoutRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectTimeoutRef.current = null
          connectWebSocket()
        }, 3000)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      isConnectingRef.current = false
    }

    return ws
  }, [setIsAutomating, setAutomationStatus, addAutomationStep, clearAutomationSteps, resetAutomationState, setUrl, automationStatus, setBrowserScreenshot, setBrowserUrl])

  // Connect WebSocket on mount (only once)
  useEffect(() => {
    const ws = connectWebSocket()

    // Keep-alive ping every 30 seconds
    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close()
      }
    }
  }, []) // Empty dependency array - only run once on mount

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: input,
      mode: currentMode,
      timestamp: new Date()
    }

    addMessage(userMessage)
    setInput('')
    setIsLoading(true)

    // Immediately show automation indicator for automate mode
    if (currentMode === 'automate' || input.toLowerCase().includes('navigate') || input.toLowerCase().includes('go to') || input.toLowerCase().includes('open')) {
      setIsAutomating(true)
      setAutomationStatus({
        status: 'Working...',
        message: 'Preparing to assist you'
      })
    }

    try {
      // API call to backend
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          mode: currentMode,
          url: currentUrl
        })
      })

      const data = await response.json()

      // Update browser preview if screenshot available
      if (data.screenshot) {
        setBrowserScreenshot(`data:image/png;base64,${data.screenshot}`)
      }

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        citations: data.citations,
        suggestedActions: data.suggestedActions,
        reasoning: data.reasoning,
        confidence: data.confidence,
        mode: currentMode,
        timestamp: new Date()
      }

      addMessage(assistantMessage)
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        error: true,
        timestamp: new Date()
      }
      addMessage(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNavigate = async (urlToNavigate = null) => {
    const url = urlToNavigate || browserUrl
    if (!url || url === 'about:blank') return

    // Ensure URL has protocol
    const finalUrl = url.startsWith('http') ? url : `https://${url}`

    setBrowserUrl(finalUrl)
    setUrl(finalUrl)

    try {
      const response = await fetch('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: finalUrl })
      })

      const data = await response.json()
      if (data.screenshot) {
        setBrowserScreenshot(`data:image/png;base64,${data.screenshot}`)
      }
    } catch (error) {
      console.error('Navigation error:', error)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-gray-900 overflow-hidden">
      {/* Header - Minimal like Comet */}
      <header className="flex-shrink-0 bg-gray-800/90 backdrop-blur-sm border-b border-gray-700 px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-blue-400" />
            <span className="text-sm font-semibold text-white">Web Assistant</span>
          </div>

          <div className="flex items-center gap-2">
            <ModeSelector />
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
            >
              {sidebarOpen ? (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronLeft className="w-4 h-4 text-gray-400" />
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content - Browser takes most space, sidebar on right */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Main Browser Area - Takes full width minus sidebar */}
        <div className={`flex-1 flex flex-col transition-all duration-300 ${sidebarOpen ? 'mr-[400px]' : ''}`}>
          {/* Browser URL Bar */}
          <div className="flex-shrink-0 bg-gray-800 border-b border-gray-700 px-4 py-2">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 flex-1 bg-gray-900 px-3 py-2 rounded-lg border border-gray-600">
                <Globe className="w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={browserUrl}
                  onChange={(e) => setBrowserUrl(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleNavigate()}
                  placeholder="Enter URL..."
                  className="flex-1 bg-transparent text-sm text-white placeholder-gray-500 focus:outline-none"
                />
              </div>
              <button
                onClick={handleNavigate}
                className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
              >
                <RefreshCw className="w-4 h-4 text-gray-400" />
              </button>
              <button className="p-2 rounded-lg hover:bg-gray-700 transition-colors">
                <ExternalLink className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          </div>

          {/* Browser Display - Full size */}
          <div className="flex-1 bg-white relative overflow-hidden">
            {browserScreenshot ? (
              <div className="w-full h-full relative">
                <img
                  src={browserScreenshot}
                  alt="Browser view"
                  className="w-full h-full object-contain bg-white"
                />

                {/* Blue glow overlay during automation */}
                {isAutomating && (
                  <motion.div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                      boxShadow: 'inset 0 0 60px rgba(59, 130, 246, 0.2)',
                    }}
                    animate={{
                      opacity: [0.5, 0.8, 0.5],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                  />
                )}

                {/* Working indicator at bottom */}
                {isAutomating && (
                  <div className="absolute bottom-4 left-4 right-4">
                    <WorkingIndicator status={automationStatus} isVisible={isAutomating} />
                  </div>
                )}
              </div>
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gray-100">
                <div className="text-center">
                  <Globe className="w-20 h-20 mx-auto text-gray-300 mb-4" />
                  <p className="text-gray-500 text-lg mb-2">No page loaded</p>
                  <p className="text-gray-400 text-sm">
                    Navigate to a URL or ask me to open a website
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar - Chat Assistant (Comet-style) */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ x: 400, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 400, opacity: 0 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="absolute right-0 top-0 bottom-0 w-[400px] bg-white border-l border-gray-200 flex flex-col shadow-2xl"
            >
              {/* Sidebar Header */}
              <div className="flex-shrink-0 px-4 py-3 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <span className="font-semibold text-gray-800">Assistant</span>
                  </div>
                  <button
                    onClick={() => setSidebarOpen(false)}
                    className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    <X className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                {/* Welcome State */}
                {messages.length === 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-center justify-center h-full text-center px-4"
                  >
                    <motion.div
                      animate={{
                        scale: [1, 1.05, 1],
                      }}
                      transition={{
                        duration: 3,
                        repeat: Infinity,
                        ease: "easeInOut"
                      }}
                      className="mb-4"
                    >
                      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                        <Sparkles className="w-8 h-8 text-white" />
                      </div>
                    </motion.div>

                    <h2 className="text-xl font-bold text-gray-800 mb-2">
                      How can I help?
                    </h2>
                    <p className="text-gray-500 text-sm mb-6">
                      Ask me anything or tell me what to do
                    </p>

                    {/* Quick Actions */}
                    <div className="grid grid-cols-1 gap-2 w-full">
                      {[
                        { icon: Globe, text: "Open YouTube", mode: "automate" },
                        { icon: Search, text: "Search for something", mode: "research" },
                        { icon: Bot, text: "Create a new project", mode: "automate" },
                      ].map((example, i) => (
                        <motion.button
                          key={i}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.1 }}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => {
                            setInput(example.text)
                            setMode(example.mode)
                          }}
                          className="flex items-center gap-3 p-3 rounded-xl border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-all text-left"
                        >
                          <example.icon className="w-4 h-4 text-blue-500" />
                          <span className="text-sm text-gray-600">{example.text}</span>
                        </motion.button>
                      ))}
                    </div>
                  </motion.div>
                )}

                {/* Messages */}
                <AnimatePresence mode="popLayout">
                  {messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
                  ))}
                </AnimatePresence>

                {/* Live Steps Indicator */}
                {(isLoading || isAutomating) && (
                  <AnimatePresence mode="wait">
                    {isAutomating ? (
                      <LiveStepsIndicator
                        key="live-steps"
                        status={automationStatus}
                        steps={automationSteps}
                        isVisible={isAutomating}
                      />
                    ) : (
                      <motion.div
                        key="loading"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center gap-3 bg-gray-50 p-3 rounded-xl"
                      >
                        <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                        <span className="text-sm text-gray-600">
                          {currentMode === 'research' && 'Searching the web...'}
                          {currentMode === 'assist' && 'Analyzing page...'}
                          {currentMode === 'automate' && 'Planning actions...'}
                        </span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Bar */}
              <div className="flex-shrink-0 border-t border-gray-200 p-3 bg-gray-50">
                <div className="relative">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Add details to this task..."
                    rows={1}
                    className="w-full bg-white border border-gray-300 rounded-xl px-4 py-3 pr-12 text-gray-800 placeholder-gray-400 resize-none focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all text-sm"
                    style={{
                      minHeight: '48px',
                      maxHeight: '100px',
                    }}
                  />

                  <button
                    onClick={handleSend}
                    disabled={!input.trim() || isLoading}
                    className={`absolute right-2 bottom-2 p-2 rounded-lg transition-all ${
                      input.trim() && !isLoading
                        ? 'bg-blue-500 hover:bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    }`}
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>

                <div className="flex items-center justify-between mt-2 text-xs text-gray-400">
                  <span>Press Enter to send</span>
                  <div className="flex items-center gap-2">
                    <span className="capitalize">{currentMode}</span>
                    {currentUrl && (
                      <>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Globe className="w-3 h-3" />
                          {new URL(currentUrl).hostname}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Toggle button when sidebar is closed */}
        {!sidebarOpen && (
          <motion.button
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            onClick={() => setSidebarOpen(true)}
            className="absolute right-4 top-4 p-3 bg-blue-500 hover:bg-blue-600 rounded-full shadow-lg transition-colors"
          >
            <Sparkles className="w-5 h-5 text-white" />
          </motion.button>
        )}
      </div>
    </div>
  )
}

export default App
