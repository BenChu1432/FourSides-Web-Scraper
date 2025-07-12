from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  
from app.routers import web_scraping
from dotenv import load_dotenv
import os

app = FastAPI(title="S-News API")


# ✅ Allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",],  # 👈 Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # You can restrict to ['GET', 'POST'] if desired
    allow_headers=["*"],  # You can restrict to specific headers
)

@app.get("/")
def root():
    return {"message": "Welcome to FourSides Web Scraper"}

app.include_router(web_scraping.router, prefix="/web-scraping", tags=["web-scraping"])
