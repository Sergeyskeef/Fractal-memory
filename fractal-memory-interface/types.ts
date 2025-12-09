export type Role = 'user' | 'assistant';
export type MemoryLevel = 'l0' | 'l1' | 'l2' | 'l3';

export interface Message {
  id: string;
  role: Role;
  content: string;
  timestamp: Date;
  metadata?: {
    context_count: number;
    importance: number;
    processing_time_ms?: number;
  };
  attachments?: { name: string; type: string }[];
}

export interface MemoryStats {
  l0_count: number;
  l1_count: number;
  l2_count: number;
  l3_count: number;
  total_nodes?: number;
  last_consolidation?: string;
}

export interface MemoryNode {
  id: string;
  label: string;
  content: string;
  level: MemoryLevel;
  importance: number;
  created_at: string;
  connections: string[]; // IDs of connected nodes
}

export interface GraphData {
  nodes: MemoryNode[];
  links: { source: string; target: string; value: number }[];
}

export interface ChatResponse {
  response: string;
  context_count: number;
  strategies_used: string[];
  processing_time_ms: number;
}