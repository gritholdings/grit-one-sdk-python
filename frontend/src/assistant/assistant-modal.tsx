import { useState, useEffect, useCallback } from 'react';
import { X } from 'lucide-react';
import { AssistantChatSimple } from './assistant-chat-simple';

const STORAGE_KEY = 'assistant_sidebar_open';

// Type for summarization context passed via events
interface SummarizeContext {
  context: Record<string, unknown>;
  modelName: string;
  recordName: string;
}

export function AssistantModal() {
  // Initialize state from sessionStorage
  const [isOpen, setIsOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem(STORAGE_KEY) === 'true';
    }
    return false;
  });

  // State for summarization context (passed to chat for auto-submit)
  const [summarizeContext, setSummarizeContext] = useState<SummarizeContext | null>(null);

  // Persist state to sessionStorage whenever it changes
  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, String(isOpen));
    // Dispatch event so other components can react to sidebar state changes
    window.dispatchEvent(new CustomEvent('assistantSidebarChange', { detail: { isOpen } }));
  }, [isOpen]);

  const toggleSidebar = useCallback(() => {
    setIsOpen(prev => !prev);
  }, []);

  const closeSidebar = useCallback(() => {
    setIsOpen(false);
  }, []);

  useEffect(() => {
    // Listen for toggle event from header button
    const handleToggleAssistant = () => {
      toggleSidebar();
    };

    // Keep backward compatibility with openAssistant event
    const handleOpenAssistant = () => {
      setIsOpen(true);
    };

    // Handle openAssistantWithContext for summarization feature
    const handleOpenAssistantWithContext = (event: CustomEvent<SummarizeContext>) => {
      setSummarizeContext(event.detail);
      setIsOpen(true);
    };

    window.addEventListener('toggleAssistant', handleToggleAssistant);
    window.addEventListener('openAssistant', handleOpenAssistant);
    window.addEventListener('openAssistantWithContext', handleOpenAssistantWithContext as EventListener);

    return () => {
      window.removeEventListener('toggleAssistant', handleToggleAssistant);
      window.removeEventListener('openAssistant', handleOpenAssistant);
      window.removeEventListener('openAssistantWithContext', handleOpenAssistantWithContext as EventListener);
    };
  }, [toggleSidebar]);

  return (
    <>
      {/* Right-side sidebar panel */}
      <div
        className={`fixed top-14 right-0 bottom-0 w-[440px] max-w-full bg-white border-l border-gray-200 shadow-lg z-40 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        role="complementary"
        aria-label="AI Assistant Sidebar"
        aria-hidden={!isOpen}
      >
        {/* Close button - z-10 to allow dropdowns (z-50) to appear above */}
        <button
          onClick={closeSidebar}
          className="absolute top-3 right-3 z-10 p-1.5 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-300"
          aria-label="Close assistant sidebar"
        >
          <X className="h-5 w-5 text-gray-500" />
        </button>

        {/* Only render chat when open to avoid unnecessary API calls */}
        {isOpen && (
          <AssistantChatSimple
            onClose={closeSidebar}
            summarizeContext={summarizeContext}
            onSummarizeContextConsumed={() => setSummarizeContext(null)}
          />
        )}
      </div>

      {/* Overlay for mobile - optional click-to-close */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 md:hidden"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}
    </>
  );
}

export default AssistantModal;
