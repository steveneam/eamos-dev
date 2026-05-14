import { EamosLogo } from '@/components/brand/EamosLogo'

export function SiteFooter() {
  return (
    <footer
      className="py-14"
      style={{ borderTop: '0.5px solid var(--line)', background: 'var(--bg-soft2)' }}
    >
      <div
        className="mx-auto flex flex-wrap items-center justify-between gap-6 px-8"
        style={{ maxWidth: 1180 }}
      >
        <div className="flex items-center gap-4">
          <EamosLogo size={16} />
          <span
            className="text-[12px]"
            style={{ color: 'var(--ink-4)' }}
          >
            Built for genomic medicine.
          </span>
        </div>
        <nav className="flex gap-6 text-[12px]" style={{ color: 'var(--ink-4)' }}>
          <a href="#about" className="hover:text-[var(--ink-2)]" style={{ textDecoration: 'none' }}>
            About
          </a>
          <a
            href="https://github.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[var(--ink-2)]"
            style={{ textDecoration: 'none' }}
          >
            GitHub
          </a>
          <a href="#contact" className="hover:text-[var(--ink-2)]" style={{ textDecoration: 'none' }}>
            Contact
          </a>
        </nav>
      </div>
    </footer>
  )
}
