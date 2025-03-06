import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:api",
        host="localhost",
        port=8000,
        reload=True,
    )
