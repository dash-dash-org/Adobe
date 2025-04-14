import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import './App.css';
import DatabaseForm from './components/DatabaseForm';
import ChatInterface from './components/ChatInterface';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const handleLogin = () => {
    navigate('/connect');
  };

  const handleSignup = () => {
    navigate('/connect');
  };

  return (
    <div className="App">
      <nav className="navbar">
        <div className="navbar-brand">NL2SQL Agent</div>
        <div className="navbar-links">
          <button onClick={handleLogin}>Login</button>
          <button onClick={handleSignup}>Sign Up</button>
        </div>
      </nav>
      
      <main className="landing-section">
        <h1>Natural Language to SQL Query Creator</h1>
        <p>Transform your database queries using natural language with our intelligent multi-agent system</p>
        <div className="cta-buttons">
          <button className="primary-btn" onClick={handleLogin}>Get Started</button>
          <button className="secondary-btn" onClick={handleSignup}>Create Account</button>
        </div>
      </main>
    </div>
  );
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/connect" element={<DatabaseForm />} />
        <Route path="/chat" element={<ChatInterface />} />
      </Routes>
    </Router>
  );
}

export default App;
