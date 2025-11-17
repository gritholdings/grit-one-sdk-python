import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { AssistantChatSimple } from './assistant-chat-simple';

export function AssistantModal() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Listen for the custom event from the header button
    const handleOpenAssistant = () => {
      // Use setTimeout to avoid the click event from propagating to the dialog overlay
      // This ensures the dialog opens after the current event loop completes
      setTimeout(() => {
        setIsOpen(true);
      }, 0);
    };

    window.addEventListener('openAssistant', handleOpenAssistant);

    return () => {
      window.removeEventListener('openAssistant', handleOpenAssistant);
    };
  }, []);

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen} modal={true}>
      <DialogContent
        className="fixed bottom-4 right-4 top-auto left-auto translate-x-0 translate-y-0 w-[440px] h-[600px] max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)] p-0 flex flex-col"
        showCloseButton={true}
        onPointerDownOutside={(e) => {
          // Prevent closing when clicking outside during the first few milliseconds
          // This helps avoid race conditions with the button click
          e.preventDefault();
        }}
        onInteractOutside={(e) => {
          // Allow closing by clicking outside, but only after the dialog is fully open
          // Check if the click target is the button that opened the modal
          const target = e.target as HTMLElement;
          if (target.closest('button[onclick*="openAssistant"]')) {
            e.preventDefault();
          }
        }}
      >
        {/* Hidden title and description for accessibility - the AssistantChatSimple component shows its own visible header */}
        <DialogTitle className="sr-only">AI Assistant</DialogTitle>
        <DialogDescription className="sr-only">Chat with the AI assistant</DialogDescription>
        <AssistantChatSimple onClose={() => setIsOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}

export default AssistantModal;
