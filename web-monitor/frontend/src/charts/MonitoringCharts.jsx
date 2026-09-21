import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function tipStyle() {
  return {
    background: '#162033',
    border: '1px solid #243149',
    borderRadius: 8,
    fontSize: 12,
  }
}

export function ResponseTimeChart({ data }) {
  const rows = (data || []).map((d) => ({
    ...d,
    label: d.timestamp ? new Date(d.timestamp).toLocaleTimeString() : '',
  }))

  if (!rows.length) {
    return <div className="empty"><p>Not enough data</p></div>
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={rows}>
        <defs>
          <linearGradient id="rtFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2ec4b6" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#2ec4b6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#243149" strokeDasharray="3 3" />
        <XAxis dataKey="label" tick={{ fill: '#6b7f9c', fontSize: 11 }} minTickGap={40} />
        <YAxis tick={{ fill: '#6b7f9c', fontSize: 11 }} unit=" ms" width={56} />
        <Tooltip contentStyle={tipStyle()} />
        <Area type="monotone" dataKey="response_time" stroke="#2ec4b6" fill="url(#rtFill)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function UptimeBars({ windows }) {
  const rows = [
    { name: '1 Hour', value: windows?.['1h'] },
    { name: '6 Hours', value: windows?.['6h'] },
    { name: '24 Hours', value: windows?.['24h'] },
    { name: '7 Days', value: windows?.['7d'] },
    { name: '30 Days', value: windows?.['30d'] },
  ].map((r) => ({ ...r, display: r.value == null ? 0 : r.value, hasData: r.value != null }))

  if (!rows.some((r) => r.hasData)) {
    return <div className="empty"><p>Not enough data</p></div>
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={rows}>
        <CartesianGrid stroke="#243149" strokeDasharray="3 3" />
        <XAxis dataKey="name" tick={{ fill: '#6b7f9c', fontSize: 11 }} />
        <YAxis domain={[0, 100]} tick={{ fill: '#6b7f9c', fontSize: 11 }} unit="%" width={48} />
        <Tooltip
          contentStyle={tipStyle()}
          formatter={(value, _n, item) => [
            item.payload.hasData ? `${Number(value).toFixed(2)}%` : 'Not enough data',
            'Uptime',
          ]}
        />
        <Bar dataKey="display" fill="#3dd68c" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function StatusCodeChart({ distribution }) {
  const rows = Object.entries(distribution || {}).map(([code, count]) => ({ code, count }))
  if (!rows.length) {
    return <div className="empty"><p>Not enough data</p></div>
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={rows}>
        <CartesianGrid stroke="#243149" strokeDasharray="3 3" />
        <XAxis dataKey="code" tick={{ fill: '#6b7f9c', fontSize: 11 }} />
        <YAxis tick={{ fill: '#6b7f9c', fontSize: 11 }} width={40} />
        <Tooltip contentStyle={tipStyle()} />
        <Bar dataKey="count" fill="#5b8def" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function StatusTimeline({ points }) {
  if (!points?.length) {
    return <div className="empty"><p>Not enough data</p></div>
  }
  return (
    <div className="timeline" title="Status timeline (chronological)">
      {points.map((p, idx) => (
        <div
          key={`${p.timestamp}-${idx}`}
          className={`timeline-cell ${(p.status || 'unknown').toLowerCase()}`}
          title={`${p.timestamp || ''} — ${p.status}${p.status_code ? ` (${p.status_code})` : ''}`}
        />
      ))}
    </div>
  )
}
