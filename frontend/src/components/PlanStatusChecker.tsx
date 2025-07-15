import React, { useState, useEffect } from 'react';
import { Alert, Button, Spinner } from 'react-bootstrap';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface PlanStatusCheckerProps {
  athleteName: string;
}

interface PlanStatus {
  status: 'processing' | 'completed' | 'failed' | 'not_found';
  message: string;
  excel_file_path?: string;
}

export const PlanStatusChecker: React.FC<PlanStatusCheckerProps> = ({ athleteName }) => {
  const [status, setStatus] = useState<PlanStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // Function to check the status of a plan
  const checkPlanStatus = async () => {
    if (!athleteName.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(`${API_URL}/training-plan/${encodeURIComponent(athleteName)}/status`);
      setStatus(response.data);

      // If the plan is completed or failed, stop polling
      if (response.data.status === 'completed' || response.data.status === 'failed') {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
      }
    } catch (err) {
      console.error('Error checking plan status:', err);
      setError('Failed to check plan status. Please try again.');
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
    } finally {
      setLoading(false);
    }
  };

  // Start polling when athlete name changes
  useEffect(() => {
    if (!athleteName.trim()) {
      setStatus(null);
      return;
    }

    // Check immediately
    checkPlanStatus();

    // Set up polling every 5 seconds
    const interval = setInterval(checkPlanStatus, 5000);
    setPollingInterval(interval);

    // Clean up on unmount or when athlete name changes
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [athleteName]);

  // Handle download button click
  const handleDownload = () => {
    if (!athleteName.trim()) return;

    // Open the download link in a new tab
    window.open(`${API_URL}/training-plan/${encodeURIComponent(athleteName)}/download`, '_blank');
  };

  // Render different content based on status
  const renderStatusContent = () => {
    if (!athleteName.trim()) {
      return <Alert variant="info">Enter an athlete name and generate a plan to see status here.</Alert>;
    }

    if (loading && !status) {
      return (
        <div className="text-center">
          <Spinner animation="border" role="status" className="mb-3" />
          <p>Checking status for {athleteName}...</p>
        </div>
      );
    }

    if (error) {
      return <Alert variant="danger">{error}</Alert>;
    }

    if (!status) {
      return null;
    }

    switch (status.status) {
      case 'processing':
        return (
          <Alert variant="info">
            <Spinner animation="border" size="sm" className="me-2" />
            {status.message || `Training plan for ${athleteName} is being generated...`}
          </Alert>
        );
      case 'completed':
        return (
          <>
            <Alert variant="success">
              Training plan for {athleteName} is ready!
            </Alert>
            <Button variant="success" onClick={handleDownload} className="mb-4">
              Download Excel Training Plan
            </Button>
            <div className="mt-3">
              <h6>Agent's Message:</h6>
              <div className="border rounded p-3 bg-light markdown-content">
                <ReactMarkdown>{status.message || "No additional message"}</ReactMarkdown>
              </div>
            </div>
          </>
        );
      case 'failed':
        return (
          <Alert variant="danger">
            {status.message || `Failed to generate training plan for ${athleteName}.`}
          </Alert>
        );
      case 'not_found':
        return (
          <Alert variant="warning">
            No training plan found for {athleteName}. Please generate a plan first.
          </Alert>
        );
      default:
        return <Alert variant="secondary">Unknown status.</Alert>;
    }
  };

  return (
    <div className="plan-status-checker">
      {renderStatusContent()}

      {athleteName && (
        <div className="text-end mt-3">
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={checkPlanStatus}
            disabled={loading}
          >
            {loading ? 'Checking...' : 'Refresh Status'}
          </Button>
        </div>
      )}
    </div>
  );
};
