from bson import ObjectId
from fastapi import HTTPException


def build_class_code(degree_code: str, branch_code: str, year: int) -> str:
    degree_part = (degree_code or "X").strip().upper()[:1]
    branch_part = (branch_code or "X").strip().upper()[:1]
    year_part = str(year)[-1]
    return f"{degree_part}{branch_part}{year_part}"


async def ensure_class_for_combination(db, college_id: str, degree_id: str, branch_id: str, year: int):
    existing_class = await db.classes.find_one(
        {
            "college_id": college_id,
            "degree_id": degree_id,
            "branch_id": branch_id,
            "year": year,
        }
    )
    if existing_class:
        return existing_class

    degree = await db.degrees.find_one({"_id": ObjectId(degree_id)})
    branch = await db.branches.find_one({"_id": ObjectId(branch_id)})
    if not degree or not branch:
        raise HTTPException(status_code=404, detail="Degree or branch not found")

    class_code = build_class_code(degree.get("code", ""), branch.get("code", ""), year)
    class_name = f"{degree.get('name')} - {branch.get('name')} - Year {year}"
    result = await db.classes.insert_one(
        {
            "college_id": college_id,
            "degree_id": degree_id,
            "branch_id": branch_id,
            "year": year,
            "code": class_code,
            "name": class_name,
        }
    )
    return await db.classes.find_one({"_id": result.inserted_id})
