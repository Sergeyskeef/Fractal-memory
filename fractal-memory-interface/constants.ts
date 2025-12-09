// API URL: используем переменную окружения или определяем автоматически
// В браузере всегда используем localhost (Docker пробрасывает порты)
export const API_URL = import.meta.env.VITE_API_URL || 
  (typeof window !== 'undefined' 
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://localhost:8000');

export const MEMORY_COLORS = {
  l0: '#3b82f6', // blue-500
  l1: '#22c55e', // green-500
  l2: '#f97316', // orange-500
  l3: '#a855f7', // purple-500
};

export const LEVEL_LABELS = {
  l0: 'Working',
  l1: 'Session',
  l2: 'Episodic',
  l3: 'Semantic',
};