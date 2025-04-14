import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './DatabaseForm.css';

interface DatabaseCredentials {
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
}

const DatabaseForm: React.FC = () => {
  const navigate = useNavigate();
  const [credentials, setCredentials] = useState<DatabaseCredentials>({
    host: '',
    port: '',
    database: '',
    username: '',
    password: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Add validation and API call to verify credentials
    console.log('Database credentials:', credentials);
    // Navigate to chat interface after successful connection
    navigate('/chat');
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setCredentials(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="database-form-container">
      <h2>Connect to Your Database</h2>
      <form onSubmit={handleSubmit} className="database-form">
        <div className="form-group">
          <label htmlFor="host">Host</label>
          <input
            type="text"
            id="host"
            name="host"
            value={credentials.host}
            onChange={handleChange}
            placeholder="localhost"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="port">Port</label>
          <input
            type="text"
            id="port"
            name="port"
            value={credentials.port}
            onChange={handleChange}
            placeholder="5432"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="database">Database Name</label>
          <input
            type="text"
            id="database"
            name="database"
            value={credentials.database}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="username">Username</label>
          <input
            type="text"
            id="username"
            name="username"
            value={credentials.username}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            value={credentials.password}
            onChange={handleChange}
            required
          />
        </div>
        <button type="submit" className="submit-btn">Connect</button>
      </form>
    </div>
  );
};

export default DatabaseForm;