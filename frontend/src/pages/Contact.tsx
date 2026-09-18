// Contact — support channels and a message composer (§74).
import { useState } from 'react'
import { Explain, Field } from '../components/ui'

export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' })

  // Compose a mailto link — we never pretend a message was delivered server-side.
  const mailto = `mailto:support@debatesettler.example?subject=${encodeURIComponent(
    form.subject || 'Debate_Settler support'
  )}&body=${encodeURIComponent(`${form.message}\n\n— ${form.name} (${form.email})`)}`

  const canSend = form.email.includes('@') && form.message.trim().length >= 10

  return (
    <div className="col" style={{ gap: 20, maxWidth: 640, margin: '0 auto', width: '100%' }}>
      <div>
        <h1>Contact us</h1>
        <p className="muted">Questions, disputes or feedback — we're happy to help.</p>
      </div>

      <Explain>
        For anything involving money or a disputed result, please include the debate
        reference so our team can find it quickly.
      </Explain>

      <div className="card col" style={{ gap: 6 }}>
        <div><strong>Support email</strong><div className="muted">support@debatesettler.example</div></div>
        <div><strong>Hours</strong><div className="muted">We aim to reply within 2 business days.</div></div>
      </div>

      <div className="card col" style={{ gap: 12 }}>
        <Field label="Your name">
          <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Your email">
          <input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Subject">
          <input className="input" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
        </Field>
        <Field label="Message" hint="At least 10 characters.">
          <textarea className="input textarea" rows={5} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
        </Field>
        <a className={`btn btn-primary ${canSend ? '' : 'btn-secondary'}`}
          href={canSend ? mailto : undefined}
          aria-disabled={!canSend}
          style={!canSend ? { pointerEvents: 'none', opacity: 0.5 } : undefined}>
          Open in email app
        </a>
        <div className="help-text">This opens your own email client — it does not send silently from the site.</div>
      </div>
    </div>
  )
}
