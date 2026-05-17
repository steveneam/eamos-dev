interface ContextStripProps {
  gene: string
  variant: string
  sub: string
  classification: string
  links?: Array<{ label: string; href: string }>
}

export function ContextStrip({ gene, variant, sub, classification, links = [] }: ContextStripProps) {
  return (
    <div className="ctx-wrap">
      <div className="wrap-wide ctx">
        <div className="ctx-left">
          <span className="ctx-gene">{gene}</span>
          <span className="ctx-sep">·</span>
          <span className="ctx-var">{variant}</span>
          <span className="ctx-sub">{sub}</span>
        </div>
        <div className="ctx-right">
          <span className="ctx-badge lp">
            <span className="bdot" />
            {classification}
          </span>
          {links.map((l) => (
            <a
              key={l.label}
              className="ctx-link"
              href={l.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              {l.label} ↗
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
