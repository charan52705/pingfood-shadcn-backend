import os
import base64
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, model_validator
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId, Binary
from dotenv import load_dotenv
import datetime


load_dotenv()


MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")

if not MONGODB_URI or not MONGODB_DB_NAME:
    raise ValueError("Required MongoDB configuration is missing in the .env file")


def handle_non_utf8(value):
    if isinstance(value, bytes):
        return base64.b64encode(value).decode('utf-8')
    try:
        return value.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        return value


def convert_objectid_to_str(obj):
    if isinstance(obj, dict):
        return {key: convert_objectid_to_str(value) if isinstance(value, (dict, list)) else str(value) if isinstance(value, ObjectId) else handle_non_utf8(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    else:
        return handle_non_utf8(obj)


class Database:
    def __init__(self, uri: str, db_name: str):
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    async def insert_one(self, collection_name: str, document: dict):
        try:
            collection = self.db[collection_name]
            result = await collection.insert_one(document)
            return result  
        except Exception as e:
            print(f"Error inserting document: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    async def find_one(self, collection_name: str, query: dict):
        try:
            collection = self.db[collection_name]
            document = await collection.find_one(query)
            return convert_objectid_to_str(document) if document else None
        except Exception as e:
            print(f"Error finding document: {e}")
            return None

    async def update_one(self, collection_name: str, query: dict, update_data: dict):
        try:
            collection = self.db[collection_name]
            result = await collection.update_one(query, {"$set": update_data})
            return {"modified_count": result.modified_count}
        except Exception as e:
            print(f"Error updating document: {e}")
            return {}

    async def delete_one(self, collection_name: str, query: dict):
        try:
            collection = self.db[collection_name]
            result = await collection.delete_one(query)
            return {"deleted_count": result.deleted_count}
        except Exception as e:
            print(f"Error deleting document: {e}")
            return {}

    async def close(self):
        self.client.close()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class restaurants(BaseModel):
    restaurants_id: int
    res_name: str
    res_email: str
    res_website: str
    res_desc: str
    res_added: Optional[datetime.datetime] = None
    res_active: bool
    city_id: str
    state_id: str

class Branch(BaseModel):
    branch_id: int
    branch_name: str
    branch_email: str
    branch_phone: str
    branch_website: str
    branch_desc: str
    branch_added: Optional[datetime.datetime] = None
    branch_active: bool
    restaurants_id: Optional[str]  
    address_id: Optional[str]  

class Order(BaseModel):
    order_id: str
    customer: dict
    order_type: str
    store: dict
    items: List[dict]
    total_price: float
    payment_method: str
    order_status: str
    order_date: datetime.datetime


    @model_validator(mode='before')
    def convert_binary_fields_to_base64(cls, values):
        if 'restaurants_id' in values and isinstance(values['restaurants_id'], Binary):
            values['restaurants_id'] = base64.b64encode(values['restaurants_id']).decode('utf-8')
        if 'address_id' in values and isinstance(values['address_id'], Binary):
            values['address_id'] = base64.b64encode(values['address_id']).decode('utf-8')
        return values

    @model_validator(mode='after')
    def convert_base64_to_binary(cls, values):
        if 'restaurants_id' in values and isinstance(values['restaurants_id'], str):
            values['restaurants_id'] = Binary(base64.b64decode(values['restaurants_id']))
        if 'address_id' in values and isinstance(values['address_id'], str):
            values['address_id'] = Binary(base64.b64decode(values['address_id']))
        return values

    class Config:
        arbitrary_types_allowed = True  



class User(BaseModel):
    id: int
    firstname: str
    lastname: str
    email: str
    phone: str
    password: str
    address_street: str
    address_city: str
    address_state: str
    address_zip: int
    user_active: bool
    role: str

    class Config:
        arbitrary_types_allowed = True  


class MenuItem(BaseModel):
    item_id: str  
    name: str
    description: str
    price: float
    category: str
    available: bool

    class Config:
        arbitrary_types_allowed = True  



db = Database(MONGODB_URI, MONGODB_DB_NAME)



@app.post("/create-branch/")
async def create_branch(branch: Branch):
    if not branch.branch_added:
        branch.branch_added = datetime.datetime.now()  
    branch_data = branch.dict()
    result = await db.insert_one("Branch", branch_data)

    if result.acknowledged:
        return {"message": "Branch created successfully", "branch_id": branch.branch_id}
    raise HTTPException(status_code=400, detail="Failed to create branch")


@app.get("/branch/{branch_id}")
async def get_branch(branch_id: int):
    result = await db.find_one("Branch", {"branch_id": branch_id})
    if result:
        return result
    raise HTTPException(status_code=404, detail="Branch not found")


@app.put("/branch/{branch_id}")
async def update_branch(branch_id: int, branch: Branch):
    branch_dict = branch.dict(exclude_unset=True)
    if not branch_dict:
        raise HTTPException(status_code=400, detail="No data provided to update")

    result = await db.update_one("Branch", {"branch_id": branch_id}, branch_dict)
    if result and result.get("modified_count", 0) > 0:
        return {"message": "Branch updated successfully"}
    raise HTTPException(status_code=400, detail="Failed to update branch")


@app.delete("/branch/{branch_id}")
async def delete_branch(branch_id: int):
    branch = await db.find_one("Branch", {"branch_id": branch_id})
    if not branch:
        raise HTTPException(status_code=400, detail="Branch not found")

    result = await db.delete_one("Branch", {"branch_id": branch_id})
    if result and result.get("deleted_count", 0) > 0:
        return {"message": "Branch deleted successfully"}
    raise HTTPException(status_code=400, detail="Failed to delete branch")


@app.get("/branches/")
async def get_all_branches():
    branches = await db.db["Branch"].find().to_list(length=200)
    return convert_objectid_to_str(branches)





@app.post("/create-user/")
async def create_user(user: User):
    user_data = user.dict()
    result = await db.insert_one("userData", user_data)

    if result.acknowledged:
        return {"message": "User created successfully", "user_id": user.id}
    raise HTTPException(status_code=400, detail="Failed to create user")


@app.get("/user/{user_id}")
async def get_user(user_id: int):
    result = await db.find_one("userData", {"id": user_id})
    if result:
        return result
    raise HTTPException(status_code=404, detail="User not found")


@app.put("/user/{user_id}")
async def update_user(user_id: int, user: User):
    user_dict = user.dict(exclude_unset=True)
    if not user_dict:
        raise HTTPException(status_code=400, detail="No data provided to update")

    result = await db.update_one("userData", {"id": user_id}, user_dict)
    if result and result.get("modified_count", 0) > 0:
        return {"message": "User updated successfully"}
    raise HTTPException(status_code=400, detail="Failed to update user")


@app.delete("/user/{user_id}")
async def delete_user(user_id: int):
    user = await db.find_one("userData", {"id": user_id})
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    result = await db.delete_one("userData", {"id": user_id})
    if result and result.get("deleted_count", 0) > 0:
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=400, detail="Failed to delete user")


@app.get("/users/")
async def get_all_users():
    users = await db.db["userData"].find().to_list(length=200)
    return convert_objectid_to_str(users)




@app.post("/create-menu-item/")
async def create_menu_item(item: MenuItem):
    item_data = item.dict()
    result = await db.insert_one("menu", item_data)

    if result.acknowledged:
        return {"message": "Menu item created successfully", "item_id": item.item_id}
    raise HTTPException(status_code=400, detail="Failed to create menu item")


@app.get("/menu-item/{item_id}")
async def get_menu_item(item_id: str):
    result = await db.find_one("menu", {"item_id": item_id})
    if result:
        return result
    raise HTTPException(status_code=404, detail="Menu item not found")


@app.put("/menu-item/{item_id}")
async def update_menu_item(item_id: str, item: MenuItem):
    item_dict = item.dict(exclude_unset=True)
    if not item_dict:
        raise HTTPException(status_code=400, detail="No data provided to update")

    result = await db.update_one("menu", {"item_id": item_id}, item_dict)
    if result and result.get("modified_count", 0) > 0:
        return {"message": "Menu item updated successfully"}
    raise HTTPException(status_code=404, detail="Menu item not found")

@app.delete("/menu-item/{item_id}")
async def delete_menu_item(item_id: str):
    
    menu_item = await db.find_one("menu", {"item_id": item_id})
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    
    result = await db.delete_one("menu", {"item_id": item_id})
    if result and result.get("deleted_count", 0) > 0:
        return {"message": "Menu item deleted successfully"}
    
    raise HTTPException(status_code=400, detail="Failed to delete menu item")



@app.get("/menu-items/")
async def get_all_menu_items():
    menu_items = await db.db["menu"].find().to_list(length=200)
    return convert_objectid_to_str(menu_items)


@app.post("/create-order/")
async def create_order(order: Order):
    order_data = order.dict()
    result = await db.insert_one("orders", order_data)

    if result.acknowledged:
        return {"message": "Order created successfully", "order_id": order.order_id}
    raise HTTPException(status_code=400, detail="Failed to create order")


@app.get("/order/{order_id}")
async def get_order(order_id: str):
    result = await db.find_one("orders", {"order_id": order_id})
    if result:
        return result
    raise HTTPException(status_code=404, detail="Order not found")


@app.put("/order/{order_id}")
async def update_order(order_id: str, order: Order):
    order_dict = order.dict(exclude_unset=True)
    if not order_dict:
        raise HTTPException(status_code=400, detail="No data provided to update")

    result = await db.update_one("orders", {"order_id": order_id}, order_dict)
    if result and result.get("modified_count", 0) > 0:
        return {"message": "Order updated successfully"}
    raise HTTPException(status_code=404, detail="Order not found")


@app.delete("/order/{order_id}")
async def delete_order(order_id: str):
    order = await db.find_one("orders", {"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    result = await db.delete_one("orders", {"order_id": order_id})
    if result and result.get("deleted_count", 0) > 0:
        return {"message": "Order deleted successfully"}
    raise HTTPException(status_code=400, detail="Failed to delete order")


@app.get("/orders/")
async def get_all_orders():
    orders = await db.db["orders"].find().to_list(length=200)
    return convert_objectid_to_str(orders)

@app.post("/create-restaurants/")
async def create_restaurants(restaurants: restaurants):
    # If no date is provided, set it to the current timestamp
    if not restaurants.res_added:
        restaurants.res_added = datetime.datetime.now()

    # Convert restaurants data to dictionary and insert into database
    restaurants_data = restaurants.dict()
    result = await db.insert_one("restaurants", restaurants_data)

    # Return success or failure message
    if result.acknowledged:
        return {"message": "restaurants created successfully", "restaurants_id": restaurants.restaurants_id}
    raise HTTPException(status_code=400, detail="Failed to create restaurants")


@app.get("/restaurants/{restaurants_id}")
async def get_restaurants(restaurants_id: int):
    # Find a restaurants by its ID
    result = await db.find_one("restaurants", {"restaurants_id": restaurants_id})
    if result:
        return result
    raise HTTPException(status_code=404, detail="restaurants not found")


@app.put("/restaurants/{restaurants_id}")
async def update_restaurants(restaurants_id: int, restaurants: restaurants):
    # Update only the fields provided in the request body
    restaurants_dict = restaurants.dict(exclude_unset=True)
    if not restaurants_dict:
        raise HTTPException(status_code=400, detail="No data provided to update")

    # Perform the update in the database
    result = await db.update_one("restaurants", {"restaurants_id": restaurants_id}, restaurants_dict)
    if result and result.get("modified_count", 0) > 0:
        return {"message": "restaurants updated successfully"}
    raise HTTPException(status_code=400, detail="Failed to update restaurants")


@app.delete("/restaurants/{restaurants_id}")
async def delete_restaurants(restaurants_id: int):
    # Check if the restaurants exists before deleting
    restaurants = await db.find_one("restaurants", {"restaurants_id": restaurants_id})
    if not restaurants:
        raise HTTPException(status_code=400, detail="restaurants not found")

    # Perform the delete operation
    result = await db.delete_one("restaurants", {"restaurants_id": restaurants_id})
    if result and result.get("deleted_count", 0) > 0:
        return {"message": "restaurants deleted successfully"}
    raise HTTPException(status_code=400, detail="Failed to delete restaurants")


@app.get("/restaurants/")
async def get_all_restaurantss():
    # Fetch all restaurantss from the database, with a limit of 200
    restaurantss = await db.db["restaurants"].find().to_list(length=200)
    return convert_objectid_to_str(restaurantss)
