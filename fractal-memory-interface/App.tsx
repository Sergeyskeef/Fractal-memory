import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Layout/Header';
import MessageBubble from './components/Chat/MessageBubble';
import InputArea from './components/Chat/InputArea';
import StatsPanel from './components/Memory/StatsPanel';
import MemoryBrowser from './components/Memory/MemoryBrowser';
import GraphView from './components/Memory/GraphView';
import { api } from './services/api';
import { Message, MemoryStats, MemoryNode } from './types';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';

function App() {
  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showStats, setShowStats] = useState(true);
  const [showGraph, setShowGraph] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  
  // Data State
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [nodes, setNodes] = useState<MemoryNode[]>([]);
  const [isConsolidating, setIsConsolidating] = useState(false);

  // Refs
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Initial Fetch - загружаем историю и данные
  useEffect(() => {
    const loadInitialData = async () => {
      setIsLoadingHistory(true);
      try {
        // Загружаем историю чата
        const history = await api.getHistory(50);
        
        if (history && history.length > 0) {
          // Конвертируем историю в формат Message
          const historyMessages: Message[] = history.map((msg: any) => ({
            id: msg.id || `hist_${Date.now()}_${Math.random()}`,
            role: msg.role || 'user',
            content: msg.content || '',
            timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
            metadata: msg.metadata || { context_count: 0 }
          }));
          
          // Сортируем по timestamp (старые первыми, новые внизу)
          historyMessages.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
          
          setMessages(historyMessages);
          
          // Прокручиваем вниз после загрузки истории
          setTimeout(() => {
            chatEndRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' });
          }, 200);
        } else {
          // Если истории нет, показываем приветственное сообщение
          setMessages([{
            id: 'init-1',
            role: 'assistant',
            content: 'Привет, Сергей! Системы памяти L0-L3 активны. Я готов к работе.',
            timestamp: new Date(),
            metadata: { importance: 1.0, context_count: 0 }
          }]);
        }
        
        // Загружаем статистику и узлы
        await refreshData();
      } catch (error) {
        console.error('Failed to load initial data:', error);
        // При ошибке показываем приветствие
        setMessages([{
          id: 'init-1',
          role: 'assistant',
          content: 'Привет, Сергей! Системы памяти L0-L3 активны. Я готов к работе.',
          timestamp: new Date(),
          metadata: { importance: 1.0, context_count: 0 }
        }]);
      } finally {
        setIsLoadingHistory(false);
      }
    };
    
    loadInitialData();
  }, []);

  // Auto-scroll при изменении сообщений
  useEffect(() => {
    // Небольшая задержка чтобы DOM обновился
    const timer = setTimeout(() => {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, 50);
    return () => clearTimeout(timer);
  }, [messages, isLoading]);

  const refreshData = async () => {
    try {
        const [newStats, newNodes] = await Promise.all([
            api.getStats(),
            api.getNodes()
        ]);
        setStats(newStats);
        setNodes(newNodes);
    } catch (e) {
        console.error("Failed to refresh data", e);
    }
  };

  const handleSendMessage = async (content: string) => {
    // 1. Add User Message (сохраняем даже если будет ошибка)
    const userMsg: Message = {
        id: Date.now().toString(),
        role: 'user',
        content,
        timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    // 2. API Call
    try {
        const res = await api.chat(content);
        
        // Проверяем, что ответ валидный
        if (!res || !res.response) {
            throw new Error('Invalid response from API');
        }
        
        // 3. Add Bot Message
        const botMsg: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: res.response,
            timestamp: new Date(),
            metadata: {
                context_count: res.context_count || 0,
                importance: 0.5,
                processing_time_ms: res.processing_time_ms || 0,
                strategies_used: res.strategies_used || []
            }
        };
        setMessages(prev => [...prev, botMsg]);
        
        // 4. Update Stats/Memory after chat turn
        await refreshData();

    } catch (error) {
        console.error('Error in handleSendMessage:', error);
        
        // Определяем тип ошибки для более информативного сообщения
        let errorMessage = 'Марк не ответил';
        if (error instanceof Error) {
            if (error.message.includes('timeout') || error.message.includes('Timeout')) {
                errorMessage = 'Марк не ответил (Timeout)';
            } else if (error.message.includes('Network') || error.message.includes('Failed to fetch')) {
                errorMessage = 'Марк не ответил (Network Error)';
            } else {
                errorMessage = `Марк не ответил (${error.message})`;
            }
        }
        
        // Показываем ошибку в красной плашке
        const errorMsg: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `⚠️ ${errorMessage}. Пожалуйста, попробуйте еще раз.`,
            timestamp: new Date(),
            metadata: { context_count: 0, importance: 0.0 }
        };
        setMessages(prev => [...prev, errorMsg]);
    } finally {
        setIsLoading(false);
    }
  };

  const handleConsolidate = async () => {
    setIsConsolidating(true);
    await api.consolidate();
    await refreshData();
    setIsConsolidating(false);
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 font-sans">
      <Header 
        showStats={showStats} 
        toggleStats={() => setShowStats(!showStats)} 
        showGraph={showGraph}
        toggleGraph={() => setShowGraph(!showGraph)}
      />

      <main className="flex-1 flex overflow-hidden pt-14 relative">
        
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col relative min-w-0 overflow-hidden">
          <div className="flex-1 overflow-y-auto custom-scrollbar p-4 md:p-6" style={{ paddingBottom: '180px' }}>
            <div className="max-w-4xl mx-auto">
              {messages.map(msg => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isLoading && (
                  <div className="flex items-center gap-2 text-slate-500 ml-12 text-sm">
                      <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></span>
                      <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></span>
                      <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></span>
                  </div>
              )}
              <div ref={chatEndRef} className="h-16 min-h-[4rem]" />
            </div>
          </div>
          
          <div className="flex-shrink-0 relative z-50">
            <InputArea onSendMessage={handleSendMessage} isLoading={isLoading} />
          </div>
        </div>

        {/* Sidebar (Stats & Browser) */}
        {showStats && (
            <aside className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col shrink-0 transition-all duration-300 absolute md:static h-full right-0 z-30 shadow-2xl md:shadow-none">
                <StatsPanel 
                    stats={stats} 
                    onConsolidate={handleConsolidate} 
                    isConsolidating={isConsolidating} 
                />
                <MemoryBrowser 
                    nodes={nodes} 
                    onNodeClick={(node) => console.log('View node', node)} 
                />
            </aside>
        )}

        {/* Graph View Overlay */}
        {showGraph && (
            <div className="absolute inset-0 z-50">
                <GraphView nodes={nodes} onClose={() => setShowGraph(false)} />
            </div>
        )}
      </main>

      {/* Mobile Toggle for Sidebar if collapsed */}
      {!showStats && (
          <button 
            onClick={() => setShowStats(true)}
            className="fixed top-20 right-4 z-20 bg-slate-800 p-2 rounded-full shadow-lg border border-slate-700 text-slate-400 md:hidden"
          >
              <PanelRightOpen size={20} />
          </button>
      )}
    </div>
  );
}

export default App;