import React, { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import { ShoppingCart, Bell, User, Search, TrendingUp, Package, Star, Phone } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Authentication Context
const AuthContext = React.createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const login = (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const logout = () => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('user');
  };

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      const userData = JSON.parse(savedUser);
      setUser(userData);
      setIsAuthenticated(true);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

// Authentication Component
const AuthPage = () => {
  const [step, setStep] = useState('phone'); // 'phone', 'otp', 'register'
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otp, setOtp] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [businessType, setBusinessType] = useState('kirana');
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const { login } = useAuth();

  const sendOTP = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/send-otp`, {
        phone_number: phoneNumber
      });
      // For MVP testing - show the OTP in the success message
      const generatedOTP = response.data.otp;
      toast({ 
        title: "Success", 
        description: `OTP sent to ${phoneNumber}. For testing: ${generatedOTP}`,
        duration: 10000  // Show for 10 seconds
      });
      setOtp(generatedOTP); // Auto-fill OTP for better UX
      setStep('otp');
    } catch (error) {
      toast({ title: "Error", description: "Failed to send OTP", variant: "destructive" });
    }
    setLoading(false);
  };

  const verifyOTP = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/verify-otp`, {
        phone_number: phoneNumber,
        otp: otp
      });
      
      if (response.data.new_user) {
        setStep('register');
      } else {
        login(response.data.user);
      }
    } catch (error) {
      toast({ title: "Error", description: "Invalid OTP", variant: "destructive" });
    }
    setLoading(false);
  };

  const registerUser = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/register`, {
        phone_number: phoneNumber,
        business_name: businessName,
        business_type: businessType
      });
      login(response.data);
      toast({ title: "Success", description: "Registration successful!" });
    } catch (error) {
      toast({ title: "Error", description: "Registration failed", variant: "destructive" });
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-indigo-800">Qwipo B2B</CardTitle>
          <CardDescription>Smart Marketplace for Retailers</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {step === 'phone' && (
            <>
              <div className="space-y-2">
                <label className="text-sm font-medium">Phone Number</label>
                <Input
                  type="tel"
                  placeholder="+91 9876543210"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  data-testid="phone-input"
                />
              </div>
              <Button 
                onClick={sendOTP} 
                disabled={loading || !phoneNumber}
                className="w-full"
                data-testid="send-otp-btn"
              >
                <Phone className="w-4 h-4 mr-2" />
                {loading ? 'Sending...' : 'Send OTP'}
              </Button>
            </>
          )}

          {step === 'otp' && (
            <>
              <div className="space-y-2">
                <label className="text-sm font-medium">Enter OTP</label>
                <Input
                  type="text"
                  placeholder="123456"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  data-testid="otp-input"
                />
                <p className="text-xs text-blue-600 mt-1">
                  💡 For testing: OTP is auto-filled and shown in the success message above
                </p>
              </div>
              <Button 
                onClick={verifyOTP} 
                disabled={loading || !otp}
                className="w-full"
                data-testid="verify-otp-btn"
              >
                {loading ? 'Verifying...' : 'Verify OTP'}
              </Button>
              <Button 
                variant="outline" 
                onClick={() => setStep('phone')}
                className="w-full"
              >
                Back
              </Button>
            </>
          )}

          {step === 'register' && (
            <>
              <div className="space-y-2">
                <label className="text-sm font-medium">Business Name</label>
                <Input
                  type="text"
                  placeholder="My Store"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  data-testid="business-name-input"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Business Type</label>
                <select 
                  className="w-full p-2 border rounded"
                  value={businessType}
                  onChange={(e) => setBusinessType(e.target.value)}
                  data-testid="business-type-select"
                >
                  <option value="kirana">Kirana Store</option>
                  <option value="restaurant">Restaurant</option>
                  <option value="retail">General Retail</option>
                  <option value="wholesale">Wholesale</option>
                </select>
              </div>
              <Button 
                onClick={registerUser} 
                disabled={loading || !businessName}
                className="w-full"
                data-testid="register-btn"
              >
                {loading ? 'Registering...' : 'Complete Registration'}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// Product Components
const ProductCard = ({ product, onAddToCart }) => {
  return (
    <Card className="hover:shadow-lg transition-all duration-300">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <CardTitle className="text-lg">{product.name}</CardTitle>
          <Badge variant="secondary">{product.category}</Badge>
        </div>
        <CardDescription className="text-sm">{product.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex justify-between items-center mb-2">
          <span className="text-2xl font-bold text-green-600">₹{product.price}</span>
          <span className="text-sm text-gray-500">{product.unit}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm">Stock: {product.stock_quantity}</span>
          <Button 
            size="sm" 
            onClick={() => onAddToCart(product)}
            data-testid={`add-to-cart-${product.id}`}
          >
            <ShoppingCart className="w-4 h-4 mr-1" />
            Add
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const RecommendationCard = ({ recommendation, onAddToCart }) => {
  const [product, setProduct] = useState(null);

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        const response = await axios.get(`${API}/products/${recommendation.product_id}`);
        setProduct(response.data);
      } catch (error) {
        console.error('Failed to fetch product:', error);
      }
    };
    fetchProduct();
  }, [recommendation.product_id]);

  if (!product) return null;

  return (
    <Card className="border-l-4 border-l-blue-500 hover:shadow-lg transition-all duration-300">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <CardTitle className="text-lg">{product.name}</CardTitle>
          <Badge variant="default">{recommendation.recommendation_type}</Badge>
        </div>
        <CardDescription className="text-sm text-blue-600">
          <Star className="w-3 h-3 inline mr-1" />
          {recommendation.reason}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex justify-between items-center mb-2">
          <span className="text-xl font-bold text-green-600">₹{product.price}</span>
          <span className="text-sm bg-blue-100 px-2 py-1 rounded">
            {Math.round(recommendation.confidence_score * 100)}% match
          </span>
        </div>
        <Button 
          size="sm" 
          onClick={() => onAddToCart(product)}
          className="w-full"
          data-testid={`add-rec-${product.id}`}
        >
          <ShoppingCart className="w-4 h-4 mr-1" />
          Add to Cart
        </Button>
      </CardContent>
    </Card>
  );
};

// Main Dashboard Component
const Dashboard = () => {
  const [products, setProducts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [cart, setCart] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [categories, setCategories] = useState([]);
  const { user, logout } = useAuth();
  const { toast } = useToast();

  useEffect(() => {
    fetchProducts();
    fetchCategories();
    fetchRecommendations();
    fetchNotifications();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API}/products`, {
        params: { category: selectedCategory, search: searchTerm }
      });
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to fetch products:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data.categories);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    }
  };

  const fetchRecommendations = async () => {
    try {
      const response = await axios.get(`${API}/recommendations/${user.id}`);
      setRecommendations(response.data);
    } catch (error) {
      console.error('Failed to fetch recommendations:', error);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await axios.get(`${API}/notifications/${user.id}`);
      setNotifications(response.data);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  };

  const addToCart = (product) => {
    const existingItem = cart.find(item => item.product_id === product.id);
    if (existingItem) {
      setCart(cart.map(item => 
        item.product_id === product.id 
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      setCart([...cart, { product_id: product.id, quantity: 1, product }]);
    }
    toast({ title: "Added to Cart", description: `${product.name} added to cart` });
  };

  const placeOrder = async () => {
    try {
      const orderItems = cart.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity
      }));
      
      await axios.post(`${API}/orders?user_id=${user.id}`, {
        items: orderItems
      });
      
      setCart([]);
      toast({ title: "Success", description: "Order placed successfully!" });
      fetchRecommendations(); // Refresh recommendations after order
      fetchNotifications(); // Refresh notifications
    } catch (error) {
      toast({ title: "Error", description: "Failed to place order", variant: "destructive" });
    }
  };

  const totalCartValue = cart.reduce((sum, item) => sum + (item.product?.price || 0) * item.quantity, 0);

  useEffect(() => {
    fetchProducts();
  }, [selectedCategory, searchTerm]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-indigo-800">Qwipo</h1>
              <Badge variant="outline" className="ml-2">{user.business_type}</Badge>
            </div>
            <div className="flex items-center space-x-4">
              <div className="relative">
                <Bell className="w-6 h-6 text-gray-600" />
                {notifications.filter(n => !n.read).length > 0 && (
                  <span className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center">
                    {notifications.filter(n => !n.read).length}
                  </span>
                )}
              </div>
              <div className="relative">
                <ShoppingCart className="w-6 h-6 text-gray-600" />
                {cart.length > 0 && (
                  <span className="absolute -top-2 -right-2 bg-blue-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center">
                    {cart.length}
                  </span>
                )}
              </div>
              <Button variant="ghost" size="sm" onClick={logout} data-testid="logout-btn">
                <User className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs defaultValue="products" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="products" data-testid="products-tab">Products</TabsTrigger>
            <TabsTrigger value="recommendations" data-testid="recommendations-tab">
              <TrendingUp className="w-4 h-4 mr-1" />
              Smart Picks
            </TabsTrigger>
            <TabsTrigger value="cart" data-testid="cart-tab">
              Cart ({cart.length})
            </TabsTrigger>
            <TabsTrigger value="notifications" data-testid="notifications-tab">
              Alerts ({notifications.filter(n => !n.read).length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="products" className="space-y-6">
            {/* Search and Filter */}
            <div className="flex gap-4 items-center">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search products..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                  data-testid="search-input"
                />
              </div>
              <select 
                className="border rounded px-3 py-2"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                data-testid="category-filter"
              >
                <option value="">All Categories</option>
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            {/* Products Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="products-grid">
              {products.map(product => (
                <ProductCard key={product.id} product={product} onAddToCart={addToCart} />
              ))}
            </div>
          </TabsContent>

          <TabsContent value="recommendations" className="space-y-6">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Smart Recommendations</h2>
              <p className="text-gray-600">AI-powered suggestions to boost your business</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="recommendations-grid">
              {recommendations.map((rec, index) => (
                <RecommendationCard key={index} recommendation={rec} onAddToCart={addToCart} />
              ))}
            </div>
            
            {recommendations.length === 0 && (
              <div className="text-center py-12">
                <Package className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No recommendations yet. Place some orders to get personalized suggestions!</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="cart" className="space-y-6">
            {cart.length === 0 ? (
              <div className="text-center py-12">
                <ShoppingCart className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">Your cart is empty</p>
              </div>
            ) : (
              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Shopping Cart</CardTitle>
                    <CardDescription>Review your items before checkout</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {cart.map(item => (
                        <div key={item.product_id} className="flex justify-between items-center py-2 border-b">
                          <div>
                            <h4 className="font-medium">{item.product?.name}</h4>
                            <p className="text-sm text-gray-500">₹{item.product?.price} x {item.quantity}</p>
                          </div>
                          <span className="font-bold">₹{(item.product?.price || 0) * item.quantity}</span>
                        </div>
                      ))}
                      <div className="flex justify-between items-center pt-4 text-lg font-bold">
                        <span>Total:</span>
                        <span className="text-green-600">₹{totalCartValue}</span>
                      </div>
                      <Button 
                        className="w-full mt-4" 
                        onClick={placeOrder}
                        data-testid="place-order-btn"
                      >
                        Place Order - ₹{totalCartValue}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          <TabsContent value="notifications" className="space-y-4">
            {notifications.length === 0 ? (
              <div className="text-center py-12">
                <Bell className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No notifications yet</p>
              </div>
            ) : (
              <div className="space-y-4" data-testid="notifications-list">
                {notifications.map(notification => (
                  <Card key={notification.id} className={notification.read ? 'opacity-60' : ''}>
                    <CardHeader className="pb-2">
                      <div className="flex justify-between items-start">
                        <CardTitle className="text-lg">{notification.title}</CardTitle>
                        <Badge variant={notification.read ? "secondary" : "default"}>
                          {notification.read ? "Read" : "New"}
                        </Badge>
                      </div>
                      <CardDescription>{notification.message}</CardDescription>
                    </CardHeader>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

// Main App Component
const App = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={
            isAuthenticated ? <Navigate to="/dashboard" /> : <AuthPage />
          } />
          <Route path="/dashboard" element={
            isAuthenticated ? <Dashboard /> : <Navigate to="/" />
          } />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </div>
  );
};

const AppWithAuth = () => (
  <AuthProvider>
    <App />
  </AuthProvider>
);

export default AppWithAuth;
