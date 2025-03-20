# main.py
import uvicorn
from dotenv import load_dotenv
from api.config import initialize_app

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = initialize_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)