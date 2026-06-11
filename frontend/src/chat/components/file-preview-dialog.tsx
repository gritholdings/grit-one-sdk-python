import { useState } from 'react';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface FilePreviewDialogProps {
  /** Thread the file belongs to (used to build the preview API URL). */
  threadId: string;
  /** Index of the file's first page in the thread's conversation_history. */
  fileIndex?: number;
  filename: string;
  /** Human-readable page count, e.g. "3 pages". */
  pageCount?: string;
}

/**
 * Claude.ai-style preview for a file uploaded in chat.
 *
 * Renders the uploaded-file chip; clicking it opens a modal that shows the first
 * page as a thumbnail alongside the filename and page count. Clicking the
 * thumbnail downloads the PDF rebuilt from the file's stored (redacted) pages.
 * The thumbnail image and the PDF are both produced on demand by
 * `/agent/api/files/preview` — nothing is fetched until the modal is opened.
 */
export const FilePreviewDialog = ({
  threadId,
  fileIndex,
  filename,
  pageCount,
}: FilePreviewDialogProps) => {
  const [open, setOpen] = useState(false);
  const [thumbnailFailed, setThumbnailFailed] = useState(false);

  const canPreview =
    threadId !== '' && fileIndex !== undefined && fileIndex !== null;

  const params = `thread_id=${encodeURIComponent(threadId)}&file_index=${fileIndex}`;
  const thumbnailUrl = `/agent/api/files/preview?${params}&output=image`;
  const pdfUrl = `/agent/api/files/preview?${params}&output=pdf`;
  const downloadName = filename
    ? filename.toLowerCase().endsWith('.pdf')
      ? filename
      : `${filename}.pdf`
    : 'document.pdf';

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <button
        type="button"
        onClick={() => canPreview && setOpen(true)}
        disabled={!canPreview}
        className="ml-auto block border border-dashed border-slate-300 text-left rounded-md px-12 py-4 transition-colors hover:border-slate-400 hover:bg-slate-50 disabled:cursor-default disabled:hover:border-slate-300 disabled:hover:bg-transparent"
      >
        <div>{filename || 'File'}</div>
        {pageCount && (
          <div className="text-xs text-gray-500 mt-1">{pageCount}</div>
        )}
      </button>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="break-all pr-8 text-left">
            {filename || 'File'}
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-col items-center gap-3 pb-2">
          <a
            href={pdfUrl}
            download={downloadName}
            title="Click to download PDF"
            className="block w-full max-w-[240px] overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md"
          >
            {thumbnailFailed ? (
              <div className="flex h-72 w-full items-center justify-center px-4 text-center text-sm text-gray-500">
                Preview unavailable — click to download
              </div>
            ) : (
              <img
                src={thumbnailUrl}
                alt={`Preview of ${filename}`}
                className="h-auto w-full object-contain"
                onError={() => setThumbnailFailed(true)}
              />
            )}
          </a>
          {pageCount && <div className="text-sm text-gray-500">{pageCount}</div>}
        </div>
      </DialogContent>
    </Dialog>
  );
};
