import React from 'react'
import Markdown from 'react-markdown'
import { AlertCircle, ChevronRight, LoaderCircle, Orbit } from 'lucide-react'

export function BrandMark() {
  return <span className="brand-mark"><Orbit size={28} strokeWidth={1.5} /></span>
}

export function Notice({ children }) {
  return children ? <div className="notice" role="alert"><AlertCircle size={17} /><span>{children}</span></div> : null
}

export function Busy({ children = 'Loading…' }) {
  return <span className="busy" role="status"><LoaderCircle className="spin" size={16} />{children}</span>
}

export function PageIntro({ icon: Icon, title, children, action, tint = 'gold' }) {
  return <div className="page-intro"><div className={'section-icon ' + tint}><Icon size={24} /></div>
    <div><h1>{title}</h1><p>{children}</p></div>{action}</div>
}

export function Empty({ icon: Icon, title, children }) {
  return <div className="empty"><Icon size={30} strokeWidth={1.4} /><h3>{title}</h3><p>{children}</p></div>
}

export function Source({ value, label }) {
  return /^https?:\/\//i.test(value || '')
    ? <a href={value} target="_blank" rel="noreferrer">{label || value}</a>
    : <span>{label || value}</span>
}

export function Answer({ children }) {
  return <div className="answer"><Markdown components={{
    a: ({ href, children }) => <Source value={href} label={children} />,
    img: ({ alt }) => <span>{alt}</span>,
  }}>{children || ''}</Markdown></div>
}

export function ResourceCard({ item }) {
  const Icon = item.icon
  return <a className={'resource ' + item.tint} href={'#' + item.route}>
    <div className="card-top"><span className={'section-icon ' + item.tint}><Icon size={21} strokeWidth={1.7} /></span><ChevronRight size={17} /></div>
    <h3>{item.title}</h3><p>{item.description}</p>
  </a>
}

export function prettyState(value = '') {
  return value.toLowerCase().replaceAll('_', ' ')
}
