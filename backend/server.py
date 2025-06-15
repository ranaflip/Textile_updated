from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import json
from pathlib import Path
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import requests
import urllib.robotparser
import re
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Web Scraper Tool", description="Advanced e-commerce scraper for dynamic content")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Define Models
class ScrapingJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    urls: List[str]
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    results: List[Dict[Any, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    total_urls: int = 0
    processed_urls: int = 0

class ScrapingJobCreate(BaseModel):
    urls: List[str]

class ScrapedData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    title: Optional[str] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    items: List[Dict[str, Any]] = Field(default_factory=list)
    prices: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    job_id: str

class WebScraperEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.use_selenium = False  # Start with requests, fallback to selenium if needed
        self.chrome_options = None
        self.driver_path = None
        self.setup_selenium_fallback()
    
    def setup_selenium_fallback(self):
        """Setup Selenium as fallback for JS-heavy sites"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            self.chrome_options = chrome_options
            # We'll enable selenium when Chrome is available
            self.use_selenium = False
            logging.info("Selenium configured as fallback (Chrome not available)")
        except Exception as e:
            logging.error(f"Failed to setup Selenium fallback: {e}")
            self.use_selenium = False

    def check_robots_txt(self, url: str, user_agent: str = "*") -> bool:
        """Check if scraping is allowed according to robots.txt"""
        try:
            parsed_url = requests.utils.urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            return rp.can_fetch(user_agent, url)
        except Exception as e:
            logging.warning(f"Could not check robots.txt for {url}: {e}")
            return True  # Default to allowing if we can't check

    def extract_table_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract structured table data from the page"""
        tables_data = []
        
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            try:
                # Convert table to pandas DataFrame for easier processing
                df = pd.read_html(str(table))[0]
                
                # Convert DataFrame to list of dictionaries
                table_dict = {
                    'table_id': i,
                    'headers': df.columns.tolist(),
                    'rows': df.fillna('').to_dict('records')
                }
                tables_data.append(table_dict)
            except Exception as e:
                logging.error(f"Error processing table {i}: {e}")
                continue
        
        return tables_data

    def extract_price_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract price information from the page"""
        prices = []
        
        # Common price patterns and selectors
        price_patterns = [
            r'\$[\d,]+\.?\d*',  # $123.45, $1,234
            r'£[\d,]+\.?\d*',   # £123.45
            r'€[\d,]+\.?\d*',   # €123.45
            r'₹[\d,]+\.?\d*',   # ₹123.45
            r'price[:\s]*[\d,]+\.?\d*',  # price: 123.45
        ]
        
        price_selectors = [
            '.price', '[class*="price"]', '[id*="price"]',
            '.cost', '[class*="cost"]', '[id*="cost"]',
            '.amount', '[class*="amount"]', '[id*="amount"]',
            '[data-price]', '[data-cost]'
        ]
        
        # Extract using CSS selectors
        for selector in price_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                for pattern in price_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        prices.append({
                            'text': text,
                            'price': match,
                            'selector': selector,
                            'element_tag': element.name
                        })
        
        # Extract using regex patterns on full page text
        page_text = soup.get_text()
        for pattern in price_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                prices.append({
                    'text': match,
                    'price': match,
                    'selector': 'text_pattern',
                    'element_tag': 'text'
                })
        
        # Remove duplicates
        unique_prices = []
        seen = set()
        for price in prices:
            price_key = (price['price'], price['text'])
            if price_key not in seen:
                seen.add(price_key)
                unique_prices.append(price)
        
        return unique_prices

    def extract_item_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract item/product information from the page"""
        items = []
        
        # Common item/product selectors
        item_selectors = [
            '.product', '[class*="product"]',
            '.item', '[class*="item"]',
            '.listing', '[class*="listing"]',
            '[data-product]', '[data-item]'
        ]
        
        for selector in item_selectors:
            elements = soup.select(selector)
            for i, element in enumerate(elements):
                # Extract title/name
                title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or element.find(class_=re.compile(r'title|name', re.I))
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # Extract description
                desc_elem = element.find(class_=re.compile(r'desc|description', re.I))
                description = desc_elem.get_text(strip=True) if desc_elem else ''
                
                # Extract price from within this item
                price_elem = element.find(class_=re.compile(r'price|cost|amount', re.I))
                price = price_elem.get_text(strip=True) if price_elem else ''
                
                # Extract image
                img_elem = element.find('img')
                image_url = img_elem.get('src') if img_elem else ''
                
                if title or description or price:  # Only add if we found some content
                    items.append({
                        'item_id': i,
                        'title': title,
                        'description': description,
                        'price': price,
                        'image_url': image_url,
                        'selector': selector,
                        'html_snippet': str(element)[:500]  # First 500 chars for reference
                    })
        
        return items

    async def scrape_url(self, url: str, job_id: str) -> ScrapedData:
        """Scrape a single URL"""
        scraped_data = ScrapedData(url=url, job_id=job_id)
        
        try:
            # Check robots.txt
            if not self.check_robots_txt(url):
                scraped_data.error = "Scraping not allowed by robots.txt"
                return scraped_data
            
            # Setup driver for this request
            if not self.driver_path:
                raise Exception("Chrome driver not available")
            
            driver = webdriver.Chrome(executable_path=self.driver_path, options=self.chrome_options)
            
            try:
                # Load the page
                driver.get(url)
                
                # Wait for page to load (adjust timeout as needed)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Additional wait for dynamic content
                time.sleep(3)
                
                # Get page source and parse with BeautifulSoup
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Extract title
                title_elem = soup.find('title')
                scraped_data.title = title_elem.get_text(strip=True) if title_elem else 'No Title'
                
                # Extract structured data
                scraped_data.tables = self.extract_table_data(soup)
                scraped_data.items = self.extract_item_data(soup)
                scraped_data.prices = self.extract_price_data(soup)
                
            finally:
                driver.quit()
                
        except Exception as e:
            scraped_data.error = str(e)
            logging.error(f"Error scraping {url}: {e}")
        
        return scraped_data

# Initialize scraper engine
scraper = WebScraperEngine()

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Web Scraper Tool API", "version": "1.0.0"}

@api_router.post("/scrape", response_model=ScrapingJob)
async def create_scraping_job(job_data: ScrapingJobCreate):
    """Create a new scraping job"""
    job = ScrapingJob(
        urls=job_data.urls,
        total_urls=len(job_data.urls)
    )
    
    # Store job in database
    await db.scraping_jobs.insert_one(job.dict())
    
    # Start background processing
    asyncio.create_task(process_scraping_job(job.id))
    
    return job

@api_router.get("/jobs", response_model=List[ScrapingJob])
async def get_scraping_jobs():
    """Get all scraping jobs"""
    jobs = await db.scraping_jobs.find().sort("created_at", -1).to_list(100)
    return [ScrapingJob(**job) for job in jobs]

@api_router.get("/jobs/{job_id}", response_model=ScrapingJob)
async def get_scraping_job(job_id: str):
    """Get a specific scraping job"""
    job = await db.scraping_jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ScrapingJob(**job)

@api_router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """Get results for a specific job"""
    results = await db.scraped_data.find({"job_id": job_id}).to_list(1000)
    return [ScrapedData(**result) for result in results]

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def process_scraping_job(job_id: str):
    """Background task to process scraping job"""
    try:
        # Get job from database
        job_doc = await db.scraping_jobs.find_one({"id": job_id})
        if not job_doc:
            return
        
        job = ScrapingJob(**job_doc)
        
        # Update job status
        await db.scraping_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "in_progress"}}
        )
        
        # Broadcast job started
        await manager.broadcast(json.dumps({
            "type": "job_started",
            "job_id": job_id,
            "total_urls": job.total_urls
        }))
        
        results = []
        processed_count = 0
        
        for url in job.urls:
            try:
                # Scrape the URL
                scraped_data = await scraper.scrape_url(url, job_id)
                
                # Store result in database
                await db.scraped_data.insert_one(scraped_data.dict())
                results.append(scraped_data.dict())
                
                processed_count += 1
                
                # Update job progress
                await db.scraping_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"processed_urls": processed_count}}
                )
                
                # Broadcast progress
                await manager.broadcast(json.dumps({
                    "type": "progress_update",
                    "job_id": job_id,
                    "processed": processed_count,
                    "total": job.total_urls,
                    "current_url": url,
                    "result": scraped_data.dict()
                }))
                
                # Rate limiting - wait between requests
                await asyncio.sleep(2)
                
            except Exception as e:
                logging.error(f"Error processing URL {url} in job {job_id}: {e}")
                processed_count += 1
                
                # Store error result
                error_data = ScrapedData(url=url, job_id=job_id, error=str(e))
                await db.scraped_data.insert_one(error_data.dict())
                
                continue
        
        # Update job as completed
        await db.scraping_jobs.update_one(
            {"id": job_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "processed_urls": processed_count,
                    "results": results
                }
            }
        )
        
        # Broadcast job completed
        await manager.broadcast(json.dumps({
            "type": "job_completed",
            "job_id": job_id,
            "total_results": len(results)
        }))
        
    except Exception as e:
        logging.error(f"Error processing job {job_id}: {e}")
        
        # Update job as failed
        await db.scraping_jobs.update_one(
            {"id": job_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(e),
                    "completed_at": datetime.utcnow()
                }
            }
        )
        
        # Broadcast job failed
        await manager.broadcast(json.dumps({
            "type": "job_failed",
            "job_id": job_id,
            "error": str(e)
        }))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
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