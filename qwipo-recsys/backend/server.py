from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import asyncio
from collections import defaultdict, Counter
import random
import hashlib

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Security
import hashlib
security = HTTPBearer()
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Qwipo B2B Recommendation System")
api_router = APIRouter(prefix="/api")

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    business_name: str
    business_type: str  # kirana, restaurant, small_business
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    business_name: str
    business_type: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    subcategory: str
    business_types: List[str]  # which business types this product is relevant for
    price: float
    unit: str
    description: str
    tags: List[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class Purchase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    product_id: str
    quantity: int
    total_amount: float
    purchase_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Recommendation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    product_id: str
    recommendation_type: str  # trending, collaborative, content_based, hybrid
    score: float
    reasons: List[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    message: str
    notification_type: str  # recommendation, trending, restock
    data: Dict[str, Any] = {}
    is_read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Helper functions
def verify_password(plain_password, hashed_password):
    try:
        # Use simple SHA256 for demo purposes
        hash_obj = hashlib.sha256(plain_password.encode())
        return hash_obj.hexdigest() == hashed_password
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False

def get_password_hash(password):
    try:
        # Use simple SHA256 for demo purposes
        hash_obj = hashlib.sha256(password.encode())
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"Password hashing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Password hashing failed")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"email": email})
    if user is None:
        raise credentials_exception
    return User(**user)

# Initialize sample data
async def init_sample_data():
    # Check if data already exists
    existing_products = await db.products.count_documents({})
    if existing_products > 0:
        return
    
    # Sample products for different business types
    sample_products = [
        # Kirana store products
        {"name": "Basmati Rice 5kg", "category": "Groceries", "subcategory": "Grains", "business_types": ["kirana", "restaurant"], "price": 450.0, "unit": "kg", "description": "Premium basmati rice", "tags": ["rice", "premium", "bulk"]},
        {"name": "Cooking Oil 1L", "category": "Groceries", "subcategory": "Oil", "business_types": ["kirana", "restaurant"], "price": 120.0, "unit": "liter", "description": "Refined cooking oil", "tags": ["oil", "cooking", "essential"]},
        {"name": "Sugar 1kg", "category": "Groceries", "subcategory": "Sweeteners", "business_types": ["kirana", "restaurant"], "price": 45.0, "unit": "kg", "description": "White sugar", "tags": ["sugar", "sweet", "basic"]},
        {"name": "Tea Leaves 250g", "category": "Beverages", "subcategory": "Tea", "business_types": ["kirana", "restaurant"], "price": 180.0, "unit": "gm", "description": "Assam tea leaves", "tags": ["tea", "beverage", "popular"]},
        {"name": "Biscuits Pack", "category": "Snacks", "subcategory": "Packaged", "business_types": ["kirana"], "price": 25.0, "unit": "pack", "description": "Glucose biscuits", "tags": ["biscuit", "snack", "kids"]},
        
        # Restaurant supplies
        {"name": "Onions 10kg", "category": "Vegetables", "subcategory": "Bulb", "business_types": ["restaurant"], "price": 300.0, "unit": "kg", "description": "Fresh onions bulk", "tags": ["onion", "vegetable", "bulk", "fresh"]},
        {"name": "Tomatoes 5kg", "category": "Vegetables", "subcategory": "Fruit vegetable", "business_types": ["restaurant"], "price": 150.0, "unit": "kg", "description": "Fresh tomatoes", "tags": ["tomato", "vegetable", "fresh"]},
        {"name": "Disposable Cups 100pc", "category": "Packaging", "subcategory": "Disposables", "business_types": ["restaurant"], "price": 80.0, "unit": "pack", "description": "Paper cups for beverages", "tags": ["cups", "disposable", "packaging"]},
        {"name": "Aluminum Foil Roll", "category": "Packaging", "subcategory": "Wrapping", "business_types": ["restaurant"], "price": 120.0, "unit": "roll", "description": "Food grade aluminum foil", "tags": ["foil", "packaging", "food-safe"]},
        
        # Small business essentials
        {"name": "A4 Paper 500 Sheets", "category": "Stationery", "subcategory": "Paper", "business_types": ["small_business"], "price": 350.0, "unit": "ream", "description": "White A4 printing paper", "tags": ["paper", "office", "printing"]},
        {"name": "Ball Pens 10pc", "category": "Stationery", "subcategory": "Writing", "business_types": ["small_business"], "price": 50.0, "unit": "pack", "description": "Blue ink ball pens", "tags": ["pen", "writing", "office"]},
        {"name": "Cleaning Detergent 1L", "category": "Cleaning", "subcategory": "Liquids", "business_types": ["small_business", "restaurant"], "price": 80.0, "unit": "liter", "description": "Multi-purpose cleaner", "tags": ["cleaner", "detergent", "hygiene"]},
        {"name": "Tissue Papers 200pc", "category": "Hygiene", "subcategory": "Paper products", "business_types": ["restaurant", "small_business"], "price": 45.0, "unit": "pack", "description": "Soft tissue papers", "tags": ["tissue", "hygiene", "soft"]},
        
        # Common items
        {"name": "Hand Sanitizer 500ml", "category": "Hygiene", "subcategory": "Sanitizers", "business_types": ["kirana", "restaurant", "small_business"], "price": 120.0, "unit": "bottle", "description": "70% alcohol sanitizer", "tags": ["sanitizer", "hygiene", "covid-safe"]},
        {"name": "Plastic Bags 100pc", "category": "Packaging", "subcategory": "Bags", "business_types": ["kirana", "restaurant"], "price": 60.0, "unit": "pack", "description": "Eco-friendly plastic bags", "tags": ["bags", "packaging", "carry"]}
    ]
    
    # Add product objects
    product_docs = []
    for product_data in sample_products:
        product = Product(**product_data)
        product_docs.append(product.dict())
    
    await db.products.insert_many(product_docs)
    logger.info(f"Inserted {len(product_docs)} sample products")

# Routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    try:
        # Check if user exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            business_name=user_data.business_name,
            business_type=user_data.business_type
        )
        
        user_dict = user.dict()
        user_dict["password_hash"] = hashed_password
        
        await db.users.insert_one(user_dict)
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer", user=user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    user = await db.users.find_one({"email": user_credentials.email})
    if not user or not verify_password(user_credentials.password, user.get("password_hash")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    user_obj = User(**user)
    return Token(access_token=access_token, token_type="bearer", user=user_obj)

@api_router.get("/products", response_model=List[Product])
async def get_products(current_user: User = Depends(get_current_user)):
    # Filter products relevant to user's business type
    products = await db.products.find({
        "business_types": current_user.business_type,
        "is_active": True
    }).to_list(length=None)
    return [Product(**product) for product in products]

@api_router.post("/purchases", response_model=Purchase)
async def record_purchase(product_id: str, quantity: int, current_user: User = Depends(get_current_user)):
    # Get product details
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    total_amount = product["price"] * quantity
    
    purchase = Purchase(
        user_id=current_user.id,
        product_id=product_id,
        quantity=quantity,
        total_amount=total_amount
    )
    
    await db.purchases.insert_one(purchase.dict())
    
    # Trigger recommendation generation (async)
    asyncio.create_task(generate_recommendations_for_user(current_user.id))
    
    return purchase

@api_router.get("/purchases", response_model=List[Purchase])
async def get_user_purchases(current_user: User = Depends(get_current_user)):
    purchases = await db.purchases.find({"user_id": current_user.id}).to_list(length=None)
    return [Purchase(**purchase) for purchase in purchases]

@api_router.get("/recommendations", response_model=List[Dict[str, Any]])
async def get_recommendations(current_user: User = Depends(get_current_user)):
    recommendations = await db.recommendations.find({
        "user_id": current_user.id
    }).sort("score", -1).limit(10).to_list(length=None)
    
    # Enrich with product details
    enriched_recommendations = []
    for rec in recommendations:
        product = await db.products.find_one({"id": rec["product_id"]})
        if product:
            enriched_rec = {
                "recommendation": Recommendation(**rec),
                "product": Product(**product)
            }
            enriched_recommendations.append(enriched_rec)
    
    return enriched_recommendations

@api_router.get("/trending", response_model=List[Dict[str, Any]])
async def get_trending_products(current_user: User = Depends(get_current_user)):
    # Get trending products based on recent purchases
    pipeline = [
        {"$match": {"purchase_date": {"$gte": datetime.now(timezone.utc) - timedelta(days=7)}}},
        {"$group": {"_id": "$product_id", "total_purchases": {"$sum": "$quantity"}}},
        {"$sort": {"total_purchases": -1}},
        {"$limit": 5}
    ]
    
    trending_data = await db.purchases.aggregate(pipeline).to_list(length=None)
    
    trending_products = []
    for item in trending_data:
        product = await db.products.find_one({"id": item["_id"]})
        if product and current_user.business_type in product["business_types"]:
            trending_products.append({
                "product": Product(**product),
                "popularity_score": item["total_purchases"]
            })
    
    return trending_products

@api_router.get("/notifications", response_model=List[Notification])
async def get_notifications(current_user: User = Depends(get_current_user)):
    notifications = await db.notifications.find({
        "user_id": current_user.id
    }).sort("created_at", -1).limit(20).to_list(length=None)
    return [Notification(**notification) for notification in notifications]

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user)):
    await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"is_read": True}}
    )
    return {"message": "Notification marked as read"}

# Recommendation algorithms
async def generate_recommendations_for_user(user_id: str):
    """Generate hybrid recommendations for a user"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        return
    
    user_obj = User(**user)
    
    # Get user's purchase history
    purchases = await db.purchases.find({"user_id": user_id}).to_list(length=None)
    
    # Collaborative filtering recommendations
    collab_recs = await get_collaborative_recommendations(user_obj, purchases)
    
    # Content-based recommendations
    content_recs = await get_content_based_recommendations(user_obj, purchases)
    
    # Combine and score recommendations
    all_recommendations = collab_recs + content_recs
    
    # Remove duplicates and sort by score
    unique_recommendations = {}
    for rec in all_recommendations:
        if rec.product_id not in unique_recommendations or rec.score > unique_recommendations[rec.product_id].score:
            unique_recommendations[rec.product_id] = rec
    
    final_recommendations = list(unique_recommendations.values())
    final_recommendations.sort(key=lambda x: x.score, reverse=True)
    
    # Store top 10 recommendations
    if final_recommendations:
        # Clear old recommendations
        await db.recommendations.delete_many({"user_id": user_id})
        
        # Insert new recommendations
        rec_docs = [rec.dict() for rec in final_recommendations[:10]]
        await db.recommendations.insert_many(rec_docs)
        
        # Create notification for top recommendation
        if final_recommendations:
            top_rec = final_recommendations[0]
            product = await db.products.find_one({"id": top_rec.product_id})
            if product:
                notification = Notification(
                    user_id=user_id,
                    title="New Product Recommendation!",
                    message=f"Based on your recent purchases, we recommend {product['name']}",
                    notification_type="recommendation",
                    data={"product_id": product["id"], "recommendation_id": top_rec.id}
                )
                await db.notifications.insert_one(notification.dict())

async def get_collaborative_recommendations(user: User, purchases: List[dict]) -> List[Recommendation]:
    """Get recommendations based on similar users' purchases"""
    if not purchases:
        return []
    
    # Find users with similar purchase patterns
    user_products = {p["product_id"] for p in purchases}
    
    # Get all users' purchases
    all_purchases = await db.purchases.find({"user_id": {"$ne": user.id}}).to_list(length=None)
    
    # Group by user and find similarity
    user_similarities = defaultdict(int)
    user_purchases_map = defaultdict(set)
    
    for purchase in all_purchases:
        user_purchases_map[purchase["user_id"]].add(purchase["product_id"])
    
    for other_user_id, other_products in user_purchases_map.items():
        similarity = len(user_products.intersection(other_products)) / len(user_products.union(other_products))
        if similarity > 0.1:  # Minimum similarity threshold
            user_similarities[other_user_id] = similarity
    
    # Get product recommendations from similar users
    recommended_products = Counter()
    for other_user_id, similarity in user_similarities.items():
        other_products = user_purchases_map[other_user_id]
        new_products = other_products - user_products
        for product_id in new_products:
            recommended_products[product_id] += similarity
    
    # Convert to recommendation objects
    recommendations = []
    for product_id, score in recommended_products.most_common(5):
        rec = Recommendation(
            user_id=user.id,
            product_id=product_id,
            recommendation_type="collaborative",
            score=score,
            reasons=["Users with similar purchase patterns also bought this"]
        )
        recommendations.append(rec)
    
    return recommendations

async def get_content_based_recommendations(user: User, purchases: List[dict]) -> List[Recommendation]:
    """Get recommendations based on user's purchase patterns and product attributes"""
    if not purchases:
        # For new users, recommend popular products for their business type
        popular_products = await db.products.find({
            "business_types": user.business_type,
            "is_active": True
        }).limit(3).to_list(length=None)
        
        recommendations = []
        for i, product in enumerate(popular_products):
            rec = Recommendation(
                user_id=user.id,
                product_id=product["id"],
                recommendation_type="content_based",
                score=0.8 - (i * 0.1),
                reasons=["Popular among similar businesses"]
            )
            recommendations.append(rec)
        return recommendations
    
    # Analyze user's purchase patterns
    purchased_products = await db.products.find({
        "id": {"$in": [p["product_id"] for p in purchases]}
    }).to_list(length=None)
    
    # Extract categories and tags from purchased products
    categories = Counter()
    tags = Counter()
    
    for product in purchased_products:
        categories[product["category"]] += 1
        for tag in product["tags"]:
            tags[tag] += 1
    
    # Find similar products
    similar_products = await db.products.find({
        "business_types": user.business_type,
        "is_active": True,
        "id": {"$nin": [p["product_id"] for p in purchases]},
        "$or": [
            {"category": {"$in": list(categories.keys())}},
            {"tags": {"$in": list(tags.keys())}}
        ]
    }).to_list(length=None)
    
    # Score products based on similarity
    recommendations = []
    for product in similar_products[:5]:
        score = 0.0
        reasons = []
        
        # Category match
        if product["category"] in categories:
            score += 0.4
            reasons.append(f"Similar to your {product['category']} purchases")
        
        # Tag matches
        matching_tags = set(product["tags"]).intersection(set(tags.keys()))
        if matching_tags:
            score += 0.3 * len(matching_tags)
            reasons.append(f"Matches your interests: {', '.join(list(matching_tags)[:2])}")
        
        if score > 0.2:
            rec = Recommendation(
                user_id=user.id,
                product_id=product["id"],
                recommendation_type="content_based",
                score=min(score, 1.0),
                reasons=reasons
            )
            recommendations.append(rec)
    
    return recommendations

@api_router.get("/")
async def root():
    return {"message": "Qwipo B2B Recommendation System API"}

# Initialize data on startup
@app.on_event("startup")
async def startup_event():
    await init_sample_data()
    logger.info("Application started successfully")

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
