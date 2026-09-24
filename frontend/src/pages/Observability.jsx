import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'

const number = (value) => Number(value || 0).toLocaleString('en-IN')
const duration = (value) => `${(Number(value || 0) / 1000).toFixed(2)}s`
const percent = (value) => value == null ? 'Not evaluated' : `${(value * 100).toFixed(1)}%`

function Badge({ value }) {
  const color = ['passed', 'success', 'exported'].includes(value) ? 'bg-emerald-100 text-emerald-800'
    : value === 'failed' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'
  return <span className={`rounded-full px-2 py-1 text-xs ${color}`}>{(value || 'unknown').replaceAll('_', ' ')}</span>
}

export default function Observability() {
  const [summary, setSummary] = useState(null)
  const [configuration, setConfiguration] = useState(null)
  const [traces, setTraces] = useState([])
  const [selected, setSelected] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [hours, setHours] = useState(24)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const pending = useRef(null)
  const sequence = useRef(0)

  const getWithRetry = async (url, retries = 1) => {
    try {
      return await api.get(url)
    } catch (err) {
      if (retries > 0 && !err.response) {
        await new Promise((r) => setTimeout(r, 2500))
        return api.get(url)
      }
      throw err
    }
  }

  const load = useCallback(async () => {
    pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    const revision = ++sequence.current
    setLoading(true)
    try {
      const options = { signal: controller.signal }
      const [summaryResponse, traceResponse, configResponse] = await Promise.all([
        getWithRetry(`/observability/summary?hours=${hours}`),
        getWithRetry(`/observability/traces?hours=${hours}&limit=50`),
        api.get('/observability/configuration', options),
      ])
      const next = traceResponse.data.traces || []
      const id = selectedId || next[0]?.trace_id
      const detail = id ? await api.get(`/observability/traces/${id}`, options) : null
      if (revision !== sequence.current) return
      setSummary(summaryResponse.data)
      setTraces(next)
      setConfiguration(configResponse.data)
      setSelected(detail?.data || null)
      setError('')
    } catch (err) {
      if (!controller.signal.aborted) setError(err.response?.data?.detail || 'Monitoring data could not be loaded. Try Refresh.')
    } finally {
      if (revision === sequence.current) setLoading(false)
    }
  }, [hours, selectedId])

  useEffect(() => {
    load()
    const timer = window.setInterval(load, 15000)
    return () => { window.clearInterval(timer); pending.current?.abort() }
  }, [load])

  const metrics = [['Recorded executions', number(summary?.requests)], ['LLM calls', number(summary?.llm_calls)],
    ['Reported tokens', number(summary?.total_tokens)], ['Estimated token cost', `$${Number(summary?.estimated_cost_usd || 0).toFixed(5)}`],
    ['Check pass rate', percent(summary?.evaluation_pass_rate)]]

  return (
    <div className="space-y-6 text-slate-900">
      <header className="rounded-2xl bg-slate-900 p-6 text-white">
        <h1 className="text-2xl font-bold">Monitoring and evaluation</h1>
        <p className="mt-2 text-sm text-slate-300">Your account’s processing stages, provider calls, storage checks and benchmark results.</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label htmlFor="monitoring-window">Time window</label>
          <select id="monitoring-window" value={hours} onChange={(event) => { setHours(Number(event.target.value)); setSelectedId(null) }} className="rounded border border-white/30 bg-white/10 p-2 text-white [&>option]:text-slate-900">
            <option value={1}>Last hour</option><option value={24}>Last 24 hours</option><option value={168}>Last 7 days</option>
          </select>
          <button onClick={load} disabled={loading} style={{ backgroundColor: '#ffffff', color: '#0f172a' }} className="rounded px-4 py-2 font-medium disabled:opacity-60">{loading ? 'Loading…' : 'Refresh'}</button>
          <Link to="/observability/rag" className="rounded border border-white/30 px-4 py-2 text-sm font-medium hover:bg-white/10">RAG evaluation</Link>
          {configuration?.langfuse_dashboard_url && <a href={configuration.langfuse_dashboard_url} target="_blank" rel="noopener noreferrer" className="underline">Open Langfuse workspace</a>}
        </div>
      </header>
      {error && <p role="alert" className="rounded bg-amber-50 p-4 text-amber-900">{error}</p>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">{metrics.map(([label, value]) => <div key={label} className="rounded-xl border bg-white p-4"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-xl font-semibold">{value}</p></div>)}</div>
      <section className="rounded-xl border bg-white p-4 text-sm text-slate-600">
        <p>Consistency checks do not prove source completeness. Accuracy requires manually verified benchmark answers.</p>
        <p className="mt-2">{number(summary?.evaluation_failures)} failed checks · {number(summary?.evaluation_not_measured)} not evaluated. Costs are estimates; missing usage and page-based OCR charges may be absent.</p>
        <p className="mt-2">Langfuse: {configuration?.langfuse_configured ? 'credentials configured; inspect score delivery below' : 'not configured — local monitoring is available'}.</p>
        {summary?.sample_limit_reached && <p className="mt-2 text-amber-800">Summary covers the latest {summary.sample_limit} executions. Choose a shorter window.</p>}
      </section>
      <section className="rounded-xl border bg-white p-4">
        <h2 className="font-semibold">Provider usage</h2>
        {(summary?.by_provider || []).map((provider) => <p key={provider.provider} className="mt-2 text-sm">{provider.provider}: {number(provider.calls)} calls · {number(provider.failed)} failed · {number(provider.fallbacks)} fallbacks · {number(provider.tokens)} tokens</p>)}
        {!summary?.by_provider?.length && <p className="mt-2 text-sm text-slate-500">No provider calls in this window.</p>}
      </section>
      <section className="overflow-x-auto rounded-xl border bg-white">
        <h2 className="p-4 font-semibold">Recent executions</h2>
        <table className="w-full text-left text-sm"><thead className="bg-slate-50"><tr>{['Started', 'Operation', 'Duration', 'LLM calls', 'Execution status'].map((label) => <th key={label} className="p-3">{label}</th>)}</tr></thead>
          <tbody>{traces.map((item) => <tr key={item.trace_id} className="border-t"><td className="p-3">{new Date(item.started_at).toLocaleString()}</td>
            <td className="p-3"><button onClick={() => setSelectedId(item.trace_id)} className="text-indigo-700 underline">{item.operation}</button></td>
            <td className="p-3">{duration(item.duration_ms)}</td><td className="p-3">{number(item.metrics?.llm_calls)}</td><td className="p-3"><Badge value={item.status} /></td></tr>)}</tbody>
        </table>
        {!traces.length && <p className="p-6 text-slate-500">No executions in this window. Upload a statement or publish a benchmark run.</p>}
      </section>
      {selected && <section className="space-y-4 rounded-xl border bg-white p-5">
        <h2 className="font-semibold">Execution details</h2>
        <p className="break-all text-xs text-slate-500">Local trace: {selected.trace_id}<br />Distributed trace: {selected.otel_trace_id || 'Unavailable'}</p>
        {selected.parent_trace_id && <p className="text-sm">Background work for upload trace <button className="text-indigo-700 underline" onClick={() => setSelectedId(selected.parent_trace_id)}>{selected.parent_trace_id}</button></p>}
        <p className="text-sm">Langfuse score delivery: <Badge value={selected.score_export_status} /></p>
        <h3 className="font-semibold">Evaluation checks</h3>
        <div className="grid gap-3 md:grid-cols-2">{(selected.evaluation_scores || []).map((item, index) => <div key={`${item.name}-${index}`} className="flex justify-between gap-4 rounded border p-3">
          <div><p className="text-sm">{item.name.replaceAll('_', ' ')}</p><p className="text-xs text-slate-500">{item.value == null ? 'Requires verified evidence' : `Score: ${Number(item.value).toFixed(3)}`}</p></div>
          <Badge value={item.passed == null ? 'not_evaluated' : item.passed ? 'passed' : 'failed'} />
        </div>)}</div>
        {!selected.evaluation_scores?.length && <p className="text-sm text-slate-500">No evaluation scores for this execution.</p>}
        <h3 className="font-semibold">Workflow events</h3>
        {(selected.events || []).map((event) => <div key={event.event_id} className="flex justify-between gap-3 border-t py-3 text-sm"><div>{event.name}<p className="text-xs text-slate-500">{event.kind} · {duration(event.duration_ms)}</p></div><Badge value={event.status} /></div>)}
      </section>}
    </div>
  )
}
