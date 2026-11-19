import { Link } from 'react-router-dom'

function AuthCard({ title, description, children }) {
  return (
    <main className="auth-page">
      <section className="auth-card">
        <Link className="auth-brand" to="/">KahveCell</Link>
        <h1>{title}</h1>
        <p className="auth-description">{description}</p>
        {children}
      </section>
    </main>
  )
}

export default AuthCard
