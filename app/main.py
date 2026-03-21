from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_to_mongo, close_mongo
from app.routes import (
    auth, users, academic, announcements, assignments, tracker, 
    reminders, schedule, college_admin, student_profile, dashboard, media
)

app = FastAPI(
    title="ClassBoard API",
    description="Multi-college academic coordination platform",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo()


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(academic.router)
app.include_router(announcements.router)
app.include_router(assignments.router)
app.include_router(tracker.router)
app.include_router(reminders.router)
app.include_router(schedule.router)
app.include_router(college_admin.router)
app.include_router(student_profile.router)
app.include_router(dashboard.router)
app.include_router(media.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
