from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routes.apply import apply_router
from server.routes.category import category_router
from server.routes.jobs import job_router
from server.routes.recomend import recommendation_router
from server.routes.user import user
from server.routes.userProfileRoute import user_profile_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user, tags=["User"])
app.include_router(job_router, prefix="/api", tags=["Jobs"])
app.include_router(apply_router, prefix="/api", tags=["Applications"])
app.include_router(recommendation_router, prefix="/api",
                   tags=["Recommendation"])
app.include_router(category_router, prefix="/api", tags=["Category"])
app.include_router(user_profile_router, prefix="/api", tags=["UserProfile"])

# Swagger UI group
app.title = "My API Documentation"
app.description = "API documentation for my application"
app.version = "1.0.0"
