from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import random
import asyncio
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Qwipo B2B Marketplace", description="Intelligent Product Recommendation System")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Pydantic Models
class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str
    subcategory: str
    brand: str
    price: float
    unit: str
    image_url: Optional[str] = None
    stock_quantity: int = 0
    tags: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    description: str
    category: str
    subcategory: str
    brand: str
    price: float
    unit: str
    image_url: Optional[str] = None
    stock_quantity: int = 0
    tags: List[str] = []

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phone_number: str
    business_name: str
    business_type: str
    verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    phone_number: str
    business_name: str
    business_type: str

class OTPRequest(BaseModel):
    phone_number: str

class OTPVerify(BaseModel):
    phone_number: str
    otp: str

class CartItem(BaseModel):
    product_id: str
    quantity: int

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[CartItem]
    total_amount: float
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderCreate(BaseModel):
    items: List[CartItem]

class Recommendation(BaseModel):
    product_id: str
    product_name: str
    reason: str
    confidence_score: float
    recommendation_type: str  # "cross_sell", "upsell", "repurchase", "trending"

class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    type: str = "recommendation"

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    message: str
    type: str
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

def get_ai_chat():
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    return LlmChat(
        api_key=api_key,
        session_id="qwipo-recommendations",
        system_message="You are an intelligent B2B product recommendation expert for kirana stores and small retailers. Analyze purchase patterns and suggest relevant FMCG products to increase order value and repeat purchases."
    ).with_model("openai", "gpt-4o")
      
@api_router.post("/auth/send-otp")
async def send_otp(request: OTPRequest):
    # In production, integrate with SMS service
    # For MVP, we'll simulate OTP generation
    otp = str(random.randint(100000, 999999))
    
    # Store OTP in database (expires in 5 minutes)
    otp_data = {
        "phone_number": request.phone_number,
        "otp": otp,
        "expires_at": datetime.now(timezone.utc).timestamp() + 300,
        "created_at": datetime.now(timezone.utc)
    }
    await db.otps.insert_one(otp_data)
    
    return {"message": f"OTP sent to {request.phone_number}", "otp": otp}  # Remove OTP in production

@api_router.post("/auth/verify-otp")
async def verify_otp(request: OTPVerify):
    
    otp_record = await db.otps.find_one({
        "phone_number": request.phone_number,
        "otp": request.otp
    })
    
    if not otp_record or otp_record["expires_at"] < datetime.now(timezone.utc).timestamp():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    user = await db.users.find_one({"phone_number": request.phone_number})
    if not user:
        # New user registration flow
        return {"verified": True, "new_user": True, "phone_number": request.phone_number}
    

    user_obj = User(**user)
    return {"verified": True, "new_user": False, "user": user_obj}

@api_router.post("/auth/register", response_model=User)
async def register_user(user_data: UserCreate):
 
    existing = await db.users.find_one({"phone_number": user_data.phone_number})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    user_dict = user_data.dict()
    user_obj = User(**user_dict, verified=True)
    await db.users.insert_one(user_obj.dict())
    return user_obj

@api_router.get("/products", response_model=List[Product])
async def get_products(category: Optional[str] = None, search: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search]}}
        ]
    
    products = await db.products.find(query).to_list(100)
    return [Product(**product) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@api_router.get("/categories")
async def get_categories():
    categories = await db.products.distinct("category")
    return {"categories": categories}

@api_router.get("/recommendations/{user_id}", response_model=List[Recommendation])
async def get_recommendations(user_id: str, recommendation_type: str = "all"):
    # Get user's order history
    orders = await db.orders.find({"user_id": user_id}).to_list(50)
    
    if not orders:
        # New user - show trending products
        trending_products = await db.products.find().limit(5).to_list(5)
        return [
            Recommendation(
                product_id=p["id"],
                product_name=p["name"],
                reason="Popular among similar businesses",
                confidence_score=0.7,
                recommendation_type="trending"
            ) for p in trending_products
        ]
    
    try:
        chat = get_ai_chat()
        
        order_data = []
        for order in orders:
            for item in order["items"]:
                product = await db.products.find_one({"id": item["product_id"]})
                if product:
                    order_data.append({
                        "product_name": product["name"],
                        "category": product["category"],
                        "price": product["price"],
                        "quantity": item["quantity"]
                    })
        
        prompt = f"""
        Based on this B2B retailer's purchase history: {json.dumps(order_data)}
        
        Recommend 5 products that would:
        1. Increase their order value (cross-sell/upsell)
        2. Encourage repeat purchases
        3. Match their business patterns
        
        Return recommendations in this JSON format:
        [
            {{
                "product_name": "Product Name",
                "reason": "Why this product fits",
                "confidence_score": 0.8,
                "recommendation_type": "cross_sell"
            }}
        ]
        """
        
        user_message = UserMessage(text=prompt)
        ai_response = await chat.send_message(user_message)
        
        recommendations = []
        try:
            ai_recs = json.loads(ai_response.strip())
            for rec in ai_recs[:5]:
                # Find matching product
                product = await db.products.find_one({
                    "name": {"$regex": rec["product_name"], "$options": "i"}
                })
                if product:
                    recommendations.append(Recommendation(
                        product_id=product["id"],
                        product_name=product["name"],
                        reason=rec["reason"],
                        confidence_score=rec["confidence_score"],
                        recommendation_type=rec["recommendation_type"]
                    ))
        except:
            pass
            
    except Exception as e:
        logging.error(f"AI recommendation error: {e}")
    
    if len(recommendations) < 3:
        recent_products = []
        for order in orders[-3:]:  # Last 3 orders
            for item in order["items"]:
                recent_products.append(item["product_id"])
        
        if recent_products:
            recent_product_data = await db.products.find({"id": {"$in": recent_products}}).to_list(10)
            categories = [p["category"] for p in recent_product_data]
            
            similar_products = await db.products.find({
                "category": {"$in": categories},
                "id": {"$nin": recent_products}
            }).limit(5).to_list(5)
            
            for product in similar_products:
                if len(recommendations) < 5:
                    recommendations.append(Recommendation(
                        product_id=product["id"],
                        product_name=product["name"],
                        reason="Frequently bought together with your recent purchases",
                        confidence_score=0.6,
                        recommendation_type="cross_sell"
                    ))
    
    return recommendations

# Orders
@api_router.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate, user_id: str):
    # Calculate total amount
    total_amount = 0
    for item in order_data.items:
        product = await db.products.find_one({"id": item.product_id})
        if product:
            total_amount += product["price"] * item.quantity
    
    order_dict = order_data.dict()
    order_obj = Order(**order_dict, user_id=user_id, total_amount=total_amount)
    await db.orders.insert_one(order_obj.dict())
    
    await create_recommendation_notification(user_id)
    
    return order_obj

@api_router.get("/orders/{user_id}", response_model=List[Order])
async def get_user_orders(user_id: str):
    orders = await db.orders.find({"user_id": user_id}).to_list(50)
    return [Order(**order) for order in orders]

@api_router.get("/notifications/{user_id}", response_model=List[Notification])
async def get_notifications(user_id: str):
    notifications = await db.notifications.find({"user_id": user_id}).sort("created_at", -1).to_list(50)
    return [Notification(**notification) for notification in notifications]

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    await db.notifications.update_one(
        {"id": notification_id},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

async def create_recommendation_notification(user_id: str):
    """Create a notification about new recommendations after order"""
    notification = Notification(
        user_id=user_id,
        title="New Recommendations Available!",
        message="Based on your recent order, we found products that can boost your business. Check them out!",
        type="recommendation"
    )
    await db.notifications.insert_one(notification.dict())

# Test endpoint to get current OTP for any phone number
@api_router.get("/auth/get-otp/{phone_number}")
async def get_current_otp(phone_number: str):
    """For testing purposes - get current valid OTP for a phone number"""
    otp_record = await db.otps.find_one(
        {"phone_number": phone_number},
        sort=[("created_at", -1)]  # Get the latest OTP
    )
    
    if not otp_record:
        raise HTTPException(status_code=404, detail="No OTP found for this number")
    
    if otp_record["expires_at"] < datetime.now(timezone.utc).timestamp():
        raise HTTPException(status_code=400, detail="OTP has expired")
    
    return {"phone_number": phone_number, "otp": otp_record["otp"], "message": "Current valid OTP"}

# Seed data function
@api_router.post("/seed-data")
async def seed_sample_data():
    # Sample FMCG products
    sample_products = [
        {"name": "Tata Salt", "description": "Iodized Salt 1kg", "category": "Grocery", "subcategory": "Spices & Condiments", "brand": "Tata", "price": 22.0, "unit": "1kg", "stock_quantity": 100, "tags": ["salt", "grocery", "tata"]},
        {"name": "Maggi Noodles", "description": "Masala Noodles 70g Pack", "category": "Grocery", "subcategory": "Instant Food", "brand": "Nestle", "price": 14.0, "unit": "70g", "stock_quantity": 200, "tags": ["noodles", "instant", "maggi"]},
        {"name": "Britannia Biscuits", "description": "Good Day Butter Cookies 100g", "category": "Snacks", "subcategory": "Biscuits", "brand": "Britannia", "price": 20.0, "unit": "100g", "stock_quantity": 150, "tags": ["biscuits", "cookies", "britannia"]},
        {"name": "Amul Milk", "description": "Full Cream Milk 1L", "category": "Dairy", "subcategory": "Milk", "brand": "Amul", "price": 60.0, "unit": "1L", "stock_quantity": 80, "tags": ["milk", "dairy", "amul"]},
        {"name": "Surf Excel", "description": "Detergent Powder 1kg", "category": "Household", "subcategory": "Cleaning", "brand": "Hindustan Unilever", "price": 180.0, "unit": "1kg", "stock_quantity": 50, "tags": ["detergent", "cleaning", "surf"]},
        {"name": "Parle-G Biscuits", "description": "Glucose Biscuits 200g", "category": "Snacks", "subcategory": "Biscuits", "brand": "Parle", "price": 25.0, "unit": "200g", "stock_quantity": 120, "tags": ["biscuits", "glucose", "parle"]},
        {"name": "Colgate Toothpaste", "description": "Strong Teeth 200g", "category": "Personal Care", "subcategory": "Oral Care", "brand": "Colgate", "price": 95.0, "unit": "200g", "stock_quantity": 90, "tags": ["toothpaste", "oral care", "colgate"]},
        {"name": "Toor Dal", "description": "Arhar Dal 1kg", "category": "Grocery", "subcategory": "Pulses", "brand": "Generic", "price": 140.0, "unit": "1kg", "stock_quantity": 60, "tags": ["dal", "pulses", "arhar"]},
        {"name": "Sunflower Oil", "description": "Fortune Sunflower Oil 1L", "category": "Grocery", "subcategory": "Cooking Oil", "brand": "Fortune", "price": 120.0, "unit": "1L", "stock_quantity": 40, "tags": ["oil", "cooking", "fortune"]},
        {"name": "Basmati Rice", "description": "Premium Basmati Rice 5kg", "category": "Grocery", "subcategory": "Rice & Grains", "brand": "India Gate", "price": 450.0, "unit": "5kg", "stock_quantity": 30, "tags": ["rice", "basmati", "premium"]}
    ]
    
    for product_data in sample_products:
        product = Product(**product_data)
        existing = await db.products.find_one({"name": product.name})
        if not existing:
            await db.products.insert_one(product.dict())
    
    return {"message": "Sample data seeded successfully"}

@api_router.get("/")
async def root():
    return {"message": "Qwipo B2B Marketplace API - Intelligent Recommendation System"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
