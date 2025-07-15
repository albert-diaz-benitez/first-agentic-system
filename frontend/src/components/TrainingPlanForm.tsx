import React, { useState } from 'react';
import { Form, Button, Alert, Spinner } from 'react-bootstrap';
import axios from 'axios';

// Define the API base URL - we'll use environment variables for deployment
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface TrainingPlanFormProps {
  onPlanSubmitted: (athleteName: string) => void;
}

export const TrainingPlanForm: React.FC<TrainingPlanFormProps> = ({ onPlanSubmitted }) => {
  const [athleteName, setAthleteName] = useState('');
  const [goals, setGoals] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      // Make API call to generate training plan
      await axios.post(`${API_URL}/training-plan`, {
        athlete_name: athleteName,
        goals: goals || undefined // Only send if not empty
      });

      // Set success message
      setSuccess('Training plan generation started!');

      // Pass the athlete name up to the parent component
      onPlanSubmitted(athleteName);

    } catch (err) {
      console.error('Error submitting training plan request:', err);
      setError('Failed to start training plan generation. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="training-plan-form">
      {error && <Alert variant="danger">{error}</Alert>}
      {success && <Alert variant="success">{success}</Alert>}

      <Form onSubmit={handleSubmit}>
        <Form.Group className="mb-3">
          <Form.Label>Athlete Name</Form.Label>
          <Form.Control
            type="text"
            placeholder="Enter your name"
            value={athleteName}
            onChange={(e) => setAthleteName(e.target.value)}
            required
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Training Goals (Optional)</Form.Label>
          <Form.Control
            as="textarea"
            rows={3}
            placeholder="E.g., Improve 10k time, build endurance, prepare for half marathon, etc."
            value={goals}
            onChange={(e) => setGoals(e.target.value)}
          />
        </Form.Group>

        <Button
          variant="primary"
          type="submit"
          disabled={isSubmitting || !athleteName.trim()}
        >
          {isSubmitting ? (
            <>
              <Spinner
                as="span"
                animation="border"
                size="sm"
                role="status"
                aria-hidden="true"
                className="me-2"
              />
              Generating...
            </>
          ) : (
            'Generate Training Plan'
          )}
        </Button>
      </Form>
    </div>
  );
};
