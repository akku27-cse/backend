import React, { useEffect, useRef, useState } from 'react'
import { BookOpen, FileText, LibraryBig, RefreshCw, Search, Trash2, Upload } from 'lucide-react'
import { knowledgePath, request } from './api'
import { Answer, Busy, Empty, Notice, PageIntro } from './ui'

export default function Knowledge() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [action, setAction] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [removeId, setRemoveId] = useState('')
  const [scope, setScope] = useState('')
  const [mode, setMode] = useState('answer')
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const input = useRef(null)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setListError('')
    request(knowledgePath + '/documents', { signal: controller.signal }).then(setDocs)
      .catch(e => { if (!controller.signal.aborted) setListError(e.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [attempt])

  async function upload(file) {
    if (!file) return
    setNotice(''); setError('')
    if (!file.name.toLowerCase().endsWith('.pdf')) { setError('Choose a PDF file to index.'); return }
    setAction('upload')
    try {
      const form = new FormData()
      form.append('file', file)
      const document = await request(knowledgePath + '/documents', { method: 'POST', body: form })
      setDocs(current => [...current.filter(doc => doc.document_id !== document.document_id), document])
      setNotice(document.name + ' was indexed.'); setAttempt(value => value + 1)
    } catch (e) { setError(e.message) }
    finally { setAction('') }
  }

  async function remove(id) {
    setAction('delete'); setError(''); setNotice('')
    try {
      await request(knowledgePath + '/documents/' + encodeURIComponent(id), { method: 'DELETE' })
      setDocs(current => current.filter(doc => doc.document_id !== id))
      if (scope === id) setScope('')
      setRemoveId(''); setResult(null); setNotice('Document removed.')
    } catch (e) { setError(e.message) }
    finally { setAction('') }
  }

  async function search(event) {
    event.preventDefault()
    if (!query.trim() || action) return
    setError(''); setNotice(''); setResult(null); setAction('query')
    try {
      const data = await request(knowledgePath + '/' + mode, {
        method: 'POST', body: { query: query.trim(), document_id: scope || null },
      })
      setResult(mode === 'answer' ? data : { sources: data })
    } catch (e) { setError(e.message) }
    finally { setAction('') }
  }

  return <>
    <PageIntro title="Knowledge base" icon={LibraryBig} tint="sage" action={<button className="primary intro-action" disabled={!!action || loading} onClick={() => input.current.click()}>
      {action === 'upload' ? <Busy>Indexing…</Busy> : <><Upload size={16} />Upload PDF</>}</button>}>
      Ask questions across your indexed PDFs and trace answers back to the page.</PageIntro>
    <input ref={input} type="file" accept=".pdf,application/pdf" className="sr-only" tabIndex={-1} aria-label="Select PDF"
      onChange={e => { const file = e.target.files[0]; e.target.value = ''; upload(file) }} />
    <div role="status" className={notice ? 'success' : ''}>{notice}</div>
    <Notice>{error}</Notice>
    <section className="panel"><div className="section-head"><h2>Indexed documents</h2><button className="icon-button" aria-label="Refresh document list" disabled={loading || !!action} onClick={() => setAttempt(attempt + 1)}><RefreshCw size={16} /></button></div>
      <Notice>{listError}</Notice>
      {loading ? <Busy>Loading documents…</Busy> : !docs.length && !listError ? <Empty icon={FileText} title="Your library is empty">Upload a PDF with selectable text to start indexing.</Empty> :
        <div className="rows">{docs.map(doc => <div key={doc.document_id} className="list-row"><FileText size={20} />
          <div className="row-info"><strong>{doc.name}</strong><small>{doc.pages} pages · {doc.chunks} chunks · {Math.max(1, Math.round(doc.size_bytes / 1024))} KB</small></div>
          {removeId === doc.document_id ? <div className="inline"><button className="danger" disabled={!!action} onClick={() => remove(doc.document_id)}>Confirm removal</button>
            <button className="secondary" disabled={!!action} onClick={() => setRemoveId('')}>Cancel</button></div> :
            <button className="icon-button" aria-label={'Remove ' + doc.name} disabled={!!action} onClick={() => setRemoveId(doc.document_id)}><Trash2 size={16} /></button>}
        </div>)}</div>}
    </section>
    <section className="panel"><h2>Query your documents</h2>
      <form onSubmit={search} className="stack"><div className="field-row">
        <label>Response type<select value={mode} disabled={!!action} onChange={e => { setMode(e.target.value); setResult(null) }}>
          <option value="answer">Grounded answer</option><option value="search">Matching passages</option></select></label>
        <label>Search in<select value={scope} disabled={!!action} onChange={e => { setScope(e.target.value); setResult(null) }}><option value="">All documents</option>
          {docs.map(doc => <option value={doc.document_id} key={doc.document_id}>{doc.name}</option>)}</select></label></div>
        <label>Question<textarea value={query} maxLength={100000} required disabled={!!action} rows={3} placeholder="What do your documents say about…" onChange={e => { setQuery(e.target.value); setResult(null) }} /></label>
        <div><button className="primary" disabled={loading || !!action || !query.trim() || !docs.length}>{action === 'query' ? <Busy>Retrieving…</Busy> : <><Search size={16} />{mode === 'answer' ? 'Get answer' : 'Find passages'}</>}</button></div>
      </form>
    </section>
    {result && <section className="panel"><h2>{mode === 'answer' ? 'Document answer' : 'Matching passages'}</h2>
      {result.response && <Answer>{result.response}</Answer>}
      {result.sources.length ? result.sources.map((chunk, i) => <article className="evidence" key={i}><strong><BookOpen size={15} />{chunk.document_name} · p. {chunk.page_number}</strong><p>{chunk.text}</p></article>) : <p>No matching passages were returned.</p>}
    </section>}
  </>
}
