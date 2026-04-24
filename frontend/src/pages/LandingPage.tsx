import { Link } from 'react-router-dom'
import {
  Mail,
  Zap,
  Search,
  BarChart2,
  Shield,
  Globe,
  GitBranch,
  ChevronRight,
  CheckCircle,
} from 'lucide-react'

const FEATURES = [
  {
    icon: Search,
    title: 'AI Contact Discovery',
    desc: 'Autonomous multi-source pipeline discovers decision-makers from the web, RSS feeds, and directories.',
  },
  {
    icon: Mail,
    title: 'Smart Sequencing',
    desc: 'Drip campaigns with configurable delays, stop-on-reply logic, and per-step HTML templates.',
  },
  {
    icon: Shield,
    title: 'Email Validation',
    desc: 'Multi-layer verification — DNS, SMTP, ZeroBounce, and a bloom-filter suppression cache.',
  },
  {
    icon: Zap,
    title: 'Hunter.io Enrichment',
    desc: 'Domain-search and email-finder enrich every contact with verified data from Hunter.io.',
  },
  {
    icon: Globe,
    title: 'RSS & Web Scraping',
    desc: 'Continuously scrapes news feeds, company directories, and web pages to surface fresh leads.',
  },
  {
    icon: BarChart2,
    title: 'Analytics & Reports',
    desc: 'Daily PDF/Excel reports with open rates, bounce stats, and per-campaign KPIs.',
  },
  {
    icon: GitBranch,
    title: 'A/B Subject Testing',
    desc: '50/50 splits on subject lines with automatic winner detection based on open-rate data.',
  },
  {
    icon: CheckCircle,
    title: 'Spam Score Guard',
    desc: 'Built-in spam analysis flags risky content before send, keeping domain reputation intact.',
  },
]

const STEPS = [
  {
    number: '01',
    title: 'Define your audience',
    desc: 'Set keywords, industries, and target count. Xmail builds the query plan automatically.',
  },
  {
    number: '02',
    title: 'Discover & enrich',
    desc: 'The 12-node LangGraph pipeline finds, validates, deduplicates, and scores every contact.',
  },
  {
    number: '03',
    title: 'Send & track',
    desc: 'Sequenced campaigns go out on schedule. Opens, clicks, and bounces feed back in real time.',
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg-primary text-text-primary font-sans">
      {/* Nav */}
      <nav className="border-b border-border sticky top-0 bg-bg-primary/90 backdrop-blur z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-accent-yellow" />
            <span className="font-bold text-base tracking-tight">Xmail</span>
          </div>
          <Link
            to="/login"
            className="flex items-center gap-1 text-sm text-accent-yellow hover:text-yellow-300 transition-colors font-medium"
          >
            Sign in <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 bg-bg-card border border-border rounded-full px-4 py-1.5 text-xs text-text-secondary mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
          Agentic outreach — powered by LangGraph + GPT-4o
        </div>

        <h1 className="text-5xl sm:text-6xl font-extrabold leading-tight tracking-tight mb-6">
          AI-driven email outreach
          <br />
          <span className="text-accent-yellow">at global scale.</span>
        </h1>

        <p className="text-lg text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed">
          Xmail autonomously discovers contacts, validates emails, enriches data, and sends
          personalised sequences — so your team focuses on closing, not prospecting.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            to="/login"
            className="inline-flex items-center justify-center gap-2 bg-accent-yellow text-bg-primary font-semibold px-6 py-3 rounded-lg hover:bg-yellow-300 transition-colors"
          >
            Open console <ChevronRight className="w-4 h-4" />
          </Link>
          <a
            href="#features"
            className="inline-flex items-center justify-center gap-2 border border-border text-text-secondary px-6 py-3 rounded-lg hover:border-text-secondary hover:text-text-primary transition-colors"
          >
            See features
          </a>
        </div>
      </section>

      {/* Stats bar */}
      <div className="border-y border-border bg-bg-secondary">
        <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-2 sm:grid-cols-4 gap-6">
          {[
            { label: 'Pipeline nodes', value: '12' },
            { label: 'Validation layers', value: '5' },
            { label: 'Data sources', value: '8+' },
            { label: 'Emails / day', value: '∞' },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="text-3xl font-mono font-bold text-accent-yellow">{value}</div>
              <div className="text-xs text-text-muted mt-1">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-3">Everything in one pipeline</h2>
        <p className="text-text-secondary text-center mb-14 max-w-xl mx-auto">
          From cold prospect to validated, enriched contact — fully automated.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="bg-bg-card border border-border rounded-xl p-5 hover:border-accent-yellow/40 transition-colors"
            >
              <Icon className="w-5 h-5 text-accent-yellow mb-3" />
              <h3 className="font-semibold text-sm mb-1.5">{title}</h3>
              <p className="text-xs text-text-secondary leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border bg-bg-secondary">
        <div className="max-w-6xl mx-auto px-6 py-24">
          <h2 className="text-3xl font-bold text-center mb-3">How it works</h2>
          <p className="text-text-secondary text-center mb-14 max-w-xl mx-auto">
            Three steps from audience definition to booked meetings.
          </p>
          <div className="grid sm:grid-cols-3 gap-8">
            {STEPS.map(({ number, title, desc }) => (
              <div key={number} className="relative">
                <div className="text-5xl font-mono font-black text-border mb-4">{number}</div>
                <h3 className="font-semibold mb-2">{title}</h3>
                <p className="text-sm text-text-secondary leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-6 py-24 text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to launch?</h2>
        <p className="text-text-secondary mb-8 max-w-md mx-auto">
          Sign in to your Xmail console and start the discovery bot.
        </p>
        <Link
          to="/login"
          className="inline-flex items-center gap-2 bg-accent-yellow text-bg-primary font-semibold px-8 py-3 rounded-lg hover:bg-yellow-300 transition-colors"
        >
          Open console <ChevronRight className="w-4 h-4" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Mail className="w-4 h-4 text-accent-yellow" />
            <span className="text-sm font-semibold">Xmail</span>
          </div>
          <p className="text-xs text-text-muted text-center">
            © {new Date().getFullYear()} AmirTech AI · Agentic email outreach
          </p>
          <Link to="/login" className="text-xs text-text-secondary hover:text-text-primary transition-colors">
            Sign in →
          </Link>
        </div>
      </footer>
    </div>
  )
}
