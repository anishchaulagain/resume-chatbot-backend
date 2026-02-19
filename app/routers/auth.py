from fastapi import APIRouter, HTTPException, status
from app.database import get_db
from app.auth.utils import verify_password, create_access_token
from app.models.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    db = get_db()
    admin = await db.admins.find_one({"email": body.email})

    if not admin or not verify_password(body.password, admin["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(data={"sub": admin["email"]})

    return LoginResponse(
        access_token=token,
        admin={
            "email": admin["email"],
            "created_at": admin["created_at"].isoformat(),
        },
    )


@router.get("/me")
async def get_me(current_admin=None):
    """Get current admin profile — requires JWT dependency injection from main app"""
    from app.auth.dependencies import get_current_admin
    from fastapi import Depends

    return current_admin


# Separate protected endpoint
@router.get("/profile")
async def get_profile():
    """This endpoint is defined but the dependency is added in main.py"""
    pass
