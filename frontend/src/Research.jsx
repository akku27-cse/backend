import React, { useEffect, useState } from 'react'
import { BookOpen, CheckCircle2, ChevronRight, Circle, FlaskConical, GitBranch, Plus, RefreshCw } from 'lucide-react'
import { request } from './api'
import { Answer, Busy, Empty, Notice, PageIntro, Source, prettyState } from './ui'

export function ResearchList({ runs }) {
  return <>
    <PageIntro icon={GitBranch} title="Research runs" tint="lilac" action={<a className="primary intro-action" href="#workspace/research"><Plus size={16} />New research</a>}>
      Reopen investigations started in this browser to inspect their progress and findings.</PageIntro>
    <section className="panel"><h2>Investigations</h2>
      {!runs.length ? <Empty icon={FlaskConical} title="No research runs yet">Start a research inquiry to follow its plan and evidence here.</Empty> :
        <div className="rows">{runs.map(run => <a className="list-row" key={run.id} href={'#research/' + run.id}>
          <FlaskConical size={19} /><div className="row-info"><strong>{run.query}</strong><small>{new Date(run.created).toLocaleString()}</small></div><ChevronRight size={17} /></a>)}</div>}
    </section></>
}

export function RunDetail({ id }) {
  const [execution, setExecution] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let timer
    async function poll() {
      try {
        const data = await request('/api/agent/status/' + encodeURIComponent(id), { signal: controller.signal })
        if (controller.signal.aborted) return
        setExecution(data); setError('')
        if (!['COMPLETED', 'FAILED'].includes(data.state)) timer = setTimeout(poll, 1600)
      } catch (e) {
        if (!controller.signal.aborted) setError(e.status === 404 ? 'This run is no longer available on the backend. Research executions expire when FastAPI restarts.' : e.message)
      }
    }
    setError('')
    poll()
    return () => { clearTimeout(timer); controller.abort() }
  }, [id, attempt])
  return <>
    <PageIntro icon={FlaskConical} title="Research run" tint="lilac">{execution?.query || 'Plan, evidence, and findings for this investigation.'}</PageIntro>
    <Notice>{error}</Notice>{error && <button className="secondary" onClick={() => setAttempt(attempt + 1)}><RefreshCw size={15} />Retry status</button>}
    {!execution && !error && <Busy>Loading research…</Busy>}
    {execution && <>
      <section className="panel"><div className="section-head"><h2>Research plan</h2><span className="pill">{prettyState(execution.state)}</span></div>
        <Notice>{execution.error}</Notice>
        {execution.plan?.tasks?.length ? <ul className="tasks">{execution.plan.tasks.map(task => <li key={task.task_id}>
          {task.status === 'COMPLETED' ? <CheckCircle2 size={18} /> : <Circle size={17} />}
          <div><strong>{task.description}</strong><small>{task.required_tool} · {prettyState(task.status)}</small><Notice>{task.error}</Notice></div>
        </li>)}</ul> : <p>{execution.state === 'FAILED' ? 'No plan was recorded.' : 'Waiting for the research plan…'}</p>}
      </section>
      <section className="panel"><div className="section-head"><h2>Evidence</h2><span className="count">{execution.evidence.length}</span></div>
        {execution.evidence.length ? execution.evidence.map(item => <article key={item.evidence_id} className="evidence">
          <strong><BookOpen size={15} /><Source value={item.source_url} label={item.source_title} /></strong>
          <small>{item.source_type} · {item.source_reference}</small><p>{item.excerpt}</p></article>) : <p>No evidence recorded yet.</p>}
      </section>
      {execution.response && <section className="panel"><h2>Findings</h2><Answer>{execution.response}</Answer></section>}
    </>}
    <a className="text-link" href="#research">All research runs</a>
  </>
}
