from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드를 허용하려면 "*"
    allow_headers=["*"],  # 모든 HTTP 헤더를 허용하려면 "*"
)


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}
