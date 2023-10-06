from fastapi import APIRouter, HTTPException
from bson import ObjectId
from server.config.db import db
from server.models.category import Category

category_router = APIRouter()


@category_router.post("/categories")
async def create_category(category: Category):
    category_data = category.dict()
    db.categories.insert_one(category_data)
    return {"message": "Category created successfully"}


@category_router.get("/categories")
async def get_all_categories():
    categories = list(db.categories.find())

    category_list = []
    for category in categories:
        category["_id"] = str(category["_id"])

        # Retrieve the count of jobs for the category
        job_count = db.jobs.count_documents({"category": category["name"]})
        category["job_count"] = job_count

        category_list.append(category)

    sorted_categories = sorted(category_list, key=lambda x: x["name"])

    return sorted_categories


@category_router.put("/categories/{category_id}")
async def update_category(category_id: str, category: Category):
    category_data = category.dict()
    category_obj_id = ObjectId(category_id)

    result = db.categories.update_one(
        {"_id": category_obj_id}, {"$set": category_data})

    if result.modified_count == 0:
        raise HTTPException(
            status_code=404, detail="Category not found"
        )

    return {"message": "Category updated successfully"}


@category_router.delete("/categories/{category_id}")
async def delete_category(category_id: str):
    category_obj_id = ObjectId(category_id)

    result = db.categories.delete_one({"_id": category_obj_id})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404, detail="Category not found"
        )

    return {"message": "Category deleted successfully"}
