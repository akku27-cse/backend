import React, { useEffect, useRef, useState } from 'react'
import { BookOpen, CornerDownLeft, Cpu, FlaskConical, GitBranch, LibraryBig, MessageSquare, MessagesSquare, Plus, Send, Sparkles, Wrench } from 'lucide-react'
import Atlas from './Atlas'
import { Answer, Busy, Notice, ResourceCard, Source } from './ui'

export const resources = [
  { route: 'knowledge', title: 'Knowledge base', description: 'Index PDFs and explore the evidence in your documents.', icon: LibraryBig, tint: 'sage' },
  { route: 'research', title: 'Research runs', description: 'Follow research plans, inspect evidence, and revisit findings.', icon: GitBranch, tint: 'lilac' },
  { route: 'tools', title: 'MCP tools', description: 'Discover connected servers and run their tools directly.', icon: Wrench, tint: 'sand' },
]

function Composer({ mode = 'chat', setMode, onSend, busy, error, model, followUp = false, awaitingRetry = false }) {
  const [text, setText] = useState('')
  const research = mode === 'research'
  function submit(event) {
    event.preventDefault()
    if (!text.trim() || busy || awaitingRetry) return
    onSend(text.trim())
    if (followUp) setText('')
  }
  return <form className="composer" onSubmit={submit}>
    {setMode && <div className="mode-row"><div className="segmented" aria-label="Inquiry mode">
      <button type="button" aria-pressed={!research} onClick={() => setMode('chat')}><MessagesSquare size={15} />Agent chat</button>
      <button type="button" aria-pressed={research} onClick={() => setMode('research')}><FlaskConical size={15} />Deep research</button>
    </div></div>}
    <textarea aria-label={followUp ? 'Follow-up message' : 'Your inquiry'} maxLength={100000} required value={text} disabled={awaitingRetry}
      placeholder={awaitingRetry ? 'Retry the last message to continue this chat.' : followUp ? 'Ask a follow-up question…' : research ? 'What would you like to investigate in depth?' : 'Ask a question, explore an idea, or paste a URL…'}
      onChange={event => setText(event.target.value)} onKeyDown={event => {
        if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing) {
          event.preventDefault(); event.currentTarget.form.requestSubmit()
        }
      }} />
    <Notice>{error}</Notice>
    <div className="composer-foot"><span className="model"><Cpu size={15} />{model || 'Local Ollama'}</span>
      <div className="inline"><kbd title="Control or Command + Enter">Ctrl <CornerDownLeft size={12} /></kbd>
      <button className="primary" disabled={busy || awaitingRetry || !text.trim()}>{busy ? <Busy>Working…</Busy> :
        <>{research ? <FlaskConical size={15} /> : <Send size={15} />}{research ? 'Start research' : 'Send message'}</>}</button></div>
    </div>
  </form>
}

export function Workspace({ initialMode, onChat, onResearch, starting, error }) {
  const [mode, setMode] = useState(initialMode)
  return <>
    <div className="hero">
      <Atlas />
      <div className="hero-content"><span className="hero-label"><i /> LOCAL INTELLIGENCE</span>
        <h1>Research workspace</h1><p>Chat with your agent, investigate a question,<br className="wide-break" /> or find answers in your documents.</p></div>
      <span aria-hidden="true" className="registration-mark">+</span>
    </div>
    <section className="work-section"><div className="section-head"><h2>Start an inquiry</h2></div>
      <Composer mode={mode} setMode={setMode} onSend={mode === 'chat' ? onChat : onResearch} busy={starting} error={error} />
    </section>
    <section className="work-section"><div className="section-head"><h2>Explore the workspace</h2></div>
      <div className="resource-grid">{resources.map(item => <ResourceCard key={item.route} item={item} />)}</div>
    </section>
  </>
}

export function Chat({ chat, pending, onSend, onRetry }) {
  const end = useRef(null)
  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest' }) }, [chat?.messages.length, pending])
  if (!chat) return <div className="panel"><h1>Conversation unavailable</h1><p>This browser has no record of that inquiry.</p><a href="#workspace">Open workspace</a></div>
  const last = chat.messages.at(-1)
  return <>
    <div className="page-intro"><div className="section-icon gold"><MessagesSquare size={23} /></div><div><h1>Agent chat</h1><p>{chat.title}</p></div>
      <a className="secondary intro-action" href="#workspace"><Plus size={15} />New inquiry</a></div>
    <section className="chat-log" aria-label="Conversation">{chat.messages.map((message, index) =>
      <article key={index} className={'message ' + message.role}>
        <div className="message-author">{message.role === 'user' ? <MessageSquare size={16} /> : <Sparkles size={16} />}
          {message.role === 'user' ? 'You' : 'Omniscience'}{message.model && <small>{message.model}</small>}</div>
        {message.role === 'user' ? <p className="plain">{message.content}</p> : <Answer>{message.content}</Answer>}
        {!!message.sources?.length && <details><summary><BookOpen size={15} />Sources ({message.sources.length})</summary>
          <ul>{message.sources.map((source, i) => <li key={i}><Source value={source} /></li>)}</ul></details>}
        {!!message.tools?.length && <div className="tags">{message.tools.map((tool, i) => <span key={i}><Wrench size={12} />{tool}</span>)}</div>}
      </article>)}
      {pending && <Busy>Waiting for the agent…</Busy>}
      {!pending && last?.role === 'user' && <div><Notice>{chat.error || 'The reply was interrupted. You can retry this message.'}</Notice>
        <button className="secondary" onClick={onRetry}>Retry message</button></div>}
      <div ref={end} />
    </section>
    <Composer followUp onSend={onSend} busy={pending} awaitingRetry={!pending && last?.role === 'user'} model={chat.messages.findLast(message => message.model)?.model} />
  </>
}
