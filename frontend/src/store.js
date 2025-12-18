import { create } from 'zustand'

export const useStore = create((set) => ({
  messages: [],
  currentMode: 'assist',
  currentUrl: null,
  browserView: null,

  // Streaming/automation state
  isAutomating: false,
  automationStatus: null,   // { status: "Working...", message: "...", action: "..." }
  automationSteps: [],       // List of completed steps with thumbnails

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message]
    })),

  clearMessages: () =>
    set({ messages: [] }),

  setMode: (mode) =>
    set({ currentMode: mode }),

  setUrl: (url) =>
    set({ currentUrl: url }),

  setBrowserView: (view) =>
    set({ browserView: view }),

  // Automation state setters
  setIsAutomating: (isAutomating) =>
    set({ isAutomating }),

  setAutomationStatus: (automationStatus) =>
    set({ automationStatus }),

  addAutomationStep: (step) =>
    set((state) => ({
      automationSteps: [...state.automationSteps, step]
    })),

  clearAutomationSteps: () =>
    set({ automationSteps: [] }),

  resetAutomationState: () =>
    set({
      isAutomating: false,
      automationStatus: null,
      automationSteps: []
    }),
}))
