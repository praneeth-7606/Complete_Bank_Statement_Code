import { createContext, useState, useContext, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { API_BASE_URL } from '../services/api'

const AuthContext = createContext(null)
// 60s: free-tier backend sleeps when idle and needs ~50s to cold-start.
// Never fail a login just because the server was asleep.
const AUTH_REQUEST_TIMEOUT_MS = 60000

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(localStorage.getItem('access_token'))
  const navigate = useNavigate()

  const API_URL = API_BASE_URL

  // Set axios default configuration
  useEffect(() => {
    axios.defaults.withCredentials = true  // Enable credentials for CORS
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete axios.defaults.headers.common['Authorization']
    }
  }, [token])

  // Check if user is logged in on mount
  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('access_token')
      if (storedToken) {
        try {
          const response = await axios.get(`${API_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${storedToken}` },
            timeout: AUTH_REQUEST_TIMEOUT_MS
          })
          setUser(response.data)
          setToken(storedToken)
        } catch (error) {
          // Only clear tokens if it's an auth error (401), not connection error
          if (error.response && error.response.status === 401) {
            console.error('Auth token invalid:', error)
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            setToken(null)
            setUser(null)
          } else {
            // Connection error - keep token, backend might be starting
            console.warn('Backend connection failed, will retry:', error.message)
          }
        }
      }
      setLoading(false)
    }

    checkAuth()
  }, [])

  const signup = async (email, password, fullName) => {
    try {
      const response = await axios.post(`${API_URL}/auth/signup`, {
        email,
        password,
        full_name: fullName
      }, { timeout: AUTH_REQUEST_TIMEOUT_MS })
      
      const { access_token, refresh_token, user: userData } = response.data
      
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      setToken(access_token)
      setUser(userData)
      
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Signup failed'
      }
    }
  }

  const postWithWakeRetry = async (url, data) => {
    try {
      return await axios.post(url, data, { timeout: AUTH_REQUEST_TIMEOUT_MS })
    } catch (error) {
      // No response at all = server asleep or network blip. Wait for cold
      // start, then retry once before surfacing an error.
      if (!error.response) {
        await sleep(5000)
        return axios.post(url, data, { timeout: AUTH_REQUEST_TIMEOUT_MS })
      }
      throw error
    }
  }

  const login = async (email, password) => {
    try {
      const response = await postWithWakeRetry(`${API_URL}/auth/login`, {
        email,
        password
      })
      
      const { access_token, refresh_token, user: userData } = response.data
      
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      setToken(access_token)
      setUser(userData)
      
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed'
      }
    }
  }

  const logout = async () => {
    try {
      await axios.post(`${API_URL}/auth/logout`, null, { timeout: AUTH_REQUEST_TIMEOUT_MS })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('dashboardData')
      setToken(null)
      setUser(null)
      navigate('/login')
    }
  }

  const value = {
    user,
    loading,
    token,
    signup,
    login,
    logout,
    isAuthenticated: !!user
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
