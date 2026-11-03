export function Footer() {
  const links = [
    { name: "Product", href: "#" },
    { name: "Pricing", href: "#" },
    { name: "Documentation", href: "#" },
    { name: "Security", href: "#" },
    { name: "Status", href: "#" },
  ];

  const company = [
    { name: "About", href: "#" },
    { name: "Blog", href: "#" },
    { name: "Careers", href: "#" },
    { name: "Contact", href: "#" },
    { name: "Privacy", href: "#" },
  ];

  return (
    <footer className="border-t border-border/50 bg-background">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-sm bg-blue-accent flex items-center justify-center">
                <span className="text-[10px] font-bold text-white tracking-widest">V</span>
              </div>
              <span className="text-lg font-bold text-text-primary tracking-tight">Ventrix</span>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed max-w-xs">
              Intelligent startup due diligence built for investors. AI-powered analysis,
              evidence verification, and institutional-grade reporting.
            </p>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-text-primary uppercase tracking-wider mb-6">Product</h4>
            <ul className="space-y-3">
              {links.slice(0, 3).map((link) => (
                <li key={link.name}>
                  <a
                    href={link.href}
                    className="text-sm text-text-secondary hover:text-blue-accent transition-colors duration-200"
                  >
                    {link.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-text-primary uppercase tracking-wider mb-6">Company</h4>
            <ul className="space-y-3">
              {company.map((item) => (
                <li key={item.name}>
                  <a
                    href={item.href}
                    className="text-sm text-text-secondary hover:text-blue-accent transition-colors duration-200"
                  >
                    {item.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="border-t border-border/10 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-text-secondary">
            © {new Date().getFullYear()} Ventrix Technologies. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            <a
              href="#"
              className="text-xs text-text-secondary hover:text-text-primary transition-colors duration-200"
            >
              Terms of Service
            </a>
            <a
              href="#"
              className="text-xs text-text-secondary hover:text-text-primary transition-colors duration-200"
            >
              Privacy Policy
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
