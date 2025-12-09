import React from 'react';
import { Message } from '../../types';
import { User, Bot, Clock, Cpu } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[85%] md:max-w-[70%] gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center mt-1
          ${isUser ? 'bg-indigo-600' : 'bg-emerald-600'}`}>
          {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
        </div>

        {/* Content */}
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words overflow-hidden w-fit max-w-full shadow-sm
            ${isUser 
              ? 'bg-slate-700 text-slate-50 rounded-tr-none border border-slate-600' 
              : 'bg-slate-800 text-slate-100 rounded-tl-none border border-slate-700'
            }`}>
            {message.content}
          </div>

          {/* Metadata Footer */}
          <div className="flex items-center gap-3 mt-1 px-1">
            <span className="text-[10px] text-slate-500 flex items-center gap-1">
              <Clock size={10} />
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            
            {!isUser && message.metadata && (
              <>
                <span className="text-[10px] text-slate-500 flex items-center gap-1" title="Context Nodes Used">
                  <Cpu size={10} />
                  ctx: {message.metadata.context_count}
                </span>
                {message.metadata.importance !== undefined && (
                  <span className="text-[10px] text-slate-500 flex items-center gap-1">
                    imp: {message.metadata.importance.toFixed(2)}
                  </span>
                )}
                {message.metadata.processing_time_ms !== undefined && (
                  <span className="text-[10px] text-slate-500 flex items-center gap-1" title="Processing Time">
                    {message.metadata.processing_time_ms.toFixed(0)}ms
                  </span>
                )}
                {message.metadata.strategies_used && message.metadata.strategies_used.length > 0 && (
                  <span className="text-[10px] text-slate-500 flex items-center gap-1" title="Strategies Used">
                    strat: {message.metadata.strategies_used.join(', ')}
                  </span>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;