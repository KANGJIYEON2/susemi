from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"messeage": "안녕하세요"}