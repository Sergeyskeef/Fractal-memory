import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Mic, StopCircle } from 'lucide-react';

interface InputAreaProps {
  onSendMessage: (content: string) => void;
  isLoading: boolean;
}

const InputArea: React.FC<InputAreaProps> = ({ onSendMessage, isLoading }) => {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSendMessage(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
        setIsRecording(false);
        // Mock voice completion
        setInput(prev => prev + " (Voice input simulation)");
    } else {
        setIsRecording(true);
    }
  };

  return (
    <div className="w-full bg-slate-900 border-t border-slate-800 p-4 pb-6">
      <div className="max-w-4xl mx-auto relative flex items-end gap-2 bg-slate-800/50 p-2 rounded-xl border border-slate-700/50 focus-within:border-blue-500/50 focus-within:bg-slate-800 transition-all shadow-lg">
        
        <button className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded-lg transition-colors" title="Attach file">
          <Paperclip size={20} />
        </button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message Mark..."
          className="flex-1 bg-transparent border-none focus:ring-0 resize-none text-slate-200 placeholder-slate-500 max-h-[120px] py-2.5 min-h-[44px]"
          rows={1}
          disabled={isLoading}
        />

        <button 
            onClick={toggleRecording}
            className={`p-2 rounded-lg transition-colors ${isRecording ? 'text-red-500 bg-red-500/10 animate-pulse' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'}`}
        >
            {isRecording ? <StopCircle size={20} /> : <Mic size={20} />}
        </button>

        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className={`p-2 rounded-lg transition-all ${
            input.trim() && !isLoading 
              ? 'bg-blue-600 text-white shadow-lg hover:bg-blue-500' 
              : 'bg-slate-700 text-slate-500 cursor-not-allowed'
          }`}
        >
          <Send size={20} />
        </button>
      </div>
      <div className="text-center mt-2 text-xs text-slate-500">
        Fractal Memory Agent may produce inaccurate information about people, places, or facts.
      </div>
    </div>
  );
};

export default InputArea;