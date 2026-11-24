import React, { useEffect, useState } from 'react'
import { Braces, Play, Plug, RefreshCw, Server, Wrench } from 'lucide-react'
import { mcpPath, request } from './api'
import { Busy, Empty, Notice, PageIntro } from './ui'

function ToolForm({ tool }) {
  const schema = tool.input_schema || {}
  const fields = Object.entries(schema.properties || {})
  const simple = fields.length ? fields.every(([, prop]) => prop.type === 'string' && !prop.enum) : schema.additionalProperties === false || !Object.keys(schema).some(k => ['anyOf', 'oneOf', 'allOf', 'additionalProperties', '$ref'].includes(k))
  const [values, setValues] = useState({})
  const [raw, setRaw] = useState('{}')
  const [useJSON, setUseJSON] = useState(!simple)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  async function execute(event) {
    event.preventDefault()
    setError(''); setResult(null)
    let args = values
    if (useJSON) {
      try { args = JSON.parse(raw) } catch { setError('Enter a valid JSON object for the arguments.'); return }
      if (args === null || typeof args !== 'object' || Array.isArray(args)) { setError('Arguments must be a JSON object.'); return }
    }
    setBusy(true)
    try {
      const data = await request(mcpPath + '/execute/' + encodeURIComponent(tool.server) + '/' + encodeURIComponent(tool.name), { method: 'POST', body: args })
      if (!data.success) setError(data.error || 'The tool reported an error.')
      setResult(data)
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  return <details className="tool"><summary><Braces size={19} /><div><strong>{tool.name}</strong><small>{tool.server}</small></div></summary>
    <div className="tool-body"><p>{tool.description}</p><form onSubmit={execute} className="stack">
      {simple && <label className="check"><input type="checkbox" checked={useJSON} disabled={busy} onChange={e => { setUseJSON(e.target.checked); if (e.target.checked) setRaw(JSON.stringify(values, null, 2)) }} />Edit as JSON</label>}
      {useJSON ? <><details><summary>Input schema</summary><pre>{JSON.stringify(schema, null, 2)}</pre></details>
        <label>Arguments (JSON)<textarea className="code-input" value={raw} rows={4} onChange={e => setRaw(e.target.value)} /></label></> :
        fields.map(([name, prop]) => <label key={name}>{prop.title || name}<input value={values[name] ?? prop.default ?? ''} required={schema.required?.includes(name)}
          onChange={e => setValues({ ...values, [name]: e.target.value })} placeholder={prop.description || name} /></label>)}
      <div><button className="primary" disabled={busy || !tool.available}>{busy ? <Busy>Running…</Busy> : <><Play size={14} />Run tool</>}</button></div>
    </form><Notice>{error}</Notice>{result && result.output != null && <div className="tool-output"><h3>Output</h3><pre>{JSON.stringify(result.output, null, 2)}</pre></div>}</div>
  </details>
}

export default function Tools() {
  const [catalog, setCatalog] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(true)
  async function load(refresh = false, signal) {
    setBusy(true); setError('')
    try {
      const servers = await request(mcpPath + '/servers', { signal })
      const tools = await request(mcpPath + (refresh ? '/refresh' : '/tools'), { method: refresh ? 'POST' : 'GET', signal })
      if (!signal?.aborted) setCatalog({ servers, tools })
    } catch (e) { if (!signal?.aborted) setError(e.message) }
    finally { if (!signal?.aborted) setBusy(false) }
  }
  useEffect(() => {
    const controller = new AbortController()
    load(false, controller.signal)
    return () => controller.abort()
  }, [])
  async function switchServer(name, connected) {
    setBusy(true); setError('')
    try {
      await request(mcpPath + (connected ? '/disconnect/' : '/connect/') + encodeURIComponent(name), { method: 'POST' })
      await load(true)
    } catch (e) { setError(e.message); setBusy(false) }
  }
  return <>
    <PageIntro icon={Wrench} title="MCP tools" tint="sand" action={<button className="secondary intro-action" disabled={busy} onClick={() => load(true)}><RefreshCw size={15} />Refresh tools</button>}>
      Manage configured servers and run the tools they expose.</PageIntro>
    <Notice>{error}</Notice>{busy && <Busy>Checking servers and tools…</Busy>}
    {catalog && <>
      <section className="panel"><div className="section-head"><h2>Servers</h2><span className="count">{Object.keys(catalog.servers).length}</span></div>
        {Object.keys(catalog.servers).length ? Object.entries(catalog.servers).map(([name, status]) => <div className="list-row" key={name}>
          <Server size={18} /><div className="row-info"><strong>{name}</strong><small>{status}</small></div>
          <button className="secondary" disabled={busy} onClick={() => switchServer(name, status === 'connected')}><Plug size={15} />{status === 'connected' ? 'Disconnect' : 'Connect'}</button>
        </div>) : <p>No MCP servers configured.</p>}
      </section>
      <section className="panel"><div className="section-head"><h2>Discovered tools</h2><span className="count">{catalog.tools.length}</span></div>
        {catalog.tools.length ? catalog.tools.map(tool => <ToolForm key={tool.server + '/' + tool.name} tool={tool} />) :
          <Empty icon={Wrench} title="No tools available">Connect a configured server, then refresh the tools.</Empty>}
      </section></>}
  </>
}
