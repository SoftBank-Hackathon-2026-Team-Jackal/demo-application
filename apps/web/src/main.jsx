import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

function clockTime(value) {
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(value);
}

function App() {
  const [feed, setFeed] = useState({ items: [], total: 0 });
  const [state, setState] = useState('connecting');
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const response = await fetch('/api/messages?limit=30', { cache: 'no-store' });
        if (!response.ok) throw new Error(`API ${response.status}`);
        const data = await response.json();
        if (active) {
          setFeed(data);
          setState('live');
          setLastUpdated(new Date());
        }
      } catch {
        if (active) setState('offline');
      }
    }
    refresh();
    const timer = setInterval(refresh, 2000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  return (
    <main className="shell">
      <header className="topbar">
        <span className="brand-mark">J</span>
        <span className="brand">JACKAL <em>/</em> MIGRATION LAB</span>
        <span className={`connection ${state}`}><i />{state === 'live' ? 'LIVE' : state === 'offline' ? 'DISCONNECTED' : 'CONNECTING'}</span>
      </header>

      <section className="hero">
        <div className="eyebrow"><span className="eyebrow-line" /> LIVE DATA MIGRATION DEMO</div>
        <h1>Every message<br /><span>makes the move.</span></h1>
        <p>마이그레이션이 진행되는 동안에도 메시지는 계속 쌓입니다. 이 화면에서 현재 데이터의 흐름을 확인하세요.</p>
        <div className="hero-meta"><span>POSTGRESQL 16</span><span className="meta-dot">·</span><span>2초마다 자동 갱신</span></div>
      </section>

      <section className="dashboard">
        <div className="stat-card">
          <div className="stat-top"><span>TOTAL MESSAGES</span><span className="stat-icon">↗</span></div>
          <strong>{feed.total.toLocaleString()}</strong>
          <p>데이터베이스에 저장된 메시지</p>
          <div className="stat-bottom"><span className={`pulse ${state}`} /> {state === 'live' ? '실시간 수집 중' : '연결 상태 확인 중'}</div>
        </div>
        <div className="stat-card secondary">
          <div className="stat-top"><span>LAST SYNC</span><span className="stat-icon">↻</span></div>
          <strong className="time">{lastUpdated ? clockTime(lastUpdated) : '--:--:--'}</strong>
          <p>최근 데이터를 확인한 시각</p>
          <div className="stat-bottom">자동 새로고침 · 2초 간격</div>
        </div>
      </section>

      <section className="feed-section">
        <div className="section-head"><div><div className="eyebrow">THE STREAM</div><h2>최근 메시지</h2></div><span className="feed-count">LATEST 30</span></div>
        <div className="feed-list">
          {feed.items.length === 0 ? <div className="empty">메시지를 기다리고 있습니다.</div> : feed.items.map((item, index) => (
            <article className="feed-item" key={item.id}>
              <span className="item-number">{String(index + 1).padStart(2, '0')}</span>
              <div className="item-main"><p>{item.body}</p><small>{item.request_id}</small></div>
              <time>{clockTime(new Date(item.created_at))}</time>
            </article>
          ))}
        </div>
      </section>
      <footer><span>JACKAL · SOFTBANK HACKATHON 2026</span><span>DATA IN MOTION, VISIBLE.</span></footer>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
