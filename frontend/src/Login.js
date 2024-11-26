import React, { useEffect } from "react";
import axios from "axios";
import { Form, Input, Button, notification, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import CryptoJS from "crypto-js";
// import './Login.css'; // Add any additional styles if needed

const { Text } = Typography;

// Utility function for decryption
const decryptMessage = (
  encryptedMessage,
  secretKey = process.env.REACT_APP_API_SECRET_KEY
) => {
  const key = CryptoJS.enc.Utf8.parse(secretKey.padEnd(32).slice(0, 32));
  const encryptedBytes = CryptoJS.enc.Base64.parse(encryptedMessage);
  const iv = CryptoJS.lib.WordArray.create(
    encryptedBytes.words.slice(0, 4),
    16
  );
  const ciphertext = CryptoJS.lib.WordArray.create(
    encryptedBytes.words.slice(4),
    encryptedBytes.sigBytes - 16
  );
  const decrypted = CryptoJS.AES.decrypt({ ciphertext }, key, { iv });
  return JSON.parse(decrypted.toString(CryptoJS.enc.Utf8));
};

// Axios instance with interceptor
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL,
});

apiClient.interceptors.response.use(
  (response) => {
    if (response.data) {
      response.data = decryptMessage(response.data);
    }
    return response;
  },
  (error) => Promise.reject(error)
);

const Login = () => {
  const navigate = useNavigate();
  const token = localStorage.getItem("token");

  useEffect(() => {
    if (token) {
      navigate("/dashboard");
    }
  }, [token, navigate]);

  const handleLogin = async (values) => {
    try {
      const response = await apiClient.post("/api/login", {
        email: values.email,
        loginPin: values.pin,
      });
      localStorage.setItem("token", response.data.token);
      notification.success({
        message: "Login Successful",
        description: "You have successfully logged in!",
      });
      navigate("/dashboard");
    } catch (err) {
      notification.error({
        message: "Login Failed",
        description:
          err.response?.data?.message || "Unable to login. Please try again.",
      });
    }
  };

  return (
    <div className="bg-gray-100 flex items-center justify-center min-h-screen">
      <div className="bg-white rounded-lg shadow-lg p-8 w-3/4 relative">
        <div className="relative mb-6">
          <h1 className="text-3xl font-bold text-center">Smart Ai Trading</h1>
          <div className="flex items-center justify-center mb-6">
            <hr className="flex-grow border-t border-dashed border-gray-400" />
            <p className="mx-4 text-lg text-gray-600 italic">
              By: Harshil Kaneria
            </p>
            <hr className="flex-grow border-t border-dashed border-gray-400" />
          </div>
        </div>

        <div
          className="login-container"
          style={{
            width: "100%",
            maxWidth: "400px",
            margin: "0 auto"
          }}
        >
          <Form layout="vertical" onFinish={handleLogin} autoComplete="off">
            <Form.Item
              label="Email"
              name="email"
              rules={[
                { required: true, message: "Please enter your email!" },
                { type: "email", message: "Enter a valid email address!" },
              ]}
            >
              <Input placeholder="Enter your email" />
            </Form.Item>
            <Form.Item
              label="PIN"
              name="pin"
              rules={[
                { required: true, message: "Please enter your PIN!" },
                { min: 6, message: "PIN must be at least 6 characters!" },
                { max: 6, message: "PIN cannot exceed 6 characters!" },
              ]}
            >
              <Input.Password placeholder="Enter your PIN" />
            </Form.Item>
            <Button ghost type="primary" htmlType="submit" block>
              Login
            </Button>
          </Form>
        </div>

        <div className="register-note mt-6">
          <hr className="flex-grow border-t border-dashed border-gray-400" />
          <div className="flex justify-center">
            <Text type="secondary">
              Don't have an account? Register by contacting us at:
            </Text>
          </div>
          <div className="contact-details mt-2 flex justify-between">
            <Text strong>Call : <a href="tel:+917622042408">+91 7622042408</a> <a href="tel:+918160187881">+91 8160187881</a></Text>
            <Text strong>
              WhatsApp :{" "}
              <a
                href="https://wa.me/917622042408"
                target="_blank"
                rel="noopener noreferrer"
              >
                (+91 7622042408)
              </a>
            </Text>
            <Text strong>
              Email :{" "}
              <a
                href="mailto:harshilkaneria00@gmail.com"
                target="_blank"
                rel="noopener noreferrer"
              >
                harshilkaneria00@gmail.com
              </a>
            </Text>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
