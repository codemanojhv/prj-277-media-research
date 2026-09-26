"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpenText, ChartNoAxesCombined, Database, FileText, FlaskConical, PanelsTopLeft, RadioTower, Search } from "lucide-react";

const navigation = [
  { href: "/", label: "Overview", icon: PanelsTopLeft },
  { href: "/research", label: "Search coverage", icon: Search },
  { href: "/stories", label: "Stories", icon: ChartNoAxesCombined },
  { href: "/articles", label: "Articles", icon: FileText },
  { href: "/methodology", label: "Methodology", icon: BookOpenText },
];

export function ResearchShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const deploymentLabel = process.env.NEXT_PUBLIC_DEPLOYMENT_LABEL || "LOCAL DEMO";
  const storageLabel = deploymentLabel.includes("CLOUDFLARE") ? "CLOUDFLARE D1 RESEARCH STORE" : "LOCAL RESEARCH WORKSPACE";
  return (
    <div className="workspace">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="PRJ 277 home">
          <span className="brand-mark"><RadioTower size={18} strokeWidth={1.8} /></span>
          <span><strong>PRJ_277</strong><small>MEDIA RESEARCH</small></span>
        </Link>
        <div className="side-rule" />
        <p className="side-caption">RESEARCH DESK</p>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return <Link key={href} href={href} className={`nav-link ${active ? "active" : ""}`}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{active && <span className="nav-indicator" />}</Link>;
          })}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-method-card">
          <div className="method-icon"><FlaskConical size={16} /></div>
          <p>Evidence first</p>
          <span>Every interpretation links back to the article sample it came from.</span>
          <Link href="/methodology">Read the method <span aria-hidden="true">↗</span></Link>
        </div>
        <div className="sidebar-footer"><Database size={13} /><span>{storageLabel}</span></div>
      </aside>
      <main className="main-stage">
        <header className="topbar">
          <div className="crumb"><span>PRJ_277</span><span className="crumb-slash">/</span><span>360° coverage study</span></div>
          <div className="topbar-right"><span className="status-dot" /> {deploymentLabel} <span className="topbar-divider" /> {new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date())}</div>
        </header>
        <div className="page-content">{children}</div>
      </main>
    </div>
  );
}
