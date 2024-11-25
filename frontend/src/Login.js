import React, { useState } from 'react';
import axios from 'axios';
import { notification } from 'antd';
import { useNavigate } from 'react-router-dom';
import CryptoJS from 'crypto-js';

const decryptMessage = (encryptedMessage, secretKey=process.env.REACT_APP_API_SECRET_KEY) => {
    // Ensure the key matches the length (256 bits / 32 bytes)
    const key = CryptoJS.enc.Utf8.parse(secretKey.padEnd(32).slice(0, 32));
  
    // Decode Base64
    const encryptedBytes = CryptoJS.enc.Base64.parse(encryptedMessage);
  
    // Extract IV (first 16 bytes)
    const iv = CryptoJS.lib.WordArray.create(encryptedBytes.words.slice(0, 4), 16);
  
    // Extract ciphertext
    const ciphertext = CryptoJS.lib.WordArray.create(encryptedBytes.words.slice(4), encryptedBytes.sigBytes - 16);
  
    // Decrypt the data
    const decrypted = CryptoJS.AES.decrypt({ ciphertext }, key, { iv });
    return JSON.parse(decrypted.toString(CryptoJS.enc.Utf8))
  };
  
  const apiClient = axios.create({
    baseURL: process.env.REACT_APP_API_BASE_URL,
  });
  
  // Add a response interceptor
  apiClient.interceptors.response.use(
    (response) => {
      // Decrypt the response data
      if (response.data) {
        response.data = decryptMessage(response.data);
      }
      return response;
    },
    (error) => {
      // Handle any error
      return Promise.reject(error);
    }
  );

const Login = () => {
  const [email, setEmail] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');

  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await apiClient.post('/api/login', { email, loginPin: pin });
      localStorage.setItem('token', response.data.token);
      notification.success({
        message: 'Login Successful',
        description: 'You have successfully logged in!',
      });
      navigate('/dashboard'); // Redirect to dashboard
    } catch (err) {
        notification.error({
            message: 'Login Failed',
            description: err.response?.data?.message || 'Unable to login. Please try again.',
          });
    }
  };

  return (
    <div className="login-container">
      <h2>Login</h2>
      <form onSubmit={handleLogin}>
        <div>
          <label>Email:</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label>PIN:</label>
          <input
            type="password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            required
          />
        </div>
        {error && <p className="error">{error}</p>}
        <button type="submit">Login</button>
      </form>
    </div>
  );
};

export default Login;