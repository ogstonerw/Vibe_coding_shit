import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="page-card empty-page">
      <span className="empty-page__icon" aria-hidden="true">404</span><h1>Тропа потерялась</h1><p>Такой страницы на ферме нет.</p><Link className="pixel-button" to="/">Вернуться к карте</Link>
    </section>
  );
}
