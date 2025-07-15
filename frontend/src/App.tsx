import React, { useState } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import { TrainingPlanForm } from './components/TrainingPlanForm';
import { PlanStatusChecker } from './components/PlanStatusChecker';

const App: React.FC = () => {
  const [athleteName, setAthleteName] = useState<string>('');

  const handlePlanSubmitted = (name: string) => {
    setAthleteName(name);
  };

  return (
    <div className="App">
      <Container className="py-4">
        <Row className="mb-4">
          <Col>
            <Card className="text-center">
              <Card.Header as="h1">Strava Training Planner</Card.Header>
              <Card.Body>
                <Card.Text className="lead">
                  Generate personalized training plans based on your Strava activity data and expert workout recommendations
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        <Row>
          <Col md={6}>
            <Card className="mb-4">
              <Card.Header as="h5">Create Training Plan</Card.Header>
              <Card.Body>
                <TrainingPlanForm onPlanSubmitted={handlePlanSubmitted} />
              </Card.Body>
            </Card>
          </Col>

          <Col md={6}>
            <Card>
              <Card.Header as="h5">Check Plan Status</Card.Header>
              <Card.Body>
                <PlanStatusChecker athleteName={athleteName} />
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
}

export default App;
