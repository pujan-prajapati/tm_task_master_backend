from fastapi import HTTPException, status

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.categories.dtos import CategorySchema
from src.modules.categories.models import CategoryModel

from src.utils.helpers import success_response


# ================= CREATE CATEGORY ===========================
def create_category(body: CategorySchema, db: Session, user_id: int):
    query = select(CategoryModel).where(
        CategoryModel.name == body.name, CategoryModel.user_id == user_id
    )
    category = db.scalar(query)

    if category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists"
        )

    new_category = CategoryModel(name=body.name, user_id=user_id)

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return success_response(new_category, "Category created successfully")


# ================= GET CATEGORY ===========================
def get_all_categories(db: Session, user_id: int):
    query = (
        select(CategoryModel)
        .where(CategoryModel.user_id == user_id)
        .order_by(CategoryModel.name)
    )

    categories = db.scalars(query).all()

    return success_response(categories, "Categories fetched successfully")


# ================= GET ONE CATEGORY ===========================
def get_one_category(category_id: int, db: Session, user_id: int):
    category = db.get(CategoryModel, category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Category Not Found"
        )

    if category.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You Are Not Authorized"
        )

    return success_response(category, "Category fetched successfully")


# ================== UPDATE CATEGORY ==============================
def update_category(body: CategorySchema, category_id: int, db: Session, user_id: int):
    category = db.get(CategoryModel, category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Category Not Found"
        )

    if category.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You Are Not Authorized"
        )

    existing_category = db.scalar(
        select(CategoryModel).where(
            CategoryModel.name == body.name,
            CategoryModel.user_id == user_id,
            CategoryModel.id != category_id,
        )
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists"
        )

    category.name = body.name

    db.add(category)
    db.commit()
    db.refresh(category)

    return success_response(category, "Category updated successfully")


# ================== DELETE CATEGORY ==============================
def delete_category(category_id: int, db: Session, user_id: int):
    category = db.get(CategoryModel, category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Category Not Found"
        )

    if category.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You Are Not Authorized"
        )

    db.delete(category)
    db.commit()

    return success_response(None, "Category deleted successfully")
