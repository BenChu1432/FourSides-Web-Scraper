import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  
from app.routers import news_router

app = FastAPI(title="FourSide API")
logger = logging.getLogger(__name__)

# ✅ Allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://main.d3p7jw0sop4gt8.amplifyapp.com","https://main.d3p7jw0sop4gt8.amplifyapp.com/"], 
    allow_credentials=True,
    allow_methods=["*"],  # You can restrict to ['GET', 'POST'] if desired
    allow_headers=["*"],  # You can restrict to specific headers
)

@app.get("/")
def root():
    return {"message": "Welcome to FourSides Web Scraper"}

app.include_router(news_router.router, prefix="/web-scraping", tags=["web-scraping"])
