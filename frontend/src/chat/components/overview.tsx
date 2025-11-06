export function Overview({
  className,
  overviewHtml
}: {
  className?: string;
  overviewHtml: string;
}) {
  return (
    <div 
      className={`overview rounded-xl 
        p-6 flex flex-col gap-8 
        leading-relaxed text-center 
        max-w-xl mx-auto
        ${className || ''}
      `}
    >
      {overviewHtml ? (
        <div dangerouslySetInnerHTML={{ __html: overviewHtml }} />
      ) : (
        <p>{overviewHtml}</p>
      )}
    </div>
  );
}