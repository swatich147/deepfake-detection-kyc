import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authSlice'
import { sessionsApi, analysisApi } from '../api/client'

interface Session {
  id: string
  external_reference: string
  applicant_name: string
  status: string
  verdict: string | null
  overall_score: number | null
  created_at: string
}

interface Stats {
  summary: {
    total_sessions: number
    avg_score: number
  }
  verdict_breakdown: Record<string, number>
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  
  const [sessions, setSessions] = useState<Session[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    loadData()
  }, [])
  
  const loadData = async () => {
    try {
      const [sessionsRes, statsRes] = await Promise.all([
        sessionsApi.list({ page_size: 10 }),
        analysisApi.getStats(),
      ])
      setSessions(sessionsRes.results)
      setStats(statsRes)
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }
  
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      recording: 'bg-blue-100 text-blue-800',
      processing: 'bg-purple-100 text-purple-800',
      completed: 'bg-green-100 text-green-800',
      flagged: 'bg-red-100 text-red-800',
      failed: 'bg-gray-100 text-gray-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }
  
  const getVerdictColor = (verdict: string | null) => {
    if (!verdict) return ''
    const colors: Record<string, string> = {
      genuine: 'text-green-600',
      suspicious: 'text-yellow-600',
      fake: 'text-red-600',
    }
    return colors[verdict] || ''
  }
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-gray-900">KYC Dashboard</h1>
            <p className="text-sm text-gray-600">{user?.organization.name}</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-gray-600">{user?.email}</span>
            <button onClick={handleLogout} className="btn btn-secondary">
              Logout
            </button>
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500">Total Sessions</h3>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {stats?.summary.total_sessions || 0}
            </p>
          </div>
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500">Genuine</h3>
            <p className="text-3xl font-bold text-green-600 mt-2">
              {stats?.verdict_breakdown.genuine || 0}
            </p>
          </div>
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500">Suspicious</h3>
            <p className="text-3xl font-bold text-yellow-600 mt-2">
              {stats?.verdict_breakdown.suspicious || 0}
            </p>
          </div>
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500">Fake Detected</h3>
            <p className="text-3xl font-bold text-red-600 mt-2">
              {stats?.verdict_breakdown.fake || 0}
            </p>
          </div>
        </div>
        
        {/* Action Button */}
        <div className="mb-8">
          <Link to="/kyc/new" className="btn btn-primary">
            + New KYC Session
          </Link>
        </div>
        
        {/* Recent Sessions */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Sessions</h2>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Reference</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Applicant</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Verdict</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Score</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Date</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4 font-mono text-sm">
                      {session.external_reference || session.id.slice(0, 8)}
                    </td>
                    <td className="py-3 px-4">{session.applicant_name || '-'}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(session.status)}`}>
                        {session.status}
                      </span>
                    </td>
                    <td className={`py-3 px-4 font-medium ${getVerdictColor(session.verdict)}`}>
                      {session.verdict || '-'}
                    </td>
                    <td className="py-3 px-4">
                      {session.overall_score !== null
                        ? `${(session.overall_score * 100).toFixed(1)}%`
                        : '-'}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-500">
                      {new Date(session.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      <Link
                        to={`/sessions/${session.id}`}
                        className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
                
                {sessions.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-gray-500">
                      No sessions yet. Start a new KYC session.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}
