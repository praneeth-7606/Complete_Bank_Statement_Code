import { useCallback, useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, Clock3, DollarSign, RefreshCw, Server, Sparkles, Zap } from 'lucide-react'
import api from '../services/api'

const number = (value) => Number(value || 0).toLocaleString('en-IN')
const money = (value) => `$${Number(value || 0).toFixed(Number(value || 0) < 0.01 ? 5 : 4)}`
const duration = (value) => Number(value || 0) < 1000 ? `${Math.round(value || 0)}ms` : `${(Number(value || 0) / 1000).toFixed(1)}s`
const time = (value) => value ? new Date(value).toLocaleString() : '—'

function Metric({ label, value, detail, icon: Icon, tone = 'indigo' }) {
  const tones = {
    indigo: 'from-indigo-500 to-violet-500',
    emerald: 'from-emerald-500 to-teal-500',
    amber: 'from-amber-500 to-orange-500',
    rose: 'from-rose-500 to-pink-500',
  }
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <span className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${tones[tone]} text-white`}><Icon size={18} /></span>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">live telemetry</span>
      </div>
      <p className="mt-5 text-xs font-semibold uppercase tracking-wider text-neutral-500">{label}</p>
      <p className="mt-1 text-2xl font-black text-neutral-900">{value}</p>
      {detail && <p className="mt-1 text-xs text-neutral-500">{detail}</p>}
    </div>
  )
}

function StatusBadge({ status }) {
  const color = status === 'success' ? 'bg-emerald-100 text-emerald-700' : status === 'running' ? 'bg-blue-100 text-blue-700' : 'bg-rose-100 text-rose-700'
  return <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${color}`}>{status || 'unknown'}</span>
}

export default function Observability() {
  const [summary, setSummary] = useState(null)
  const [traces, setTraces] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [hours, setHours] = useState(24)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [summaryResponse, tracesResponse] = await Promise.all([
        api.get(`/observability/summary?hours=${hours}`),
        api.get(`/observability/traces?hours=${hours}&limit=50`),
      ])
      setSummary(summaryResponse.data)
      const nextTraces = tracesResponse.data.traces || []
      setTraces(nextTraces)
      if (selected?.trace_id) {
        const detail = await api.get(`/observability/traces/${selected.trace_id}`)
        setSelected(detail.data)
      } else if (nextTraces[0]?.trace_id) {
        const detail = await api.get(`/observability/traces/${nextTraces[0].trace_id}`)
        setSelected(detail.data)
      }
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Observability data is unavailable. Run a statement or chat request first.')
    } finally {
      setLoading(false)
    }
  }, [hours, selected?.trace_id])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    const timer = window.setInterval(load, 10000)
    return () => window.clearInterval(timer)
  }, [load])

  const selectedEvents = useMemo(() => selected?.events || [], [selected])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-3xl bg-gradient-to-r from-slate-950 via-indigo-950 to-slate-900 p-7 text-white shadow-xl sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-indigo-300"><Activity size={15} /> Application observability</div>
          <h1 className="text-3xl font-black">System flight recorder</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">See how statement extraction, categorization, RAG, vector search, and provider fallbacks behave for your account.</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={hours} onChange={(event) => setHours(Number(event.target.value))} className="rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm text-white outline-none">
            <option value={1} className="text-black">Last hour</option>
            <option value={24} className="text-black">Last 24 hours</option>
            <option value={168} className="text-black">Last 7 days</option>
          </select>
          <button onClick={load} className="flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-bold text-slate-900 hover:bg-indigo-50"><RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Refresh</button>
        </div>
      </div>

      {error && <div className="flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"><AlertTriangle size={18} />{error}</div>}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Metric label="Requests" value={number(summary?.requests)} detail={`${number(summary?.failed_requests)} failed`} icon={Server} />
        <Metric label="LLM calls" value={number(summary?.llm_calls)} detail={`${number(summary?.fallback_calls)} fallbacks`} icon={Sparkles} tone="emerald" />
        <Metric label="Tokens" value={number(summary?.total_tokens)} detail={`${number(summary?.input_tokens)} in · ${number(summary?.output_tokens)} out`} icon={Zap} tone="amber" />
        <Metric label="Estimated cost" value={money(summary?.estimated_cost_usd)} detail={`${duration(summary?.total_duration_ms)} aggregate runtime`} icon={DollarSign} tone="rose" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm xl:col-span-1">
          <div className="mb-4 flex items-center justify-between"><div><h2 className="font-bold text-neutral-900">Provider usage</h2><p className="text-xs text-neutral-500">Calls, failures, fallbacks and spend</p></div><Clock3 size={18} className="text-neutral-400" /></div>
          <div className="space-y-4">
            {(summary?.by_provider || []).map((provider) => {
              const share = Math.min(100, (provider.calls / Math.max(summary?.llm_calls || 1, 1)) * 100)
              return <div key={provider.provider}><div className="mb-1 flex justify-between text-xs"><span className="font-semibold capitalize text-neutral-800">{provider.provider}</span><span className="text-neutral-500">{provider.calls} calls · {money(provider.cost_usd)}</span></div><div className="h-2 rounded-full bg-neutral-100"><div className="h-2 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400" style={{ width: `${share}%` }} /></div><p className="mt-1 text-[11px] text-neutral-500">{provider.failed} failed · {provider.fallbacks} fallback · {number(provider.tokens)} tokens</p></div>
            })}
            {!summary?.by_provider?.length && <p className="py-8 text-center text-sm text-neutral-500">No provider calls recorded yet.</p>}
          </div>
        </section>

        <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm xl:col-span-2">
          <div className="flex items-center justify-between border-b border-neutral-100 p-5"><div><h2 className="font-bold text-neutral-900">Recent traces</h2><p className="text-xs text-neutral-500">Every upload, RAG chat, and investment request is correlated by trace ID.</p></div><span className="text-xs font-semibold text-neutral-400">{traces.length} shown</span></div>
          <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-neutral-50 text-[10px] uppercase tracking-wider text-neutral-500"><tr><th className="px-5 py-3">Time</th><th className="px-5 py-3">Route</th><th className="px-5 py-3">Duration</th><th className="px-5 py-3">LLM</th><th className="px-5 py-3">Status</th></tr></thead><tbody>{traces.map((trace) => <tr key={trace.trace_id} onClick={async () => setSelected((await api.get(`/observability/traces/${trace.trace_id}`)).data)} className="cursor-pointer border-t border-neutral-100 hover:bg-indigo-50/40"><td className="whitespace-nowrap px-5 py-3 text-xs text-neutral-500">{time(trace.started_at)}</td><td className="px-5 py-3 font-medium text-neutral-800">{trace.route}</td><td className="px-5 py-3 font-mono text-xs">{duration(trace.duration_ms)}</td><td className="px-5 py-3 font-mono text-xs">{trace.metrics?.llm_calls || 0}</td><td className="px-5 py-3"><StatusBadge status={trace.status} /></td></tr>)}</tbody></table></div>
          {!traces.length && <p className="p-10 text-center text-sm text-neutral-500">Run an upload or chat request to populate the flight recorder.</p>}
        </section>
      </div>

      {selected && <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><div className="flex flex-col gap-2 border-b border-neutral-100 pb-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-bold text-neutral-900">Trace detail</h2><p className="font-mono text-[11px] text-neutral-500">{selected.trace_id} · request {selected.request_id}</p></div><StatusBadge status={selected.status} /></div><div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5">{[['Events', selected.metrics?.event_count || 0], ['LLM calls', selected.metrics?.llm_calls || 0], ['Tokens', number(selected.metrics?.total_tokens)], ['Cost', money(selected.metrics?.estimated_cost_usd)], ['Runtime', duration(selected.duration_ms)]].map(([label, value]) => <div key={label} className="rounded-xl bg-neutral-50 p-3"><p className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">{label}</p><p className="mt-1 font-mono text-sm font-bold text-neutral-900">{value}</p></div>)}</div><div className="mt-5 space-y-3">{selectedEvents.map((event) => <div key={event.event_id} className="flex items-start justify-between gap-4 rounded-xl border border-neutral-100 p-3"><div><p className="text-sm font-semibold text-neutral-800">{event.name}</p><p className="text-xs text-neutral-500">{event.kind} · {event.metadata?.provider || 'application event'}{event.metadata?.fallback ? ' · fallback' : ''}</p></div><div className="text-right"><StatusBadge status={event.status} /><p className="mt-1 font-mono text-[11px] text-neutral-500">{duration(event.duration_ms)}</p></div></div>)}{!selectedEvents.length && <p className="py-6 text-center text-sm text-neutral-500">No child events recorded for this trace.</p>}</div></section>}
    </div>
  )
}
