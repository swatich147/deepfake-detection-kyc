import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { sessionsApi, analysisApi } from '../api/client'

interface SessionDetail {
  id: string
  external_reference: string
  applicant_name: string
  status: string
  video_duration_ms: number
  analysis: {
    overall_score: number
    verdict: string
    face_manipulation_score: number
    lipsync_score: number
    rppg_quality: number
    rppg_heart_rate: number
    av_correlation_score: number
    frames_analyzed: number
    processing_time_ms: number
    model_versions: Record<string, string>
  } | null
  created_at: string
  completed_at: string
}

interface FrameScore {
  frame_number: number
  timestamp_ms: number
  face_detected: boolean
  manipulation_score: number
  is_anomaly: boolean
}

export default function SessionReview() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  
  const [session, setSession] = useState<SessionDetail | null>(null)
  const [frames, setFrames] = useState<FrameScore[]>([])
  const [loading, setLoading] = useState(true)
  const [showAllFrames, setShowAllFrames] = useState(false)
  
  useEffect(() => {
    loadSession()
  }, [id])
  
  const loadSession = async () => {
    if (!id) return
    
    try {
      const [sessionData, framesData] = await Promise.all([
        sessionsApi.get(id),
        analysisApi.getFrames(id, { anomalies_only: !showAllFrames }),
      ])
      setSession(sessionData)
      setFrames(framesData.frames || [])
    } catch (err) {
      console.error('Failed to load session:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const getVerdictStyle = (verdict: string) => {
    switch (verdict) {
      case 'genuine':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'suspicious':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'fake':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }
  
  const getScoreColor = (score: number) => {
    if (score < 0.3) return 'text-green-600'
    if (score < 0.7) return 'text-yellow-600'
    return 'text-red-600'
  }
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    )
  }
  
  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Session not found</p>
          <Link to="/dashboard" className="btn btn-primary">Back to Dashboard</Link>
        </div>
      </div>
    )
  }
  
  const analysis = session.analysis
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Session Review</h1>
            <p className="text-sm text-gray-600 font-mono">{session.id}</p>
          </div>
          <button onClick={() => navigate('/dashboard')} className="btn btn-secondary">
            Back to Dashboard
          </button>
          {id && (
            <button
              onClick={() => sessionsApi.exportJson(id)}
              className="btn btn-secondary"
            >
              Export JSON
            </button>
          )}
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Verdict Banner */}
        {analysis && (
          <div className={`p-6 rounded-lg border-2 mb-8 ${getVerdictStyle(analysis.verdict)}`}>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold capitalize">{analysis.verdict}</h2>
                <p className="text-sm opacity-75">
                  Confidence Score: {((1 - analysis.overall_score) * 100).toFixed(1)}%
                </p>
              </div>
              <div className="text-right">
                <p className={`text-4xl font-bold ${getScoreColor(analysis.overall_score)}`}>
                  {(analysis.overall_score * 100).toFixed(1)}%
                </p>
                <p className="text-sm opacity-75">Risk Score</p>
              </div>
            </div>
          </div>
        )}
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Session Info */}
          <div className="lg:col-span-1 space-y-6">
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Session Details</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-gray-500">Reference</dt>
                  <dd className="font-medium">{session.external_reference || '-'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Applicant</dt>
                  <dd className="font-medium">{session.applicant_name || '-'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Status</dt>
                  <dd className="font-medium capitalize">{session.status}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Duration</dt>
                  <dd className="font-medium">
                    {session.video_duration_ms
                      ? `${(session.video_duration_ms / 1000).toFixed(1)}s`
                      : '-'}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Created</dt>
                  <dd className="font-medium">
                    {new Date(session.created_at).toLocaleString()}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Completed</dt>
                  <dd className="font-medium">
                    {session.completed_at
                      ? new Date(session.completed_at).toLocaleString()
                      : '-'}
                  </dd>
                </div>
              </dl>
            </div>
            
            {analysis && (
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Model Versions</h3>
                <dl className="space-y-2 text-sm">
                  {Object.entries(analysis.model_versions).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <dt className="text-gray-500">{key}</dt>
                      <dd className="font-mono">{value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </div>
          
          {/* Analysis Scores */}
          <div className="lg:col-span-2 space-y-6">
            {analysis && (
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Detection Scores</h3>
                <div className="grid grid-cols-2 gap-6">
                  {/* Face Manipulation */}
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm text-gray-500">Face Manipulation</span>
                      <span className={`font-medium ${getScoreColor(analysis.face_manipulation_score)}`}>
                        {(analysis.face_manipulation_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          analysis.face_manipulation_score < 0.3 ? 'bg-green-500' :
                          analysis.face_manipulation_score < 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${analysis.face_manipulation_score * 100}%` }}
                      />
                    </div>
                  </div>
                  
                  {/* Lip Sync */}
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm text-gray-500">Lip-Sync Mismatch</span>
                      <span className={`font-medium ${getScoreColor(analysis.lipsync_score)}`}>
                        {(analysis.lipsync_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          analysis.lipsync_score < 0.3 ? 'bg-green-500' :
                          analysis.lipsync_score < 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${analysis.lipsync_score * 100}%` }}
                      />
                    </div>
                  </div>
                  
                  {/* rPPG Quality */}
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm text-gray-500">Physiological Signal (rPPG)</span>
                      <span className="font-medium text-gray-700">
                        {(analysis.rppg_quality * 100).toFixed(1)}% quality
                      </span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500"
                        style={{ width: `${analysis.rppg_quality * 100}%` }}
                      />
                    </div>
                    {analysis.rppg_heart_rate && (
                      <p className="text-xs text-gray-500 mt-1">
                        Detected heart rate: {analysis.rppg_heart_rate.toFixed(0)} BPM
                      </p>
                    )}
                  </div>
                  
                  {/* AV Correlation */}
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm text-gray-500">Audio-Visual Correlation</span>
                      <span className={`font-medium ${getScoreColor(analysis.av_correlation_score)}`}>
                        {(analysis.av_correlation_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          analysis.av_correlation_score < 0.3 ? 'bg-green-500' :
                          analysis.av_correlation_score < 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${analysis.av_correlation_score * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
                
                <div className="mt-6 pt-4 border-t flex justify-between text-sm text-gray-500">
                  <span>Frames analyzed: {analysis.frames_analyzed}</span>
                  <span>Processing time: {analysis.processing_time_ms}ms</span>
                </div>
              </div>
            )}
            
            {/* Frame Timeline */}
            <div className="card">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Frame Analysis</h3>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={showAllFrames}
                    onChange={(e) => {
                      setShowAllFrames(e.target.checked)
                      loadSession()
                    }}
                    className="rounded"
                  />
                  Show all frames
                </label>
              </div>
              
              {frames.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 px-3">Frame</th>
                        <th className="text-left py-2 px-3">Time</th>
                        <th className="text-left py-2 px-3">Face</th>
                        <th className="text-left py-2 px-3">Score</th>
                        <th className="text-left py-2 px-3">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {frames.slice(0, 20).map((frame) => (
                        <tr key={frame.frame_number} className="border-b hover:bg-gray-50">
                          <td className="py-2 px-3">{frame.frame_number}</td>
                          <td className="py-2 px-3">{(frame.timestamp_ms / 1000).toFixed(1)}s</td>
                          <td className="py-2 px-3">
                            {frame.face_detected ? (
                              <span className="text-green-600">✓</span>
                            ) : (
                              <span className="text-red-600">✗</span>
                            )}
                          </td>
                          <td className={`py-2 px-3 font-medium ${getScoreColor(frame.manipulation_score)}`}>
                            {(frame.manipulation_score * 100).toFixed(1)}%
                          </td>
                          <td className="py-2 px-3">
                            {frame.is_anomaly && (
                              <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">
                                Anomaly
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  
                  {frames.length > 20 && (
                    <p className="text-sm text-gray-500 mt-2 text-center">
                      Showing 20 of {frames.length} frames
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">
                  No frame data available
                </p>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
