from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

origins = [
    "http://localhost:4200",  
    
    
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


class User(BaseModel):
    full_name: str
    email: str
    password: str
    retype_password: str
    agree_terms: bool


class UserResponse(BaseModel):
    full_name: str
    email: str


mock_db = []

@app.post("/register")
async def register(user: User):
    
    if user.password != user.retype_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    
    if not user.agree_terms:
        raise HTTPException(status_code=400, detail="You must agree to the terms")
    
    
    mock_db.append({
        "full_name": user.full_name,
        "email": user.email,
        "password": user.password  
    })
    
    return {"message": "Registration successful"}

@app.get("/users", response_model=List[UserResponse])
async def get_all_users():
    
    if not mock_db:
        raise HTTPException(status_code=404, detail="No users found")
    
    return mock_db
