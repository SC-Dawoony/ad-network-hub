import {
  Activity,
  AppWindow,
  CheckCircle2,
  ClipboardList,
  History,
  ListChecks,
  Play,
  RotateCcw,
  Search,
  Settings,
  ShieldCheck,
} from "lucide-react";

const networks = [
  { key: "bigoads", label: "BigOAds", status: "Ready" },
  { key: "ironsource", label: "IronSource", status: "Ready" },
  { key: "mintegral", label: "Mintegral", status: "Ready" },
  { key: "pangle", label: "Pangle", status: "Needs check" },
  { key: "fyber", label: "Fyber", status: "Ready" },
  { key: "inmobi", label: "InMobi", status: "Ready" },
  { key: "unity", label: "Unity", status: "Manual review" },
  { key: "admob", label: "AdMob", status: "OAuth" },
];

const steps = [
  { label: "BigOAds", state: "success", detail: "App and 3 units created" },
  { label: "IronSource", state: "running", detail: "Creating app" },
  { label: "Mintegral", state: "pending", detail: "Waiting" },
  { label: "Pangle", state: "pending", detail: "Waiting" },
];

const logs = [
  { time: "22:31:08", user: "user@company.com", network: "BigOAds", method: "POST", path: "/app/add", status: 200, ms: 812 },
  { time: "22:31:16", user: "user@company.com", network: "BigOAds", method: "POST", path: "/slot/add", status: 200, ms: 533 },
  { time: "22:32:01", user: "user@company.com", network: "IronSource", method: "POST", path: "/apps", status: 201, ms: 664 },
];

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <AppWindow size={22} />
          <span>Ad Network Hub</span>
        </div>
        <nav className="nav-list" aria-label="Primary">
          <button className="nav-item active"><ListChecks size={18} /> Registration</button>
          <button className="nav-item"><ClipboardList size={18} /> Apps</button>
          <button className="nav-item"><Activity size={18} /> API Logs</button>
          <button className="nav-item"><ShieldCheck size={18} /> Audit</button>
          <button className="nav-item"><Settings size={18} /> Settings</button>
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Registration Workbench</p>
            <h1>Register one app across every selected network</h1>
          </div>
          <div className="topbar-actions">
            <label className="search-box">
              <Search size={17} />
              <input placeholder="Search jobs or logs" />
            </label>
            <button className="icon-button" aria-label="History"><History size={18} /></button>
          </div>
        </header>

        <section className="summary-grid" aria-label="Registration summary">
          <div className="metric success">
            <span>Ready networks</span>
            <strong>6</strong>
          </div>
          <div className="metric amber">
            <span>Needs review</span>
            <strong>2</strong>
          </div>
          <div className="metric blue">
            <span>Last job</span>
            <strong>Partial</strong>
          </div>
          <div className="metric rose">
            <span>API failures today</span>
            <strong>1</strong>
          </div>
        </section>

        <section className="main-grid">
          <div className="panel workbench-panel">
            <div className="panel-heading">
              <div>
                <h2>App input</h2>
                <p>Store metadata feeds each network payload.</p>
              </div>
              <button className="secondary-button"><RotateCcw size={16} /> Reset</button>
            </div>

            <div className="form-grid">
              <label>
                <span>Google Play URL</span>
                <input placeholder="https://play.google.com/store/apps/details?id=..." />
              </label>
              <label>
                <span>App Store URL</span>
                <input placeholder="https://apps.apple.com/app/id..." />
              </label>
              <label>
                <span>App match name</span>
                <input placeholder="game-name" />
              </label>
              <label>
                <span>Failure policy</span>
                <select defaultValue="continue">
                  <option value="continue">Continue on failure</option>
                  <option value="stop">Stop on failure</option>
                </select>
              </label>
            </div>

            <div className="network-grid">
              {networks.map((network) => (
                <label className="network-tile" key={network.key}>
                  <input type="checkbox" defaultChecked={network.status !== "Manual review"} />
                  <span>
                    <strong>{network.label}</strong>
                    <small>{network.status}</small>
                  </span>
                </label>
              ))}
            </div>

            <div className="action-row">
              <button className="primary-button"><Play size={17} /> Start registration</button>
            </div>
          </div>

          <div className="panel progress-panel">
            <div className="panel-heading">
              <div>
                <h2>Current job</h2>
                <p>My Game by user@company.com</p>
              </div>
              <span className="status-pill running">Running</span>
            </div>
            <ol className="step-list">
              {steps.map((step) => (
                <li className={`step ${step.state}`} key={step.label}>
                  <CheckCircle2 size={18} />
                  <span>
                    <strong>{step.label}</strong>
                    <small>{step.detail}</small>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="panel logs-panel">
          <div className="panel-heading">
            <div>
              <h2>Recent API logs</h2>
              <p>Requests and responses are masked before storage.</p>
            </div>
            <button className="secondary-button"><Search size={16} /> Filter</button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>User</th>
                  <th>Network</th>
                  <th>Method</th>
                  <th>Path</th>
                  <th>Status</th>
                  <th>ms</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={`${log.time}-${log.path}`}>
                    <td>{log.time}</td>
                    <td>{log.user}</td>
                    <td>{log.network}</td>
                    <td><code>{log.method}</code></td>
                    <td>{log.path}</td>
                    <td><span className="status-pill success">{log.status}</span></td>
                    <td>{log.ms}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
