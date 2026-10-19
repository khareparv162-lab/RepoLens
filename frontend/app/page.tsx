"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  Activity, ArrowDownRight, ArrowUpRight, BookOpen, CheckCircle2,
  ChevronRight, CircleAlert, Clock3, Code2, ExternalLink, GitBranch,
  GitCommit, GitFork, Github, History, LoaderCircle, RefreshCw, Search,
  ShieldCheck, Star, Users, XCircle,
} from "lucide-react";
import {
  analyzeRepository,
  getHistory,
  type HistoryItem,
  type RepositoryAnalysis,
} from "@/lib/api";

function formatNumber(value: number) {
  return new Intl.NumberFormat("en", { notation: value >= 10000 ? "compact" : "standard" }).format(value);
}

function timeAgo(value: string | null) {
  if (!value) return "Unknown date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown date";
  return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(
    Math.round((date.getTime() - Date.now()) / 86400000), "day"
  );
}

function parseRepositoryInput(input: string): { owner: string; repo: string } | null {
  const trimmed = input.trim().replace(/\/+$/, "");
  const githubUrl = trimmed.match(/^(?:https?:\/\/)?(?:www\.)?github\.com\/([^/]+)\/([^/?#]+)/i);
  const parts = githubUrl ? [githubUrl[1], githubUrl[2]] : trimmed.split("/");
  if (parts.length !== 2) return null;
  const owner = parts[0].trim();
  const repo = parts[1].replace(/\.git$/i, "").trim();
  if (!owner || !repo || owner.includes(" ") || repo.includes(" ")) return null;
  return { owner, repo };
}

export default function HomePage() {
  const [input, setInput] = useState("vercel/next.js");
  const [analysis, setAnalysis] = useState<RepositoryAnalysis | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeView, setActiveView] = useState<"overview" | "history">("overview");

  const refreshHistory = useCallback(async () => {
    try {
      setHistory(await getHistory());
    } catch {
      // The primary analysis view remains useful if history cannot load.
    }
  }, []);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

  async function handleAnalyze(event?: FormEvent<HTMLFormElement>, value = input) {
    event?.preventDefault();
    const parsed = parseRepositoryInput(value);
    if (!parsed) {
      setError("Enter a repository as owner/repo or paste its GitHub URL.");
      return;
    }
    setLoading(true);
    setError("");
    setActiveView("overview");
    try {
      const result = await analyzeRepository(parsed.owner, parsed.repo);
      setAnalysis(result);
      setInput(`${result.repository.owner}/${result.repository.name}`);
      await refreshHistory();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to analyze this repository.");
    } finally {
      setLoading(false);
    }
  }

  const repo = analysis?.repository;
  const score = analysis?.health_score ?? 0;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={() => setActiveView("overview")}>
          <span className="brand-mark"><Code2 size={20} /></span>
          <span>repo<span className="brand-light">lens</span><small>REPOSITORY INTELLIGENCE</small></span>
        </a>
        <div className="side-label">WORKSPACE</div>
        <button className={`nav-item ${activeView === "overview" ? "active" : ""}`} onClick={() => setActiveView("overview")}>
          <Activity size={17} /> Overview
        </button>
        <button className={`nav-item ${activeView === "history" ? "active" : ""}`} onClick={() => { setActiveView("history"); void refreshHistory(); }}>
          <History size={17} /> Analysis history <span className="nav-count">{history.length}</span>
        </button>
        <div className="sidebar-bottom">
          <div className="status-dot" />
          <div><strong>System status</strong><small>GitHub API · PostgreSQL</small></div>
          <span className="status-label">READY</span>
        </div>
      </aside>

      <section className="main-area">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><ChevronRight size={14} /><strong>{activeView === "history" ? "Analysis history" : "Repository overview"}</strong></div>
          <a className="github-link" href="https://github.com" target="_blank" rel="noreferrer"><Github size={16} /> GitHub <ExternalLink size={13} /></a>
        </header>

        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> DEVELOPER TOOLING / REPOSITORY ANALYTICS</div>
              <h1>{activeView === "history" ? "Analysis history" : "Repository overview"}</h1>
              <p className="subtitle">{activeView === "history" ? "Revisit previous repository health reports stored in your database." : "A clearer picture of repository health, activity, and engineering hygiene."}</p>
            </div>
            <div className="updated-pill"><span /> LIVE ANALYSIS</div>
          </div>

          <form className="search-panel" onSubmit={(event) => void handleAnalyze(event)}>
            <div className="search-icon"><Search size={19} /></div>
            <div className="search-input-wrap">
              <label htmlFor="repo-search">GITHUB REPOSITORY</label>
              <input id="repo-search" value={input} onChange={(event) => setInput(event.target.value)} placeholder="owner/repository or GitHub URL" />
            </div>
            <button className="analyze-button" disabled={loading} type="submit">
              {loading ? <LoaderCircle className="spin" size={17} /> : <Search size={17} />}
              {loading ? "Analyzing..." : "Analyze repository"}
            </button>
          </form>
          <div className="search-hint"><span>TRY</span> <button onClick={() => { setInput("vercel/next.js"); void handleAnalyze(undefined, "vercel/next.js"); }}>vercel/next.js</button><button onClick={() => { setInput("facebook/react"); void handleAnalyze(undefined, "facebook/react"); }}>facebook/react</button><button onClick={() => { setInput("fastapi/fastapi"); void handleAnalyze(undefined, "fastapi/fastapi"); }}>fastapi/fastapi</button></div>

          {error && <div className="error-banner"><CircleAlert size={18} /><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><XCircle size={17} /></button></div>}

          {activeView === "history" ? (
            <section className="panel history-panel">
              <div className="section-heading"><div><h2>Saved reports</h2><p>Latest reports persisted in PostgreSQL</p></div><button className="icon-button" onClick={() => void refreshHistory()} aria-label="Refresh history"><RefreshCw size={16} /></button></div>
              {history.length === 0 ? <div className="empty-state"><History size={28} /><strong>No saved analyses yet</strong><p>Analyze a repository to create your first history record.</p></div> : <div className="history-list">{history.map((item) => <button className="history-row" key={item.id} onClick={() => { setInput(item.repository); void handleAnalyze(undefined, item.repository); }}><span className="history-repo-icon"><Github size={18} /></span><span className="history-info"><strong>{item.repository}</strong><small>{item.created_at ? new Date(item.created_at).toLocaleString() : "Saved report"}</small></span><span className={`history-score ${item.health_score >= 80 ? "good" : item.health_score >= 60 ? "mid" : "low"}`}>{item.health_score}</span><ChevronRight size={16} /></button>)}</div>}
            </section>
          ) : (
            <>
              {!analysis && !loading && !error && <div className="welcome-panel"><div className="welcome-art"><div className="art-ring ring-one" /><div className="art-ring ring-two" /><Code2 size={42} /></div><h2>Start with a public repository</h2><p>Enter a GitHub repository above to inspect its documentation, engineering hygiene, languages, and recent activity.</p><div className="welcome-features"><span><ShieldCheck size={15} /> Hygiene checks</span><span><GitCommit size={15} /> Recent activity</span><span><History size={15} /> Saved history</span></div></div>}

              {loading && <div className="loading-panel"><LoaderCircle className="spin" size={27} /><strong>Inspecting repository</strong><p>Fetching metadata, languages, commits, and contributors from GitHub.</p></div>}

              {analysis && !loading && repo && <>
                <div className="repo-banner">
                  <div className="repo-identity"><div className="repo-avatar"><Github size={25} /></div><div><div className="repo-owner">{repo.owner} <span>/</span></div><h2>{repo.name}</h2><p>{repo.description || "No repository description has been provided."}</p></div></div>
                  <a className="outline-button" href={repo.html_url} target="_blank" rel="noreferrer">View on GitHub <ExternalLink size={14} /></a>
                </div>

                <div className="metric-grid">
                  <div className="metric-card"><div className="metric-top"><span>STARS</span><Star size={17} /></div><strong>{formatNumber(repo.stars)}</strong><small><ArrowUpRight size={13} /> Community interest</small></div>
                  <div className="metric-card"><div className="metric-top"><span>FORKS</span><GitFork size={17} /></div><strong>{formatNumber(repo.forks)}</strong><small><GitBranch size={13} /> Project derivatives</small></div>
                  <div className="metric-card"><div className="metric-top"><span>OPEN ISSUES</span><CircleAlert size={17} /></div><strong>{formatNumber(repo.open_issues)}</strong><small><Activity size={13} /> Current open count</small></div>
                  <div className="metric-card"><div className="metric-top"><span>PRIMARY LANGUAGE</span><Code2 size={17} /></div><strong className="language-metric">{repo.primary_language || "Unknown"}</strong><small><BookOpen size={13} /> {repo.license || "No license detected"}</small></div>
                </div>

                <div className="dashboard-grid">
                  <section className="panel health-panel">
                    <div className="section-heading"><div><h2>Repository health</h2><p>Engineering hygiene snapshot</p></div><span className="panel-tag">5 CHECKS</span></div>
                    <div className="score-row"><div className="score-ring" style={{ "--score": `${score * 3.6}deg` } as React.CSSProperties}><div><strong>{score}</strong><small>/ 100</small></div></div><div className="score-summary"><strong>{score >= 80 ? "Healthy baseline" : score >= 60 ? "Room to improve" : "Needs attention"}</strong><p>{analysis.health_checks.filter((check) => check.passed).length} of {analysis.health_checks.length} baseline checks passed.</p><small>Not a security audit or code-quality guarantee.</small></div></div>
                    <div className="checks-list">{analysis.health_checks.map((check) => <div className="check-row" key={check.key}><span className={`check-icon ${check.passed ? "passed" : "failed"}`}>{check.passed ? <CheckCircle2 size={16} /> : <XCircle size={16} />}</span><span className="check-text"><strong>{check.label}</strong><small>{check.detail}</small></span><span className={`check-status ${check.passed ? "pass" : "missing"}`}>{check.passed ? "PASS" : "MISSING"}</span></div>)}</div>
                  </section>

                  <section className="panel languages-panel">
                    <div className="section-heading"><div><h2>Language breakdown</h2><p>Based on GitHub language byte counts</p></div><Code2 size={17} className="section-icon" /></div>
                    {analysis.languages.length === 0 ? <div className="empty-inline">No language data available.</div> : <div className="language-list">{analysis.languages.slice(0, 7).map((language, index) => <div className="language-item" key={language.name}><div className="language-label"><span className={`language-dot language-${index % 6}`} /><strong>{language.name}</strong><span>{language.percentage}%</span></div><div className="bar-track"><div className={`bar-fill bar-${index % 6}`} style={{ width: `${language.percentage}%` }} /></div></div>)}</div>}
                    <div className="language-foot"><span>{analysis.languages.length} languages detected</span><span>Source: GitHub API</span></div>
                  </section>
                </div>

                <div className="dashboard-grid lower-grid">
                  <section className="panel commits-panel">
                    <div className="section-heading"><div><h2>Recent commits</h2><p>Latest activity from the default branch</p></div><GitCommit size={17} className="section-icon" /></div>
                    {analysis.recent_commits.length === 0 ? <div className="empty-inline">No recent commits returned.</div> : <div className="commit-list">{analysis.recent_commits.map((commit) => <div className="commit-row" key={commit.sha}><span className="commit-mark"><GitCommit size={15} /></span><div className="commit-content"><strong>{commit.message}</strong><small>{commit.author} · {timeAgo(commit.date)}</small></div><code>{commit.sha}</code>{commit.url && <a href={commit.url} target="_blank" rel="noreferrer" aria-label="Open commit"><ExternalLink size={13} /></a>}</div>)}</div>}
                  </section>
                  <section className="panel contributors-panel">
                    <div className="section-heading"><div><h2>Contributors</h2><p>Top contributors returned by GitHub</p></div><Users size={17} className="section-icon" /></div>
                    {analysis.contributors.length === 0 ? <div className="empty-inline">No contributor data returned.</div> : <div className="contributor-list">{analysis.contributors.map((person) => <a className="contributor-row" key={person.login} href={person.url || "#"} target="_blank" rel="noreferrer"><span className="contributor-avatar">{person.avatar_url ? <img src={person.avatar_url} alt="" /> : <Github size={15} />}</span><span className="contributor-name"><strong>{person.login}</strong><small>Contributor</small></span><span className="contribution-count">{formatNumber(person.contributions)} <small>contributions</small></span><ChevronRight size={14} /></a>)}</div>}
                  </section>
                </div>
                <div className="report-footer"><span><Clock3 size={14} /> Analyzed {new Date(analysis.generated_at).toLocaleString()}</span><span><ShieldCheck size={14} /> Public repository data only</span><button onClick={() => void handleAnalyze(undefined, `${repo.owner}/${repo.name}`)}><RefreshCw size={14} /> Refresh report</button></div>
              </>}
            </>
          )}
          <footer className="site-footer"><span>RepoLens <span>©</span> {new Date().getFullYear()}</span><span>Built for clearer repository insights.</span></footer>
        </div>
      </section>
    </main>
  );
}
