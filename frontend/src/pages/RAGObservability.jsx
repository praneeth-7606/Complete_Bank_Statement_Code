import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'

const number = (value) => Number(value || 0).toLocaleString('en-IN')
const duration = (value) => `${(Number(value || 0) / 1000).toFixed(2)}s`
const percent = (value) => value == null ? 'Not measured' : `${(value * 100).toFixed(1)}%`
const stageLabel = (stage) => (stage || 'unknown').replace(/^rag\./, '').replaceAll('_', ' ')

function Badge({ value }) {
  const tone = ['passed', 'success', 'exported'].includes(value)
    ? 'bg-emerald-100 text-emerald-800'
    : value === 'failed' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'
  return <span className={`rounded-full px-2 py-1 text-xs font-medium ${tone}`}>{(value || 'unknown').replaceAll('_', ' ')}</span>
}

function SafeMetadata({ metadata }) {
  const values = Object.entries(metadata || {})
  if (!values.length) return <p className="text-xs text-slate-500">No safe metadata recorded.</p>
  return (
    <dl className="grid gap-2 text-xs sm:grid-cols-2">
      {values.map(([key, value]) => <div key={key} className="rounded bg-slate-50 p-2">
        <dt className="capitalize text-slate-500">{key.replaceAll('_', ' ')}</dt>
        <dd className="mt-1 font-medium text-slate-800">{String(value)}</dd>
      </div>)}
    </dl>
  )
}

export default function RAGObservability() {
  const [summary, setSummary] = useState(null)
  const [traces, setTraces] = useState([])
  const [selected, setSelected] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [hours, setHours] = useState(24)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const pending = useRef(null)
  const revision = useRef(0)

  const load = useCallback(async () => {
    pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    const requestVersion = ++revision.current
    setLoading(true)
    try {
      const options = { signal: controller.signal }
      const [summaryResponse, tracesResponse] = await Promise.all([
        api.get(`/observability/rag/summary?hours=${hours}`, options),
        api.get(`/observability/rag/traces?hours=${hours}&limit=50`, options),
      ])
      const nextTraces = tracesResponse.data.traces || []
      const traceId = selectedId || nextTraces[0]?.trace_id
      const detail = traceId ? await api.get(`/observability/rag/traces/${traceId}`, options) : null
      if (requestVersion !== revision.current) return
      setSummary(summaryResponse.data)
      setTraces(nextTraces)
      setSelected(detail?.data || null)
      setError('')
    } catch (requestError) {
      if (!controller.signal.aborted) {
        setError(requestError.response?.data?.detail || 'RAG monitoring data could not be loaded. Try Refresh.')
      }
    } finally {
      if (requestVersion === revision.current) setLoading(false)
    }
  }, [hours, selectedId])

  useEffect(() => {
    load()
    const interval = window.setInterval(load, 15000)
    return () => {
      window.clearInterval(interval)
      pending.current?.abort()
    }
  }, [load])

  const cards = [
    ['RAG requests', number(summary?.requests)],
    ['P95 response time', duration(summary?.p95_latency_ms)],
    ['Retrieved evidence', percent(summary?.retrieval_available_rate)],
    ['Guardrail pass rate', percent(summary?.evaluation_pass_rate)],
    ['LLM fallbacks', number(summary?.fallback_calls)],
  ]
  const ragEvents = (selected?.events || []).filter((event) => event.kind === 'rag' || event.name?.startsWith('rag.'))
  const scores = (selected?.evaluation_scores || []).filter((score) => score.name?.startsWith('rag_'))

  return (
    <div className="space-y-6 text-slate-900">
      <header className="rounded-2xl bg-slate-900 p-6 text-white">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-300">Observability / RAG</p>
            <h1 className="mt-2 text-2xl font-bold">RAG monitoring and evaluation</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-300">Trace every chat through planning, retrieval, reranking, context, response generation, and deterministic guardrails.</p>
          </div>
          <Link to="/observability" className="rounded border border-white/30 px-3 py-2 text-sm font-medium hover:bg-white/10">Pipeline monitoring</Link>
        </div>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <label htmlFor="rag-monitoring-window">Time window</label>
          <select id="rag-monitoring-window" value={hours} onChange={(event) => { setHours(Number(event.target.value)); setSelectedId(null) }} className="rounded border border-white/30 bg-white/10 p-2 text-white [&>option]:text-slate-900">
            <option value={1}>Last hour</option><option value={24}>Last 24 hours</option><option value={168}>Last 7 days</option>
          </select>
          <button type="button" onClick={load} disabled={loading} style={{ backgroundColor: '#ffffff', color: '#0f172a' }} className="rounded px-4 py-2 font-medium disabled:opacity-60">{loading ? 'Loading…' : 'Refresh'}</button>
        </div>
      </header>

      {error && <p role="alert" className="rounded bg-amber-50 p-4 text-amber-900">{error}</p>}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {cards.map(([label, value]) => <div key={label} className="rounded-xl border bg-white p-4"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-xl font-semibold">{value}</p></div>)}
      </div>

      <section className="rounded-xl border bg-white p-4 text-sm text-slate-600">
        <p className="font-medium text-slate-800">What this proves</p>
        <p className="mt-1">Live guardrails verify plan shape, retrieval health, reranking/context integrity, response schema, and deterministic aggregate grounding. Prompts and transaction narration are intentionally excluded from telemetry.</p>
        <p className="mt-2 text-slate-500">{summary?.offline_benchmark_note || 'Offline benchmark results will appear here after verified cases are configured.'}</p>
      </section>

      <section className="overflow-x-auto rounded-xl border bg-white">
        <h2 className="p-4 font-semibold">Pipeline stage performance</h2>
        <table className="w-full text-left text-sm"><thead className="bg-slate-50"><tr>{['Stage', 'Runs', 'Failed', 'Average', 'P95'].map((label) => <th key={label} className="p-3">{label}</th>)}</tr></thead>
          <tbody>{(summary?.stage_metrics || []).map((item) => <tr key={item.stage} className="border-t"><td className="p-3 font-medium capitalize">{stageLabel(item.stage)}</td><td className="p-3">{number(item.runs)}</td><td className="p-3">{number(item.failed)}</td><td className="p-3">{duration(item.avg_latency_ms)}</td><td className="p-3">{duration(item.p95_latency_ms)}</td></tr>)}</tbody>
        </table>
        {!summary?.stage_metrics?.length && <p className="p-6 text-sm text-slate-500">No RAG requests in this window. Ask a question in Chat to create a trace.</p>}
      </section>

      <section className="overflow-x-auto rounded-xl border bg-white">
        <h2 className="p-4 font-semibold">Recent RAG executions</h2>
        <table className="w-full text-left text-sm"><thead className="bg-slate-50"><tr>{['Started', 'Trace', 'Duration', 'LLM calls', 'Status'].map((label) => <th key={label} className="p-3">{label}</th>)}</tr></thead>
          <tbody>{traces.map((trace) => <tr key={trace.trace_id} className="border-t"><td className="p-3">{new Date(trace.started_at).toLocaleString()}</td><td className="p-3"><button type="button" onClick={() => setSelectedId(trace.trace_id)} className="font-mono text-xs text-indigo-700 underline">{trace.trace_id.slice(0, 12)}…</button></td><td className="p-3">{duration(trace.duration_ms)}</td><td className="p-3">{number(trace.metrics?.llm_calls)}</td><td className="p-3"><Badge value={trace.status} /></td></tr>)}</tbody>
        </table>
        {!traces.length && <p className="p-6 text-sm text-slate-500">No RAG executions in this window.</p>}
      </section>

      {selected && <section className="space-y-5 rounded-xl border bg-white p-5">
        <div><h2 className="font-semibold">RAG trace detail</h2><p className="mt-1 break-all font-mono text-xs text-slate-500">Trace ID: {selected.trace_id}</p></div>
        <div className="grid gap-3 md:grid-cols-2">
          {scores.map((score, index) => <div key={`${score.name}-${index}`} className="rounded border p-3"><div className="flex items-start justify-between gap-3"><div><p className="capitalize">{score.name.replace(/^rag_/, '').replaceAll('_', ' ')}</p><p className="mt-1 text-xs text-slate-500">{score.value == null ? 'Requires a verified offline benchmark' : `Score: ${Number(score.value).toFixed(3)}`}</p></div><Badge value={score.passed == null ? 'not_evaluated' : score.passed ? 'passed' : 'failed'} /></div></div>)}
        </div>
        {!scores.length && <p className="text-sm text-slate-500">This trace predates RAG evaluation instrumentation or has not reached the evaluation stage.</p>}
        <div><h3 className="font-semibold">RAG stage timeline</h3><div className="mt-3 space-y-3">{ragEvents.map((event) => <article key={event.event_id} className="rounded border p-3"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-medium capitalize">{stageLabel(event.name)}</p><p className="mt-1 text-xs text-slate-500">{event.kind} · {duration(event.duration_ms)}{event.error_type ? ` · ${event.error_type}` : ''}</p></div><Badge value={event.status} /></div><div className="mt-3"><SafeMetadata metadata={event.metadata} /></div></article>)}</div></div>
        {!ragEvents.length && <p className="text-sm text-slate-500">No detailed RAG stages were recorded for this older trace.</p>}
        <div><h3 className="font-semibold">LLM calls</h3><div className="mt-3 grid gap-3 md:grid-cols-2">{(selected.llm_calls || []).map((call) => <div key={call.call_id} className="rounded border p-3 text-sm"><p className="font-medium">{call.provider} / {call.model}</p><p className="mt-1 text-slate-500">{call.kind} · {duration(call.duration_ms)} · {number(call.total_tokens)} tokens</p><div className="mt-2"><Badge value={call.status} /></div></div>)}</div></div>
      </section>}
    </div>
  )
}
