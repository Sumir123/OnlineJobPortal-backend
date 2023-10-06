import uvicorn

if __name__ == "__main__":
    uvicorn.run("server.app:app", host="localhost", port=4000, reload=True)
