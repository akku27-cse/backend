import React, { useCallback, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Activity, ChevronRight, Cpu, GitBranch, LayoutGrid, LibraryBig, Menu, MessageSquare, Monitor, PanelLeft, Plus, RefreshCw, Wrench, X } from 'lucide-react'
import '@fontsource/dm-sans/latin-400.css'
import '@fontsource/dm-sans/latin-500.css'
import '@fontsource/dm-sans/latin-600.css'
import '@fontsource/dm-sans/latin-700.css'
import '@fontsource/instrument-serif/latin-400.css'
import { readSaved, request, writeSaved } from './api'
import { BrandMark, Notice } from './ui'
import { Chat, Workspace } from './Workspace'
import Knowledge from './Knowledge'
import { ResearchList, RunDetail } from './Research'
import Tools from './Tools'
import './styles.css'

const nav = [
  { path: 'workspace', label: 'Overview', icon: LayoutGrid },
  { path: 'knowledge', label: 'Knowledge base', icon: LibraryBig },
  { path: 'research', label: 'Research runs', icon: GitBranch },
  { path: 'tools', label: 'MCP tools', icon: Wrench },
]
const currentRoute = () => window.location.hash.slice(1) || 'workspace'
function useSavedList(key) {
  const [items, setItems] = useState(() => readSaved(key))
  useEffect(() => writeSaved(key, items), [items, key])
  return [items, setItems]
}

function Runtime({ health, refresh, close }) {
  const dialog = useRef(null)
  const [model, setModel] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => { dialog.current.showModal() }, [])
  useEffect(() => {
    const controller = new AbortController()
    setModel(null); setError('')
    request('/api/v1/ollama/status', { signal: controller.signal }).then(setModel)
      .catch(e => { if (!controller.signal.aborted) setError(e.message) })
    return () => controller.abort()
  }, [attempt])
  return <dialog ref={dialog} onCancel={close} onClick={event => { if (event.target === dialog.current) close() }} aria-labelledby="runtime-title">
    <div className="modal-content"><div className="section-head"><h2 id="runtime-title">System status</h2><button className="icon-button" aria-label="Close system status" onClick={close}><X size={18} /></button></div>
      <div className="list-row"><Activity size={18} /><div className="row-info"><strong>FastAPI backend</strong><small>{health}</small></div></div>
      <div className="list-row"><Cpu size={18} /><div className="row-info"><strong>Ollama runtime</strong><small>{model ? model.connected ? model.model_available ? 'Configured model available' : 'Configured model is missing' : 'Disconnected' : error ? 'Status unavailable' : 'Checking…'}</small></div></div>
      <Notice>{error || model?.error}</Notice>
      {!!model?.models?.length && <><h3>Installed models</h3><div className="tags">{model.models.map(name => <span key={name}>{name}</span>)}</div></>}
      <button className="secondary" onClick={() => { refresh(); setAttempt(attempt + 1) }}><RefreshCw size={14} />Check again</button></div>
  </dialog>
}

function App() {
  const [route, setRoute] = useState(currentRoute)
  const [mobile, setMobile] = useState(false)
  const [runtime, setRuntime] = useState(false)
  const [health, setHealth] = useState('Checking')
  const [chats, setChats] = useSavedList('chats')
  const [runs, setRuns] = useSavedList('runs')
  const [pending, setPending] = useState({})
  const [starting, setStarting] = useState(false)
  const [researchError, setResearchError] = useState('')
  const [composerKey, setComposerKey] = useState(0)
  const [section, id] = route.split('/')
  const pageLabel = nav.find(item => item.path === section)?.label || (section === 'chat' ? 'Agent chat' : 'Page unavailable')
  const drawer = useRef(null)
  const main = useRef(null)
  const menu = useRef(null)
  useEffect(() => {
    function change() {
      setRoute(currentRoute()); setMobile(false); setResearchError('')
      window.scrollTo(0, 0)
      main.current?.focus({ preventScroll: true })
    }
    window.addEventListener('hashchange', change)
    return () => window.removeEventListener('hashchange', change)
  }, [])
  useEffect(() => { document.title = pageLabel + ' · The Omniscience Bound' }, [pageLabel])
  useEffect(() => {
    if (!mobile) return
    const sidebar = drawer.current
    const controls = [...sidebar.querySelectorAll('a, button')].filter(node => node.offsetParent !== null)
    controls[0]?.focus()
    function keys(e) {
      if (e.key === 'Escape') { setMobile(false); menu.current?.focus() }
      if (e.key === 'Tab' && e.shiftKey && document.activeElement === controls[0]) { e.preventDefault(); controls.at(-1)?.focus() }
      if (e.key === 'Tab' && !e.shiftKey && document.activeElement === controls.at(-1)) { e.preventDefault(); controls[0]?.focus() }
    }
    const media = window.matchMedia('(min-width: 851px)')
    const resize = e => { if (e.matches) setMobile(false) }
    media.addEventListener('change', resize)
    document.addEventListener('keydown', keys)
    return () => { document.removeEventListener('keydown', keys); media.removeEventListener('change', resize) }
  }, [mobile])
  const refreshHealth = useCallback(async () => {
    try {
      const data = await request('/health', { signal: AbortSignal.timeout(6000) })
      setHealth(data.status === 'ok' ? 'Online' : 'Unavailable')
    } catch { setHealth('Offline') }
  }, [])
  useEffect(() => {
    refreshHealth()
    const timer = setInterval(refreshHealth, 60000)
    return () => clearInterval(timer)
  }, [refreshHealth])
  function newInquiry() {
    setComposerKey(key => key + 1); setResearchError(''); setMobile(false)
    window.location.hash = 'workspace'
    window.scrollTo(0, 0)
  }
  async function send(text, existing, retry = false) {
    const chatId = existing?.id || crypto.randomUUID()
    if (pending[chatId]) return
    const messages = retry ? existing.messages : [...(existing?.messages || []), { role: 'user', content: text }]
    const record = { id: chatId, title: existing?.title || text, messages, error: '' }
    setChats(current => [record, ...current.filter(c => c.id !== chatId)])
    setPending(current => ({ ...current, [chatId]: true }))
    window.location.hash = 'chat/' + chatId
    try {
      // Explicit history also restores a conversation after the backend restarts.
      const data = await request('/api/v1/chat', { method: 'POST', body: {
        message: messages.at(-1).content, history: messages.slice(0, -1).map(({ role, content }) => ({ role, content })),
      } })
      const answer = { role: 'assistant', content: data.response, model: data.model, sources: data.sources, tools: data.tools_used }
      setChats(current => current.map(c => c.id === chatId ? { ...c, messages: [...messages, answer] } : c))
    } catch (e) {
      setChats(current => current.map(c => c.id === chatId ? { ...c, error: e.message } : c))
    } finally { setPending(current => ({ ...current, [chatId]: false })) }
  }
  async function startResearch(query) {
    if (starting) return
    setStarting(true); setResearchError('')
    try {
      const data = await request('/api/agent/research', { method: 'POST', body: { query } })
      setRuns(current => [{ id: data.execution_id, query, created: Date.now() }, ...current])
      if (currentRoute().startsWith('workspace')) window.location.hash = 'research/' + data.execution_id
    } catch (e) { setResearchError(e.message) }
    finally { setStarting(false) }
  }
  const activeChat = chats.find(c => c.id === id)
  const sidebarClose = () => { setMobile(false); menu.current?.focus() }
  return <div className="app">
    <a href="#main-content" className="skip" onClick={e => { e.preventDefault(); main.current.focus() }}>Skip to content</a>
    {mobile && <div className="scrim" onClick={sidebarClose} />}
    <aside className={'sidebar' + (mobile ? ' open' : '')} id="sidebar" ref={drawer} aria-label="Sidebar">
      <div className="brand-row"><a className="brand" href="#workspace" onClick={() => setMobile(false)}><BrandMark /><span>Omniscience<small>BOUND</small></span></a>
        <button className="close-menu" aria-label="Close menu" onClick={sidebarClose}><X size={19} /></button></div>
      <button className="new-inquiry" onClick={newInquiry}><Plus size={17} />New inquiry</button>
      <div className="nav-heading">Workspace</div>
      <nav aria-label="Workspace">{nav.map(({ path, label, icon: Icon }) => <a href={'#' + path} key={path} onClick={() => setMobile(false)}
        className={section === path ? 'active' : ''} aria-current={section === path ? 'page' : undefined}><Icon size={18} />{label}</a>)}</nav>
      <div className="recent"><div className="nav-heading">Recent chats</div>
        {chats.length ? <nav aria-label="Recent chats">{chats.map(c => <a key={c.id} href={'#chat/' + c.id} onClick={() => setMobile(false)} title={c.title}
          className={section === 'chat' && id === c.id ? 'active' : ''}><MessageSquare size={15} /><span>{c.title}</span></a>)}</nav> : <p>Your chats will appear here.</p>}
      </div>
      <div className="sidebar-footer"><span className="device"><Monitor size={18} /></span><div><strong>Local workspace</strong><small>On this device</small></div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="crumb">
      <button className="menu-button" ref={menu} onClick={() => setMobile(true)} aria-label="Open menu" aria-expanded={mobile} aria-controls="sidebar"><Menu size={20} /></button>
      <PanelLeft size={16} className="desktop-mark" /><span>Console</span><ChevronRight size={13} /><strong>{pageLabel}</strong></div>
      <button className="status-button" onClick={() => setRuntime(true)} aria-label={'System status. Backend ' + health}><i className={'dot ' + health.toLowerCase()} />Backend {health.toLowerCase()}</button></header>
      <main id="main-content" tabIndex={-1} ref={main}>
        {section === 'workspace' ? <Workspace key={route + composerKey} initialMode={id === 'research' ? 'research' : 'chat'} onChat={text => send(text)} onResearch={startResearch} starting={starting} error={researchError} /> :
         section === 'chat' ? <Chat key={id} chat={activeChat} pending={pending[id]} onSend={text => send(text, activeChat)} onRetry={() => send('', activeChat, true)} /> :
         section === 'knowledge' ? <Knowledge /> : section === 'tools' ? <Tools /> :
         section === 'research' ? id ? <RunDetail key={id} id={id} /> : <ResearchList runs={runs} /> :
         <section className="panel"><h1>Page unavailable</h1><a href="#workspace">Return to overview</a></section>}
      </main></div>
    {runtime && <Runtime health={health} refresh={refreshHealth} close={() => setRuntime(false)} />}
  </div>
}

createRoot(document.getElementById('root')).render(<App />)
