export interface Project {
  id: string
  title: string
  description: string
  stage: string
  status: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  type?: string
  stage?: string
  stage_complete?: boolean
  stage_ready?: boolean
  stage_ready_hint?: string
  requirement_card?: Record<string, unknown>
  stage_transition?: { from: string; to: string; pending?: boolean }
  thinking_report?: string
  structure?: Record<string, unknown>
}

export interface RequirementCard {
  [key: string]: {
    label: string
    value: string
    state: string
  }
}

export const STAGE_LABELS: Record<string, string> = {
  idea: '想法捕获',
  thinking: '产品思路',
  structure: '产品结构',
  prototype: '原型',
  prd: 'PRD',
  delivery: '交付',
}
