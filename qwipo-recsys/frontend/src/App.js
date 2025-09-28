import React, { useState, useEffect, createContext } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";

// Components
import LoginPage from "./components/LoginPage";
import Dashboard from "./components/Dashboard";
import ProductCatalog from "./components/ProductCatalog";
import Recommendations from "./components/Recommendations";
import PurchaseHistory from "./components/PurchaseHistory";
import Notifications from "./components/Notifications";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth context
const AuthContext = createContext();

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  // Set default axios header for auth
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common["Authorization"];
    }
  }, [token]);

  // Check if user is logged in on app load
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          // Try to get user data to verify token
          const response = await axios.get(`${API}/products`);
          // If successful, token is valid
          setLoading(false);
        } catch (error) {
          // Token is invalid
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          setToken(null);
          setUser(null);
          setLoading(false);
        }
      } else {
        setLoading(false);
      }
    };

    checkAuth();
  }, [token]);

  const login = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
    localStorage.setItem("token", authToken);
    localStorage.setItem("user", JSON.stringify(userData));
    toast.success(`Welcome back, ${userData.business_name}!`);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    delete axios.defaults.headers.common["Authorization"];
    toast.info("Logged out successfully");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      <div className="App">
        <BrowserRouter>
          <Routes>
            {!token ? (
              <Route path="/*" element={<LoginPage />} />
            ) : (
              <>
                <Route path="/" element={<Dashboard />} />
                <Route path="/products" element={<ProductCatalog />} />
                <Route path="/recommendations" element={<Recommendations />} />
                <Route path="/history" element={<PurchaseHistory />} />
                <Route path="/notifications" element={<Notifications />} />
                <Route path="/*" element={<Navigate to="/" replace />} />
              </>
            )}
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </div>
    </AuthContext.Provider>
  );
}

export default App;
export { AuthContext, API };
