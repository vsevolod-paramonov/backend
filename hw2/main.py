from fastapi import FastAPI, HTTPException
from routes.predict_router import router
from model import get_or_train_model
import logging
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.on_event("startup")
def startup_event():
    logger.info("Starting application...")
    try:
        app.state.model = get_or_train_model()
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        app.state.model = None


app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
