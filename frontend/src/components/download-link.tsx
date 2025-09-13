interface DownloadLinkProps {
  href: string
  label?: string
  target?: string
  className?: string
}

export default function DownloadLink({ 
  href, 
  label = 'Download', 
  target = '_blank',
  className = 'font-bold underline inline-flex items-center gap-1'
}: DownloadLinkProps) {
  return (
    <a 
      href={href} 
      target={target}
      rel={target === '_blank' ? 'noopener noreferrer' : undefined}
      className={className}
    >
      <svg 
        className="w-4 h-4" 
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24" 
        xmlns="http://www.w3.org/2000/svg"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth={2} 
          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
        />
      </svg>
      {label}
    </a>
  )
}