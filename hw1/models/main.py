from fastapi import FastAPI, HTTPException
from models.obj import PredictRequest
import uvicorn


app = FastAPI()

@app.post("/predict")
def predict(request: PredictRequest) -> bool:
    
    try:
        if request.is_verified_seller:
            return True
        else:
            return request.images_qty > 0

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)