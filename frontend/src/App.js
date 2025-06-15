import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');

function App() {
  const [urls, setUrls] = useState('');
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobResults, setJobResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [realTimeUpdates, setRealTimeUpdates] = useState([]);
  const wsRef = useRef(null);

  // WebSocket connection for real-time updates
  useEffect(() => {
    connectWebSocket();
    fetchJobs();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      wsRef.current = new WebSocket(`${WS_URL}/api/ws`);
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setRealTimeUpdates(prev => [...prev, data]);
        
        // Update jobs list when job status changes
        if (data.type === 'job_started' || data.type === 'job_completed' || data.type === 'job_failed') {
          fetchJobs();
        }
      };
      
      wsRef.current.onclose = () => {
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
    } catch (error) {
      console.error('WebSocket connection failed:', error);
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await axios.get(`${API}/jobs`);
      setJobs(response.data);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  const fetchJobResults = async (jobId) => {
    try {
      const response = await axios.get(`${API}/jobs/${jobId}/results`);
      setJobResults(response.data);
    } catch (error) {
      console.error('Error fetching job results:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!urls.trim()) return;

    setLoading(true);
    try {
      const urlList = urls.split('\n').filter(url => url.trim()).map(url => url.trim());
      const response = await axios.post(`${API}/scrape`, { urls: urlList });
      
      setUrls('');
      fetchJobs();
      setSelectedJob(response.data.id);
      
      // Clear previous real-time updates
      setRealTimeUpdates([]);
    } catch (error) {
      console.error('Error starting scraping job:', error);
      alert('Error starting scraping job: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleJobSelect = (job) => {
    setSelectedJob(job.id);
    fetchJobResults(job.id);
  };

  const getJobStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'text-yellow-600 bg-yellow-100';
      case 'in_progress': return 'text-blue-600 bg-blue-100';
      case 'completed': return 'text-green-600 bg-green-100';
      case 'failed': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const renderTable = (table, index) => {
    if (!table.rows || table.rows.length === 0) return null;
    
    return (
      <div key={index} className="mb-6 overflow-x-auto">
        <h4 className="text-lg font-semibold mb-2 text-gray-800">Table {index + 1}</h4>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {table.headers.map((header, headerIndex) => (
                  <th
                    key={headerIndex}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {table.rows.slice(0, 10).map((row, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-gray-50">
                  {table.headers.map((header, cellIndex) => (
                    <td key={cellIndex} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {row[header] || '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {table.rows.length > 10 && (
            <div className="bg-gray-50 px-6 py-3 text-sm text-gray-500">
              ... and {table.rows.length - 10} more rows
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderItems = (items) => {
    if (!items || items.length === 0) return null;
    
    return (
      <div className="mb-6">
        <h4 className="text-lg font-semibold mb-2 text-gray-800">Items Found ({items.length})</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.slice(0, 12).map((item, index) => (
            <div key={index} className="bg-white p-4 rounded-lg shadow-sm border">
              {item.image_url && (
                <img
                  src={item.image_url}
                  alt={item.title}
                  className="w-full h-32 object-cover rounded mb-2"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
              )}
              <h5 className="font-medium text-gray-900 mb-1">{item.title || 'No Title'}</h5>
              {item.price && (
                <p className="text-green-600 font-semibold mb-1">{item.price}</p>
              )}
              {item.description && (
                <p className="text-gray-600 text-sm">{item.description.substring(0, 100)}...</p>
              )}
            </div>
          ))}
        </div>
        {items.length > 12 && (
          <div className="text-center mt-4 text-gray-500">
            ... and {items.length - 12} more items
          </div>
        )}
      </div>
    );
  };

  const renderPrices = (prices) => {
    if (!prices || prices.length === 0) return null;
    
    const uniquePrices = prices.filter((price, index, self) => 
      index === self.findIndex(p => p.price === price.price)
    );
    
    return (
      <div className="mb-6">
        <h4 className="text-lg font-semibold mb-2 text-gray-800">Prices Found ({uniquePrices.length})</h4>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 p-4">
            {uniquePrices.slice(0, 20).map((price, index) => (
              <div key={index} className="bg-green-50 border border-green-200 rounded px-3 py-2">
                <div className="font-semibold text-green-700">{price.price}</div>
                <div className="text-xs text-gray-600">{price.selector}</div>
              </div>
            ))}
          </div>
          {uniquePrices.length > 20 && (
            <div className="bg-gray-50 px-4 py-2 text-sm text-gray-500">
              ... and {uniquePrices.length - 20} more prices
            </div>
          )}
        </div>
      </div>
    );
  };

  const selectedJobData = jobs.find(job => job.id === selectedJob);
  const currentJobUpdates = realTimeUpdates.filter(update => update.job_id === selectedJob);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Web Scraper Tool</h1>
          <p className="text-xl text-gray-600">Advanced e-commerce scraper for dynamic content</p>
        </div>

        {/* URL Input Form */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4 text-gray-800">Start New Scraping Job</h2>
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="urls" className="block text-sm font-medium text-gray-700 mb-2">
                URLs to Scrape (one per line)
              </label>
              <textarea
                id="urls"
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
                placeholder="https://example.com/product1&#10;https://example.com/product2&#10;https://example.com/product3"
                className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !urls.trim()}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {loading && (
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              {loading ? 'Starting Scraping...' : 'Start Scraping'}
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Jobs List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-800">Scraping Jobs</h2>
              <div className="space-y-3">
                {jobs.map((job) => (
                  <div
                    key={job.id}
                    onClick={() => handleJobSelect(job)}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedJob === job.id 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${getJobStatusColor(job.status)}`}>
                        {job.status.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(job.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-sm text-gray-700">
                      {job.total_urls} URLs • {job.processed_urls || 0} processed
                    </div>
                    {job.status === 'in_progress' && (
                      <div className="mt-2">
                        <div className="bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${((job.processed_urls || 0) / job.total_urls) * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                {jobs.length === 0 && (
                  <p className="text-gray-500 text-center py-4">No scraping jobs yet</p>
                )}
              </div>
            </div>
          </div>

          {/* Results Display */}
          <div className="lg:col-span-2">
            {selectedJobData && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-800">Job Results</h2>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getJobStatusColor(selectedJobData.status)}`}>
                    {selectedJobData.status.toUpperCase()}
                  </span>
                </div>

                {/* Real-time Updates */}
                {currentJobUpdates.length > 0 && selectedJobData.status === 'in_progress' && (
                  <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                    <h3 className="text-lg font-medium text-blue-800 mb-2">Live Updates</h3>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {currentJobUpdates.slice(-3).map((update, index) => (
                        <div key={index} className="text-sm text-blue-700">
                          {update.type === 'progress_update' && (
                            <span>✓ Scraped: {update.current_url}</span>
                          )}
                          {update.type === 'job_started' && (
                            <span>🚀 Job started with {update.total_urls} URLs</span>
                          )}
                          {update.type === 'job_completed' && (
                            <span>✅ Job completed with {update.total_results} results</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Results */}
                <div className="space-y-8">
                  {jobResults.map((result, index) => (
                    <div key={index} className="border-b border-gray-200 pb-6 last:border-b-0">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-medium text-gray-900">
                          {result.title || 'Untitled Page'}
                        </h3>
                        <a
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 text-sm"
                        >
                          View Source →
                        </a>
                      </div>
                      
                      {result.error ? (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                          <p className="text-red-700">Error: {result.error}</p>
                        </div>
                      ) : (
                        <div>
                          {result.tables && result.tables.length > 0 && (
                            <div className="mb-6">
                              <h4 className="text-lg font-semibold mb-2 text-gray-800">Tables Found ({result.tables.length})</h4>
                              {result.tables.map((table, tableIndex) => renderTable(table, tableIndex))}
                            </div>
                          )}
                          
                          {renderItems(result.items)}
                          {renderPrices(result.prices)}
                          
                          {(!result.tables || result.tables.length === 0) && 
                           (!result.items || result.items.length === 0) && 
                           (!result.prices || result.prices.length === 0) && (
                            <div className="text-gray-500 text-center py-4">
                              No structured data found on this page
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                  
                  {selectedJobData && jobResults.length === 0 && selectedJobData.status !== 'in_progress' && (
                    <div className="text-gray-500 text-center py-8">
                      No results available for this job
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {!selectedJob && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="text-center py-12">
                  <div className="text-gray-400 mb-4">
                    <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Job Selected</h3>
                  <p className="text-gray-500">Select a scraping job from the left panel to view results</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;