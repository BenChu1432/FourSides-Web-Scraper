from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # ✅ Import CORS middleware
from app.routers import preferences,web_scraping

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
    return {"message": "Welcome to S-News API"}

app.include_router(preferences.router, prefix="/preferences", tags=["preferences"])
app.include_router(web_scraping.router, prefix="/web-scraping", tags=["web-scraping"])