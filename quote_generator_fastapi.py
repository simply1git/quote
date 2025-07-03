import asyncio
import logging
import random
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn
import csv
from io import StringIO
from fastapi.responses import StreamingResponse
import pytz  # Added for IST timezone

# Configure logging
logging.basicConfig(
    filename='quote_generator.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize FastAPI
app = FastAPI(title="Quote Generator")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# SQLite setup
DATABASE_URL = "sqlite:///quotes.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True)
    timestamp = Column(String)
    quote = Column(String)
    author = Column(String)
    image_prompt = Column(String)
    image_style = Column(String)
    keywords = Column(String)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Quote templates
QUOTE_TEMPLATES = [
    {
        "theme": "inspiration",
        "structure": "{adjective} {noun}, {verb} with {quality} to {goal}.",
        "keywords": ["inspiration", "motivation", "success", "hope", "dream big"],
        "words": {
            "adjective": ["Courageous", "Visionary", "Resilient", "Bold", "Wise"],
            "noun": ["hearts", "minds", "souls", "dreamers", "spirits"],
            "verb": ["forge ahead", "rise above", "embrace", "pursue", "inspire"],
            "quality": ["unwavering determination", "boundless passion", "relentless hope", "fearless resolve", "enduring faith"],
            "goal": ["achieve greatness", "shape a brighter future", "leave a legacy", "reach new heights", "create change"]
        }
    },
    {
        "theme": "philosophy",
        "structure": "To {verb} is to {action} the {aspect} of {concept}.",
        "keywords": ["philosophy", "wisdom", "life lessons", "truth", "self reflection"],
        "words": {
            "verb": ["live", "exist", "thrive", "question", "reflect"],
            "action": ["embrace", "challenge", "unravel", "seek", "define"],
            "aspect": ["essence", "truth", "mystery", "depth", "core"],
            "concept": ["life", "destiny", "humanity", "existence", "wisdom"]
        }
    },
    {
        "theme": "motivation",
        "structure": "The {noun} to {source} lies in {action} with {quality}.",
        "keywords": ["motivation", "success", "productivity", "growth", "inspire"],
        "words": {
            "noun": ["path", "journey", "secret", "key", "power"],
            "source": ["success", "happiness", "fulfillment", "victory", "growth"],
            "action": ["moving forward", "persisting", "dreaming big", "taking risks", "never giving up"],
            "quality": ["courage", "resilience", "passion", "grit", "heart"]
        }
    }
]

AUTHORS = ["Philosopher Sage", "Modern Visionary", "Timeless Poet", "Inspirational Leader", "Eternal Dreamer"]
IMAGE_STYLES = ["cinematic", "surreal", "impressionist", "futuristic", "classic painting"]
SHORTS_MODE = True  # Enable shorter quotes for YouTube Shorts

def generate_dynamic_quote():
    """Generate a dynamic quote with keywords."""
    try:
        template = random.choice(QUOTE_TEMPLATES)
        words = template["words"]
        quote = template["structure"].format(
            adjective=random.choice(words.get("adjective", [""])),
            noun=random.choice(words.get("noun", [""])),
            verb=random.choice(words.get("verb", [""])),
            quality=random.choice(words.get("quality", [""])),
            goal=random.choice(words.get("goal", [""])),
            action=random.choice(words.get("action", [""])),
            aspect=random.choice(words.get("aspect", [""])),
            concept=random.choice(words.get("concept", [""])),
            source=random.choice(words.get("source", [""]))
        )
        if SHORTS_MODE and len(quote) > 40:
            quote = quote[:37] + "..."
        author = random.choice(AUTHORS)
        keywords = ",".join(template["keywords"])
        logging.info(f"Generated quote: {quote} by {author}")
        return quote, author, keywords
    except Exception as e:
        logging.error(f"Quote generation failed: {e}")
        return None, None, None

def generate_image_prompt(quote, author):
    """Generate a creative image prompt."""
    try:
        quote_lower = quote.lower()
        style = random.choice(IMAGE_STYLES)
        if any(word in quote_lower for word in ["courage", "resilient", "grit", "resolve"]):
            prompt = f"A {style} scene of a lone warrior on a cliff at sunrise, armor glinting, stormy sky parting to reveal hope, inspired by {author}'s words."
        elif any(word in quote_lower for word in ["dream", "vision", "hope", "future"]):
            prompt = f"A {style} dreamscape with floating islands, glowing stars, and a figure reaching for a radiant horizon, capturing {author}'s vision."
        elif any(word in quote_lower for word in ["wisdom", "truth", "philosophy", "reflect"]):
            prompt = f"A {style} library bathed in golden light, a sage pondering glowing manuscripts, reflecting {author}'s philosophical depth."
        else:
            prompt = f"A {style} cityscape at twilight, a dreamer gazing at stars, embodying {author}'s timeless inspiration."
        logging.info(f"Generated image prompt: {prompt}")
        return prompt, style
    except Exception as e:
        logging.error(f"Image prompt generation failed: {e}")
        return None, None

async def background_generator():
    """Run quote generation every 10 seconds."""
    while True:
        try:
            session = Session()
            quote, author, keywords = generate_dynamic_quote()
            if quote and author:
                image_prompt, image_style = generate_image_prompt(quote, author)
                if image_prompt:
                    ist = pytz.timezone('Asia/Kolkata')
                    ist_time = datetime.now(ist).isoformat()
                    new_quote = Quote(
                        timestamp=ist_time,
                        quote=quote,
                        author=author,
                        image_prompt=image_prompt,
                        image_style=image_style,
                        keywords=keywords
                    )
                    session.add(new_quote)
                    session.commit()
                    logging.info("Saved quote to database.")
            session.close()
        except Exception as e:
            logging.error(f"Background generator error: {e}")
        await asyncio.sleep(10)

# Start background scheduler
scheduler = AsyncIOScheduler()
scheduler.start()
scheduler.add_job(background_generator, 'interval', seconds=10)

# Pydantic models
class QuoteResponse(BaseModel):
    id: int
    timestamp: str
    quote: str
    author: str
    image_prompt: str
    image_style: str
    keywords: str

class QuoteUpdate(BaseModel):
    quote: str
    author: str
    image_prompt: str
    image_style: str
    keywords: str

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page with recent quotes."""
    try:
        session = Session()
        quotes = session.query(Quote).order_by(Quote.timestamp.desc()).limit(10).all()
        latest_quote = quotes[0] if quotes else None
        session.close()
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist).strftime("%I:%M %p IST on %A, %B %d, %Y")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "quotes": quotes,
            "meta_description": latest_quote.quote if latest_quote else "Inspirational quotes updated every 10 seconds.",
            "og_title": "Inspirational Quote Generator",
            "og_description": latest_quote.quote if latest_quote else "Discover new quotes for motivation and YouTube content!",
            "current_time": current_time
        })
    except Exception as e:
        logging.error(f"Index route error: {e}")
        raise HTTPException(status_code=500, detail="Error loading quotes")

@app.get("/api/quotes", response_model=list[QuoteResponse])
async def get_quotes(shorts_only: bool = False):
    """API endpoint to fetch recent quotes, optionally filtered for Shorts."""
    try:
        session = Session()
        query = session.query(Quote).order_by(Quote.timestamp.desc()).limit(10)
        if shorts_only:
            query = query.filter(len(Quote.quote) <= 40)
        quotes = query.all()
        session.close()
        return [{
            "id": q.id,
            "timestamp": q.timestamp,
            "quote": q.quote,
            "author": q.author,
            "image_prompt": q.image_prompt,
            "image_style": q.image_style,
            "keywords": q.keywords
        } for q in quotes]
    except Exception as e:
        logging.error(f"API quotes error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch quotes")

@app.delete("/api/quotes/{quote_id}")
async def delete_quote(quote_id: int):
    """Delete a quote by ID."""
    try:
        session = Session()
        quote = session.query(Quote).filter(Quote.id == quote_id).first()
        if not quote:
            session.close()
            raise HTTPException(status_code=404, detail="Quote not found")
        session.delete(quote)
        session.commit()
        session.close()
        logging.info(f"Deleted quote ID: {quote_id}")
        return {"message": "Quote deleted successfully"}
    except Exception as e:
        logging.error(f"Delete quote error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete quote")

@app.put("/api/quotes/{quote_id}", response_model=QuoteResponse)
async def update_quote(quote_id: int, update: QuoteUpdate):
    """Update a quote by ID."""
    try:
        session = Session()
        quote = session.query(Quote).filter(Quote.id == quote_id).first()
        if not quote:
            session.close()
            raise HTTPException(status_code=404, detail="Quote not found")
        quote.quote = update.quote
        quote.author = update.author
        quote.image_prompt = update.image_prompt
        quote.image_style = update.image_style
        quote.keywords = update.keywords
        session.commit()
        updated_quote = QuoteResponse(
            id=quote.id,
            timestamp=quote.timestamp,
            quote=quote.quote,
            author=quote.author,
            image_prompt=quote.image_prompt,
            image_style=quote.image_style,
            keywords=quote.keywords
        )
        session.close()
        logging.info(f"Updated quote ID: {quote_id}")
        return updated_quote
    except Exception as e:
        logging.error(f"Update quote error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update quote")

@app.get("/api/quotes/export/{format}")
async def export_quotes(format: str):
    """Export quotes as JSON or CSV."""
    try:
        session = Session()
        quotes = session.query(Quote).order_by(Quote.timestamp.desc()).limit(10).all()
        session.close()
        if format == "json":
            data = [{
                "id": q.id,
                "timestamp": q.timestamp,
                "quote": q.quote,
                "author": q.author,
                "image_prompt": q.image_prompt,
                "image_style": q.image_style,
                "keywords": q.keywords
            } for q in quotes]
            return JSONResponse(content=data, media_type="application/json", headers={"Content-Disposition": "attachment; filename=quotes.json"})
        elif format == "csv":
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "timestamp", "quote", "author", "image_prompt", "image_style", "keywords"])
            writer.writeheader()
            for q in quotes:
                writer.writerow({
                    "id": q.id,
                    "timestamp": q.timestamp,
                    "quote": q.quote,
                    "author": q.author,
                    "image_prompt": q.image_prompt,
                    "image_style": q.image_style,
                    "keywords": q.keywords
                })
            output.seek(0)
            return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=quotes.csv"})
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'json' or 'csv'.")
    except Exception as e:
        logging.error(f"Export quotes error: {e}")
        raise HTTPException(status_code=500, detail="Failed to export quotes")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
