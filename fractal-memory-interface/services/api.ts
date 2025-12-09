import { API_URL } from '../constants';
import { ChatResponse, MemoryStats, MemoryNode } from '../types';

// Helper to delay for mock effect
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Mock Data for fallback
const MOCK_STATS: MemoryStats = {
  l0_count: 47,
  l1_count: 12,
  l2_count: 156,
  l3_count: 23,
  last_consolidation: new Date().toISOString()
};

const MOCK_NODES: MemoryNode[] = [
  { id: '1', label: 'User Identity', content: 'User is Sergey', level: 'l3', importance: 0.95, created_at: '2024-12-04T10:00:00Z', connections: ['2', '3'] },
  { id: '2', label: 'Project Goal', content: 'Build Fractal Memory', level: 'l2', importance: 0.85, created_at: '2024-12-04T10:05:00Z', connections: ['1'] },
  { id: '3', label: 'Tech Stack', content: 'React, FastAPI, D3', level: 'l2', importance: 0.70, created_at: '2024-12-04T10:06:00Z', connections: ['2'] },
  { id: '4', label: 'Current Task', content: 'Implement UI', level: 'l0', importance: 0.4, created_at: '2024-12-04T12:00:00Z', connections: ['2'] },
  { id: '5', label: 'Recent Context', content: ' discussing layout', level: 'l1', importance: 0.5, created_at: '2024-12-04T12:05:00Z', connections: ['4'] },
  { id: '6', label: 'System Prompt', content: 'You are Mark', level: 'l3', importance: 1.0, created_at: '2024-01-01T00:00:00Z', connections: ['1'] },
];

export const api = {
  async health(): Promise<boolean> {
    try {
      const res = await fetch(`${API_URL}/health`);
      return res.ok;
    } catch (e) {
      return false;
    }
  },

  async chat(message: string): Promise<ChatResponse> {
    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errorText}`);
      }
      const data = await res.json();
      // Проверяем, что ответ содержит обязательные поля
      if (!data.response) {
        throw new Error('Invalid response format: missing "response" field');
      }
      return {
        response: data.response,
        context_count: data.context_count || 0,
        strategies_used: data.strategies_used || [],
        processing_time_ms: data.processing_time_ms || 0
      };
    } catch (error) {
      console.error("Chat API error:", error);
      // Не используем mock в продакшене - пробрасываем ошибку дальше
      throw error;
    }
  },

  async getStats(): Promise<MemoryStats> {
    try {
      const res = await fetch(`${API_URL}/memory/stats`);
      if (!res.ok) throw new Error('Network response was not ok');
      const data = await res.json();
      // Новый формат API возвращает плоский объект с l0_count, l1_count и т.д.
      // Старый формат был { memory: { l0_count, ... } }, новый - { l0_count, ... }
      return data.memory || data;
    } catch (error) {
       console.warn("Backend unavailable, using mock stats", error);
       return MOCK_STATS;
    }
  },

  async getNodes(level: string = 'all'): Promise<MemoryNode[]> {
    try {
      const res = await fetch(`${API_URL}/memory/${level}?limit=50`);
      if (!res.ok) throw new Error('Network response was not ok');
      return await res.json();
    } catch (error) {
      console.warn("Backend unavailable, using mock nodes");
      if (level === 'all') return MOCK_NODES;
      return MOCK_NODES.filter(n => n.level === level);
    }
  },

  async consolidate(): Promise<{ status: string }> {
    try {
      const res = await fetch(`${API_URL}/memory/consolidate`, { method: 'POST' });
      return await res.json();
    } catch (error) {
      await delay(1500);
      return { status: "success (mock)" };
    }
  },

  async getHistory(limit: number = 50): Promise<any[]> {
    try {
      const res = await fetch(`${API_URL}/chat/history?limit=${limit}`);
      if (!res.ok) throw new Error('Network response was not ok');
      return await res.json();
    } catch (error) {
      console.warn("Failed to get chat history", error);
      return [];
    }
  }
};