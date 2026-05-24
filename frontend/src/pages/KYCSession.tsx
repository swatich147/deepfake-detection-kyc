import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { sessionsApi } from '../api/client'
import { useAuthStore } from '../store/authSlice'

interface Session {
  id: string
  websocket_url: string
  challenge?: {
    type: string
    instructions: string[]
    nonce?: string
  }
}

type Phase = 'setup' | 'preview' | 'recording' | 'processing' | 'complete'

export default function KYCSession() {
  const navigate = useNavigate()
  const accessToken = useAuthStore((state) => state.accessToken)
  
  const [phase, setPhase] = useState<Phase>('setup')
  const [session, setSession] = useState<Session | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [wsStatus, setWsStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const [chunkCount, setChunkCount] = useState(0)
  const [recordingTime, setRecordingTime] = useState(0)
  const [consentGiven, setConsentGiven] = useState(false)
  
  const videoRef = useRef<HTMLVideoElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const timerRef = useRef<number | null>(null)
  
  // Create session
  const handleStartSession = async () => {
    try {
      setError(null)
      const data = await sessionsApi.create({
        challenge_type: 'random_movement',
      })
      setSession(data)
      setPhase('preview')
      
      // Start camera preview
      await startCamera()
      
      // Connect WebSocket
      connectWebSocket(data)
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Failed to create session')
    }
  }
  
  // Start camera
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        },
        audio: true,
      })
      
      streamRef.current = stream
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
    } catch (err) {
      setError('Failed to access camera. Please grant permission.')
      throw err
    }
  }
  
  // Connect WebSocket
  const connectWebSocket = (sessionData: Session) => {
    if (wsRef.current) return
    
    setWsStatus('connecting')
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/video-stream/${sessionData.id}/?token=${accessToken}`
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      setWsStatus('connected')
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      switch (data.type) {
        case 'chunk_received':
          setChunkCount(data.chunk_index + 1)
          break
        case 'processing_started':
          setPhase('processing')
          break
        case 'analysis_complete':
          setPhase('complete')
          setTimeout(() => {
            navigate(`/sessions/${sessionData.id}`)
          }, 2000)
          break
        case 'error':
          setError(data.message)
          break
      }
    }
    
    ws.onerror = () => {
      setError('WebSocket connection failed')
    }
    
    ws.onclose = () => {
      setWsStatus('disconnected')
    }
    
    wsRef.current = ws
  }
  
  // Start recording
  const handleStartRecording = () => {
    if (!streamRef.current || !wsRef.current) return
    
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
      ? 'video/webm;codecs=vp9,opus'
      : 'video/webm'
    
    const recorder = new MediaRecorder(streamRef.current, {
      mimeType,
      videoBitsPerSecond: 2500000,
    })
    
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(event.data)
      }
    }
    
    mediaRecorderRef.current = recorder
    
    // Send start message
    wsRef.current.send(JSON.stringify({
      type: 'start_recording',
      timestamp: Date.now(),
      consent_given: consentGiven,
    }))
    
    // Start recording with 5-second chunks
    recorder.start(5000)
    setPhase('recording')
    
    // Start timer
    timerRef.current = window.setInterval(() => {
      setRecordingTime((t) => t + 1)
    }, 1000)
  }
  
  // Stop recording
  const handleStopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'stop_recording',
        timestamp: Date.now(),
        nonce: session?.challenge?.nonce,
      }))
    }
    
    if (timerRef.current) {
      clearInterval(timerRef.current)
    }
    
    // Stop camera
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
    }
    
    setPhase('processing')
  }
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
      }
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [])
  
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  
  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Video KYC Verification</h1>
          <button onClick={() => navigate('/dashboard')} className="btn btn-secondary">
            Back to Dashboard
          </button>
        </div>
        
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}
        
        <div className="card">
          {/* Video Preview */}
          <div className="relative aspect-video bg-black rounded-lg overflow-hidden mb-6">
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
            />
            
            {/* Status Badge */}
            <div className="absolute top-4 left-4">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                wsStatus === 'connected' ? 'bg-green-500 text-white' :
                wsStatus === 'connecting' ? 'bg-yellow-500 text-white' :
                'bg-gray-500 text-white'
              }`}>
                {wsStatus === 'connected' ? 'Connected' :
                 wsStatus === 'connecting' ? 'Connecting...' :
                 'Not Connected'}
              </span>
            </div>
            
            {/* Recording Indicator */}
            {phase === 'recording' && (
              <div className="absolute top-4 left-1/2 transform -translate-x-1/2">
                <span className="flex items-center px-4 py-2 bg-red-600 text-white rounded-full">
                  <span className="w-3 h-3 bg-white rounded-full animate-pulse mr-2"></span>
                  Recording - {formatTime(recordingTime)}
                </span>
              </div>
            )}
            
            {/* Chunks Counter */}
            {(phase === 'recording' || phase === 'processing') && (
              <div className="absolute top-4 right-4 bg-black/50 text-white px-3 py-1 rounded">
                Chunks: {chunkCount}
              </div>
            )}
            
            {/* Challenge Instructions */}
            {phase === 'recording' && session?.challenge?.instructions && (
              <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/70 text-white px-6 py-3 rounded-lg">
                <p className="text-lg font-medium text-center">
                  {session.challenge.instructions[Math.floor(recordingTime / 4) % session.challenge.instructions.length]}
                </p>
              </div>
            )}
            
            {/* Processing Overlay */}
            {phase === 'processing' && (
              <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
                <div className="text-center text-white">
                  <div className="animate-spin w-12 h-12 border-4 border-white border-t-transparent rounded-full mx-auto mb-4"></div>
                  <p className="text-lg">Analyzing video for deepfakes...</p>
                </div>
              </div>
            )}
            
            {/* Complete Overlay */}
            {phase === 'complete' && (
              <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
                <div className="text-center text-white">
                  <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-lg">Analysis Complete! Redirecting...</p>
                </div>
              </div>
            )}
          </div>
          
          {/* Controls */}
          <div className="flex justify-center gap-4">
            {phase === 'setup' && (
              <button onClick={handleStartSession} className="btn btn-primary px-8 py-3 text-lg">
                Start Verification
              </button>
            )}
            
            {phase === 'preview' && wsStatus === 'connected' && (
              <div className="flex flex-col items-center gap-4">
                <label className="flex items-start gap-3 max-w-md text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={consentGiven}
                    onChange={(e) => setConsentGiven(e.target.checked)}
                    className="mt-1 rounded"
                  />
                  <span>
                    I consent to a short video recording for identity verification demo purposes.
                    Data is stored locally in Docker volumes on this machine only.
                  </span>
                </label>
                <button
                  onClick={handleStartRecording}
                  disabled={!consentGiven}
                  className="btn btn-success px-8 py-3 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Begin Recording
                </button>
              </div>
            )}
            
            {phase === 'recording' && (
              <>
                <button onClick={handleStopRecording} className="btn btn-danger px-8 py-3 text-lg">
                  Stop & Submit
                </button>
                <p className="text-gray-500 self-center">
                  Record for at least 10 seconds
                </p>
              </>
            )}
          </div>
          
          {/* Instructions */}
          {phase === 'setup' && (
            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-medium text-blue-800 mb-2">Instructions</h3>
              <ul className="text-sm text-blue-700 list-disc list-inside space-y-1">
                <li>Ensure good lighting on your face</li>
                <li>Position yourself in the center of the frame</li>
                <li>Follow the on-screen prompts during recording</li>
                <li>Recording should be at least 10 seconds</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
