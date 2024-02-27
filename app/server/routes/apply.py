
import bson
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import  StreamingResponse
from server.auth.auth import RoleChecker, UserRole
from server.config.db import db
from server.models.user import User
from server.routes.user import get_current_user
from bson import ObjectId
import mimetypes
import os
from math import ceil

UPLOADS_DIR = "uploads"

apply_router = APIRouter()

@apply_router.post("/apply", dependencies=[Depends(RoleChecker([UserRole.JOBSEEKER]))])
async def create_application( user_id: str, job_id: str, resume: UploadFile = File(...), cover_letter: UploadFile = File(None),current_user: User = Depends(get_current_user)):
    # Check if the user has already applied for the job
    current_user_name = current_user["name"]

    existing_application = db.applications.find_one(
        {"user_id": user_id, "job_id": job_id})
    if existing_application:
        raise HTTPException(
            status_code=400, detail="You have already applied for this job")

   
    resume_filename = os.path.join(UPLOADS_DIR, f"{current_user_name}_resume_{resume.filename}")
    
    with open(resume_filename, "wb") as f:
        f.write(await resume.read())

    cover_letter_filename = None
    if cover_letter is not None:
        cover_letter_filename = os.path.join(UPLOADS_DIR, f"{current_user_name}_cover_letter_{cover_letter.filename}")
        with open(cover_letter_filename, "wb") as f:
            f.write(await cover_letter.read())

    application_data = {
        "user_id": ObjectId(user_id),
        "job_id": ObjectId(job_id),
        "resume_filename": resume_filename,
        "cover_letter_filename": cover_letter_filename,
    }
    db.applications.insert_one(application_data)

    return {"message": "Applied for job successfully"}

@apply_router.get("/application")
async def get_all_applications(
    job_id: str = Query(None),
    user_id: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user),
):
    filter_params = {}
    if job_id:
        filter_params["job_id"] = ObjectId(job_id)
    if user_id:
        filter_params["user_id"] = ObjectId(user_id)

    # Use aggregation to filter applications for jobs posted by the current user
    jobs_by_user = list(db.jobs.find({"employer_id": current_user["_id"]}))
    job_ids_by_user = [str(job["_id"]) for job in jobs_by_user]

    if job_ids_by_user:
        filter_params["job_id"] = {"$in": job_ids_by_user}

    pipeline = [
        {"$match": filter_params},
        {"$skip": (page - 1) * limit},
        {"$limit": limit}
    ]

    total_applications = db.applications.count_documents(filter_params)
    total_pages = ceil(total_applications / limit)

    applications = list(db.applications.aggregate(pipeline))

    application_list = []
    for application in applications:
        application["_id"] = str(application["_id"])
        application["user_id"] = str(application["user_id"])
        application["job_id"] = str(application["job_id"])

        # Retrieve the user information for the application
        user = db.users.find_one({"_id": ObjectId(application["user_id"])})
        if user:
            user["_id"] = str(user["_id"])
            application["user_name"] = user.get("name", "")
            application["user_email"] = user.get("email", "")

        # Retrieve the job information for the application
        job = db.jobs.find_one({"_id": ObjectId(application["job_id"])})
        if job:
            job["_id"] = str(job["_id"])
            application["job_title"] = job.get("title", "")

        application_list.append(application)

    return {
        "total_applications": total_applications,
        "total_pages": total_pages,
        "current_page": page,
        "applications": application_list,
    }

@apply_router.delete("/delete_application", dependencies=[Depends(RoleChecker([UserRole.ADMIN]))])
async def delete_application(application_id:str):
    # Check if the application exists
    existing_application = db.applications.find_one(
        {"_id": ObjectId(application_id)})

    if not existing_application:
        raise HTTPException(
            status_code=404, detail="Application not found")

    # Delete the application
    db.applications.delete_one({"_id": ObjectId(application_id)})

    # Optionally, delete associated files (resume and cover letter)
    if existing_application.get("resume_filename"):
        os.remove(existing_application["resume_filename"])
    if existing_application.get("cover_letter_filename"):
        os.remove(existing_application["cover_letter_filename"])

    return {"message": "Application deleted successfully"}


@apply_router.get("/application/resume/{application_id}")
async def get_application_resume(application_id: str, response: Response):
    try:
        obj_id = ObjectId(application_id)
    except (bson.errors.InvalidId, ValueError):
        raise HTTPException(status_code=400, detail="Invalid application ID")

    application = db.applications.find_one({"_id": obj_id})
    print("application", application,obj_id)
    if application:
        # Convert ObjectId to string
        application["_id"] = str(application["_id"])

        resume_filename = application["resume_filename"]
        file_path = f"{resume_filename}"

        # Check if the file exists
        if os.path.isfile(file_path):
            # Set the Content-Type header based on the file type
            file_extension = os.path.splitext(resume_filename)[1]
            content_type = mimetypes.types_map.get(
                file_extension, "application/octet-stream")
            response.headers["Content-Type"] = content_type

            # Set the Content-Disposition header to suggest a filename
            response.headers["Content-Disposition"] = f"inline; filename={resume_filename}"

            # Return the file as a streaming response
            return StreamingResponse(open(file_path, "rb"), media_type=content_type)
        else:
            return {"message": "File not found"}
    else:
        return {"message": "Application not found"}

@apply_router.get("/application/cover_letter/{application_id}")
async def get_application_cover_letter(application_id: str, response: Response):
    try:
        obj_id = ObjectId(application_id)
    except (bson.errors.InvalidId, ValueError):
        raise HTTPException(status_code=400, detail="Invalid application ID")

    application = db.applications.find_one({"_id": obj_id})
    if application:
        # Convert ObjectId to string
        application["_id"] = str(application["_id"])

        cover_letter_filename = application["cover_letter_filename"]
        file_path = f"{cover_letter_filename}"

        # Check if the file exists
        if os.path.isfile(file_path):
            # Set the Content-Type header based on the file type
            file_extension = os.path.splitext(cover_letter_filename)[1]
            if file_extension == ".docx":
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                content_type = mimetypes.types_map.get(
                    file_extension, "application/octet-stream")

            response.headers["Content-Type"] = content_type

            # Set the Content-Disposition header to suggest a filename and force download
            response.headers["Content-Disposition"] = f"attachment; filename={cover_letter_filename}"

            # Return the file as a streaming response
            return StreamingResponse(open(file_path, "rb"), media_type=content_type)
        else:
            return {"message": "File not found"}
    else:
        return {"message": "Application not found"}
    
@apply_router.get("/my_applicants")
async def get_applicants_for_current_user_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user),
):
    # Use aggregation to get applicants for jobs posted by the current user
    jobs_by_user = list(db.jobs.find({"employer_id": current_user["_id"]}))
    job_ids_by_user = [ObjectId(job["_id"]) for job in jobs_by_user]
    
    print("jobs_by_user",jobs_by_user)
    print("job_ids_by_user",job_ids_by_user)

    pipeline = [
        {"$match": {"job_id": {"$in": job_ids_by_user}}},
        {"$skip": (page - 1) * limit},
        {"$limit": limit}
    ]

    total_applicants = db.applications.count_documents({"job_id": {"$in": job_ids_by_user}})
    total_pages = ceil(total_applicants / limit)

    applicants = list(db.applications.aggregate(pipeline))

    applicant_list = []
    for applicant in applicants:
        applicant["_id"] = str(applicant["_id"])
        applicant["job_id"] = str(applicant["job_id"])
        applicant["user_id"] = str(applicant["user_id"])

        # Retrieve the user information for the applicant
        user = db.users.find_one({"_id": ObjectId(applicant["user_id"])})
        if user:
            user["_id"] = str(user["_id"])
            applicant["user_name"] = user.get("name", "")
            applicant["user_email"] = user.get("email", "")

        # Retrieve the job information for the applicant
        job = db.jobs.find_one({"_id": ObjectId(applicant["job_id"])})
        if job:
            job["_id"] = str(job["_id"])
            applicant["job_title"] = job.get("title", "")

        applicant_list.append(applicant)

    return {
        "total_applicants": total_applicants,
        "total_pages": total_pages,
        "current_page": page,
        "applicants": applicant_list,
    }

@apply_router.get("/applications/me")
async def get_user_applications(current_user: User = Depends(get_current_user)):
    user_id = ObjectId(current_user["_id"])
    applications = list(db.applications.find({"user_id": user_id}))
    
    application_list = []
    for application in applications:
        application["_id"] = str(application["_id"])
        application["job_id"] = str(application["job_id"])
        application["user_id"] = str(application["user_id"])
        application_list.append(application)

    return application_list

@apply_router.get("/applications/aggregation_data", dependencies=[Depends(RoleChecker([UserRole.ADMIN]))])
async def get_user_applications():
    applications_cursor = list(db.applications.aggregate([
    {
        "$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "userdata"
        }
    },
    {
        "$lookup": {
            "from": "jobs",
            "localField": "job_id",
            "foreignField": "_id",
            "as": "jobdata"
        }
    },
    {
        "$project": {
            "user_id": { "$toString": "$user_id" },
            "otherField": 1,
            "job_id": 1,
            "resume_filename": 1,
            "cover_letter_filename": 1,
            "user_name":{
                 "$ifNull": [
                    { "$arrayElemAt": ["$userdata.name", 0] },
                    "N/A",
                ],
            },
            "job_title": {
                "$ifNull": [
                    { "$arrayElemAt": ["$jobdata.title", 0] },
                    "N/A",
                ],
            },
        }
    }
]))
   
    application_list = []
    for application in applications_cursor:
        application["_id"] = str(application["_id"])  # Convert _id to string
        application["user_id"] = str(application["user_id"])  # Convert user_id to string
        application["job_id"] = str(application["job_id"])  # Convert user_id to string
        application_list.append(application)

    return application_list

