from fastapi import FastAPI
import random

app = FastAPI()

APPLICATIONS = [
    {"metadata": {"name": "frontend"}, "status": {"health": {"status": "Healthy"}, "sync": {"status": "Synced"}}},
    {"metadata": {"name": "backend"}, "status": {"health": {"status": "Healthy"}, "sync": {"status": "Synced"}}},
    {"metadata": {"name": "failing-service"}, "status": {"health": {"status": "Degraded"}, "sync": {"status": "OutOfSync"}}},
    {"metadata": {"name": "auth-service"}, "status": {"health": {"status": "Missing"}, "sync": {"status": "OutOfSync"}}}
]

@app.get("/api/v1/applications")
def get_applications():
    # Randomly update one status to "Degraded"
    apps = APPLICATIONS.copy()
    apps[random.randint(0, 3)]["status"]["health"]["status"] = "Degraded"
    return {"items": apps}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
