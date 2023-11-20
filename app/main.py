import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4000))
    uvicorn.run("server.app:app", host="localhost", port=port, reload=True)
