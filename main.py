from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import EmailStr

app = FastAPI()

origins = [
    "http://localhost:4200",  # Replace with your frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Database connection setup
MONGO_URL = "mongodb://localhost:27017"  # Replace with your MongoDB URL
client = AsyncIOMotorClient(MONGO_URL)
db = client.admin_module  # Your database name

# User collection in MongoDB
users_collection = db.get_collection('users')
items_collection = db.get_collection('items')
menus_collection = db.get_collection('menus')
customers_collection = db.get_collection('customers')
branches_collection = db.get_collection('branches')
inventory_collection = db.get_collection('inventory')


# Pydantic Models
class User(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    retype_password: str
    agree_terms: bool

class UserResponse(BaseModel):
    full_name: str
    email: str

    class Config:
        orm_mode = True

class Item(BaseModel):
    name: str
    description: str
    price: float

    class Config:
        orm_mode = True

class Menu(BaseModel):
    name: str
    items: List[str]  # List of item names or ids

    class Config:
        orm_mode = True

class Customer(BaseModel):
    name: str
    email: str
    phone: str

    class Config:
        orm_mode = True

class Branch(BaseModel):
    name: str
    location: str
    contact_number: str

    class Config:
        orm_mode = True

class Inventory(BaseModel):
    item_name: str
    quantity: int

    class Config:
        orm_mode = True


# Utility functions for password hashing and verification
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


# Admin Tasks: CRUD Operations

# Create a user
@app.post("/admin/register", response_model=UserResponse)
async def register(user: User):
    # Password and retype password match validation
    if user.password != user.retype_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Terms and conditions acceptance validation
    if not user.agree_terms:
        raise HTTPException(status_code=400, detail="You must agree to the terms")

    # Check if the user already exists (email uniqueness)
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password before storing it
    hashed_password = hash_password(user.password)

    # Create the user object to store in MongoDB
    new_user = {
        "full_name": user.full_name,
        "email": user.email,
        "password": hashed_password
    }

    # Insert new user into MongoDB
    await users_collection.insert_one(new_user)
    
    return {"message": "Registration successful"}

# Get all users (admin)
@app.get("/admin/users", response_model=List[UserResponse])
async def get_all_users():
    users = await users_collection.find().to_list(100)
    
    if not users:
        raise HTTPException(status_code=404, detail="No users found")

    # Transform the MongoDB response into a list of UserResponse models
    return [{"full_name": user["full_name"], "email": user["email"]} for user in users]


# Admin CRUD for items
@app.post("/admin/items", response_model=Item)
async def create_item(item: Item):
    item_dict = item.dict()
    result = await items_collection.insert_one(item_dict)
    item_dict['id'] = str(result.inserted_id)
    return item_dict

@app.get("/admin/items/{item_id}", response_model=Item)
async def get_item(item_id: str):
    item = await items_collection.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item['id'] = str(item['_id'])
    return item

@app.put("/admin/items/{item_id}", response_model=Item)
async def update_item(item_id: str, item: Item):
    updated_item = await items_collection.find_one_and_update(
        {"_id": ObjectId(item_id)},
        {"$set": item.dict()},
        return_document=True
    )
    if not updated_item:
        raise HTTPException(status_code=404, detail="Item not found")
    updated_item['id'] = str(updated_item['_id'])
    return updated_item

@app.delete("/admin/items/{item_id}")
async def delete_item(item_id: str):
    result = await items_collection.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}


# Admin CRUD for menu
@app.post("/admin/menus", response_model=Menu)
async def create_menu(menu: Menu):
    menu_dict = menu.dict()
    result = await menus_collection.insert_one(menu_dict)
    menu_dict['id'] = str(result.inserted_id)
    return menu_dict

@app.get("/admin/menus/{menu_id}", response_model=Menu)
async def get_menu(menu_id: str):
    menu = await menus_collection.find_one({"_id": ObjectId(menu_id)})
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    menu['id'] = str(menu['_id'])
    return menu

@app.put("/admin/menus/{menu_id}", response_model=Menu)
async def update_menu(menu_id: str, menu: Menu):
    updated_menu = await menus_collection.find_one_and_update(
        {"_id": ObjectId(menu_id)},
        {"$set": menu.dict()},
        return_document=True
    )
    if not updated_menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    updated_menu['id'] = str(updated_menu['_id'])
    return updated_menu

@app.delete("/admin/menus/{menu_id}")
async def delete_menu(menu_id: str):
    result = await menus_collection.delete_one({"_id": ObjectId(menu_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Menu not found")
    return {"message": "Menu deleted successfully"}


# Admin CRUD for customers
@app.post("/admin/customers", response_model=Customer)
async def create_customer(customer: Customer):
    customer_dict = customer.dict()
    result = await customers_collection.insert_one(customer_dict)
    customer_dict['id'] = str(result.inserted_id)
    return customer_dict

@app.get("/admin/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str):
    customer = await customers_collection.find_one({"_id": ObjectId(customer_id)})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer['id'] = str(customer['_id'])
    return customer

@app.put("/admin/customers/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, customer: Customer):
    updated_customer = await customers_collection.find_one_and_update(
        {"_id": ObjectId(customer_id)},
        {"$set": customer.dict()},
        return_document=True
    )
    if not updated_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    updated_customer['id'] = str(updated_customer['_id'])
    return updated_customer

@app.delete("/admin/customers/{customer_id}")
async def delete_customer(customer_id: str):
    result = await customers_collection.delete_one({"_id": ObjectId(customer_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}


# Admin CRUD for branches
@app.post("/admin/branches", response_model=Branch)
async def create_branch(branch: Branch):
    branch_dict = branch.dict()
    result = await branches_collection.insert_one(branch_dict)
    branch_dict['id'] = str(result.inserted_id)
    return branch_dict

@app.get("/admin/branches/{branch_id}", response_model=Branch)
async def get_branch(branch_id: str):
    branch = await branches_collection.find_one({"_id": ObjectId(branch_id)})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    branch['id'] = str(branch['_id'])
    return branch

@app.put("/admin/branches/{branch_id}", response_model=Branch)
async def update_branch(branch_id: str, branch: Branch):
    updated_branch = await branches_collection.find_one_and_update(
        {"_id": ObjectId(branch_id)},
        {"$set": branch.dict()},
        return_document=True
    )
    if not updated_branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    updated_branch['id'] = str(updated_branch['_id'])
    return updated_branch

@app.delete("/admin/branches/{branch_id}")
async def delete_branch(branch_id: str):
    result = await branches_collection.delete_one({"_id": ObjectId(branch_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Branch not found")
    return {"message": "Branch deleted successfully"}


# Admin CRUD for inventory
@app.post("/admin/inventory", response_model=Inventory)
async def create_inventory(inventory: Inventory):
    inventory_dict = inventory.dict()
    result = await inventory_collection.insert_one(inventory_dict)
    inventory_dict['id'] = str(result.inserted_id)
    return inventory_dict

@app.get("/admin/inventory/{inventory_id}", response_model=Inventory)
async def get_inventory(inventory_id: str):
    inventory = await inventory_collection.find_one({"_id": ObjectId(inventory_id)})
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    inventory['id'] = str(inventory['_id'])
    return inventory

@app.put("/admin/inventory/{inventory_id}", response_model=Inventory)
async def update_inventory(inventory_id: str, inventory: Inventory):
    updated_inventory = await inventory_collection.find_one_and_update(
        {"_id": ObjectId(inventory_id)},
        {"$set": inventory.dict()},
        return_document=True
    )
    if not updated_inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    updated_inventory['id'] = str(updated_inventory['_id'])
    return updated_inventory

@app.delete("/admin/inventory/{inventory_id}")
async def delete_inventory(inventory_id: str):
    result = await inventory_collection.delete_one({"_id": ObjectId(inventory_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return {"message": "Inventory item deleted successfully"}
