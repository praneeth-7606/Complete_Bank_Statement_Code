import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    
    // Handle 401 Unauthorized - redirect to login
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

export const statementAPI = {
  // Process single statement
  processSingleStatement: async (file, password, uploadId = null) => {
    const formData = new FormData();
    formData.append('statement_pdf', file);
    formData.append('password', password);
    if (uploadId) {
      formData.append('upload_id', uploadId);
    }
    
    const response = await api.post('/process-statement/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Process multiple statements
  processMultipleStatements: async (files, passwords, uploadId = null) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('statement_pdfs', file);
    });
    formData.append('passwords', passwords.join(','));
    if (uploadId) {
      formData.append('upload_id', uploadId);
    }
    
    const response = await api.post('/process-multiple-statements/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export const chatAPI = {
  // Send chat query
  sendQuery: async (query) => {
    const response = await api.post('/chat', { query });
    return response.data;
  },
};

export const correctionAPI = {
  // Submit correction
  submitCorrection: async (keyword, category) => {
    const response = await api.post('/correct-transaction/', {
      transaction_description_keyword: keyword,
      correct_category: category,
    });
    return response.data;
  },
};

// NEW: Statements API
export const statementsAPI = {
  // Get all statements
  getAllStatements: async () => {
    const response = await api.get('/statements/');
    return response.data;
  },

  // Get specific statement details
  getStatementDetails: async (uploadId) => {
    const response = await api.get(`/statement/${uploadId}`);
    return response.data;
  },

  // Delete statement
  deleteStatement: async (uploadId) => {
    const response = await api.delete(`/statement/${uploadId}`);
    return response.data;
  },

  // Check background task status
  getBackgroundStatus: async (uploadId) => {
    const response = await api.get(`/background-status/${uploadId}`);
    return response.data;
  },
};

export default api;
