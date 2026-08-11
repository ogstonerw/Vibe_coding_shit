import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import sproutUrl from "../assets/sprout.svg";
import { useFarmData } from "../app/FarmDataContext";

const navigation = [
  { to: "/", label: "Парк ботов", icon: "♟", end: true },
  { to: "/test-lab", label: "Test Lab", icon: "⚗" },
  { to: "/risk", label: "Risk Center", icon: "◆" },
  { to: "/releases", label: "Releases", icon: "▣" },
  { to: "/reviews", label: "Agent Reviews", icon: "★" },
] as const;

export function AppShell() {
  const { snapshot, loading, error } = useFarmData();
  const location = useLocation();
  const [watering, setWatering] = useState(false);
  const resetTimer = useRef<number | undefined>(undefined);
  const mainStage = useRef<HTMLElement | null>(null);

  useEffect(
    () => () => {
      window.clearTimeout(resetTimer.current);
    },
    [],
  );

  useEffect(() => {
    if (!snapshot || !mainStage.current) return;
    mainStage.current.scrollTop = 0;
    mainStage.current.focus({ preventScroll: true });
  }, [location.pathname, snapshot]);

  function waterFarm() {
    window.clearTimeout(resetTimer.current);
    setWatering(true);
    resetTimer.current = window.setTimeout(() => setWatering(false), 1800);
  }

  if (loading) {
    return (
      <div className="boot-screen" role="status">
        <span className="pixel-loader" aria-hidden="true" />
        Загружаем карту фермы…
      </div>
    );
  }

  if (error || !snapshot) {
    return (
      <div className="boot-screen boot-screen--error" role="alert">
        <strong>Карта фермы недоступна</strong>
        <span>{error ?? "Неизвестная ошибка mock-репозитория"}</span>
      </div>
    );
  }

  return (
    <div className={`app-shell${watering ? " app-shell--watering" : ""}`}>
      <a className="skip-link" href="#main-content">К основному содержимому</a>

      <header className="top-bar">
        <Link className="farm-brand" to="/" aria-label="На главную фермы ботов">
          <span className="brand-emblem"><img src={sproutUrl} alt="" /></span>
          <span className="brand-copy">
            <strong>{snapshot.farmName}</strong>
            <small>{snapshot.subtitle}</small>
          </span>
        </Link>

        <div className="status-plaques" aria-label="Ключевые статусы">
          {snapshot.plaques.map((plaque) => (
            <div className={`status-plaque status-plaque--${plaque.tone}`} key={plaque.id}>
              <span className="plaque-icon" aria-hidden="true" />
              <span><small>{plaque.label}</small><strong>{plaque.primary}</strong><em>{plaque.secondary}</em></span>
            </div>
          ))}
        </div>

        <div className="operator-card" aria-label="Текущий оператор">
          <span className="operator-avatar" aria-hidden="true"><i /></span>
          <span><strong>{snapshot.operator.displayName}</strong><small>Роль: {snapshot.operator.roleLabel} · {snapshot.operator.mode}</small></span>
          <span className="operator-caret" aria-hidden="true">⌄</span>
        </div>
      </header>

      <div className="farm-workspace">
        <aside className="side-rail" aria-label="Навигация и новости фермы">
          <nav className="primary-nav" aria-label="Основная навигация">
            {navigation.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => `nav-board${isActive ? " nav-board--active" : ""}`}
              >
                <span className="nav-icon" aria-hidden="true">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <section className="news-board" aria-labelledby="news-title">
            <h2 id="news-title">Новости фермы</h2>
            <ul>
              {snapshot.news.map((item) => (
                <li className={`news-item news-item--${item.tone}`} key={item.id}>
                  <span>{item.message}</span><small>{item.age}</small>
                </li>
              ))}
            </ul>
          </section>

          <div className="farm-almanac">
            <div className="day-card"><small>День на ферме</small><strong>{snapshot.farmDay}</strong></div>
            <div className="weather-card"><small>Погода</small><strong>☀ Ясно</strong><span>{snapshot.weather}</span></div>
          </div>
        </aside>

        <main className="main-stage" id="main-content" ref={mainStage} tabIndex={-1}>
          <aside className="evidence-provenance" aria-label="Источник и свежесть evidence snapshot">
            <strong>EVIDENCE SNAPSHOT</strong>
            <span>{snapshot.quality.sourceLabel}</span>
            <span>commit {snapshot.quality.sourceCommit}</span>
            <span>{snapshot.quality.sourceRun}</span>
            <time dateTime={snapshot.quality.capturedAt}>{snapshot.quality.capturedAt}</time>
          </aside>
          <Outlet />
        </main>
      </div>

      <footer className="bottom-dock">
        <NavLink to="/events"><span aria-hidden="true">▤</span> Журнал событий</NavLink>
        <NavLink to="/notifications"><span aria-hidden="true">●</span> Уведомления <b>3</b></NavLink>
        <NavLink to="/builds"><span aria-hidden="true">◇</span> Архив билдов</NavLink>
        <NavLink to="/docs"><span aria-hidden="true">▥</span> Документация</NavLink>
        <button className="water-button" type="button" onClick={waterFarm} aria-pressed={watering}>
          <span className="watering-can" aria-hidden="true">▰</span>
          <span><strong>{watering ? "Ферма полита!" : "Полить ферму"}</strong><small>{watering ? "+5 к уюту · mock" : "Локальная анимация"}</small></span>
        </button>
        <span className="sr-only" aria-live="polite">{watering ? "Ферма полита. Это только локальная анимация." : ""}</span>
      </footer>
    </div>
  );
}
