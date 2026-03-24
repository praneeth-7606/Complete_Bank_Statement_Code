# app/auth_router.py
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
import logging
from . import models
from . import auth_utils

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post("/signup", response_model=models.TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: models.UserSignup):
    """Register a new user with email and password"""
    try:
        logger.info(f"Signup attempt for email: {user_data.email}")
        
        # Check if user already exists
        existing_user = await models.User.find_one(models.User.email == user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = auth_utils.get_password_hash(user_data.password)
        new_user = models.User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            is_active=True,
            is_verified=False,
            created_at=datetime.utcnow()
        )
        
        await new_user.insert()
        logger.info(f"User created successfully: {new_user.email}")
        
        # Create tokens
        tokens = auth_utils.create_tokens_for_user(new_user)
        logger.info(f"Tokens created for user: {new_user.email}")
        
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during signup: {str(e)}"
        )


@router.post("/login", response_model=models.TokenResponse)
async def login(credentials: models.UserLogin):
    """Login with email and password"""
    
    # Find user by email
    user = await models.User.find_one(models.User.email == credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user has a password (not OAuth-only user)
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses Google Sign-In. Please login with Google."
        )
    
    # Verify password
    if not auth_utils.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await user.save()
    
    # Create tokens
    tokens = auth_utils.create_tokens_for_user(user)
    
    return tokens


@router.post("/google", response_model=models.TokenResponse)
async def google_auth(auth_request: models.GoogleAuthRequest):
    """Login or signup with Google OAuth"""
    
    # Verify Google token
    google_user_info = await auth_utils.verify_google_token(auth_request.token)
    
    # Check if user exists
    user = await models.User.find_one(models.User.email == google_user_info["email"])
    
    if user:
        # Existing user - update Google info if needed
        if not user.google_id:
            user.google_id = google_user_info["google_id"]
        if google_user_info.get("profile_picture"):
            user.profile_picture = google_user_info["profile_picture"]
        user.is_verified = True
        user.last_login = datetime.utcnow()
        await user.save()
    else:
        # New user - create account
        user = models.User(
            email=google_user_info["email"],
            full_name=google_user_info["full_name"],
            google_id=google_user_info["google_id"],
            profile_picture=google_user_info.get("profile_picture"),
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        await user.insert()
    
    # Create tokens
    tokens = auth_utils.create_tokens_for_user(user)
    
    return tokens


@router.post("/refresh", response_model=models.TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    
    # Verify refresh token
    payload = auth_utils.verify_token(refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = await models.User.find_one(models.User.user_id == user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    tokens = auth_utils.create_tokens_for_user(user)
    
    return tokens


@router.get("/me", response_model=models.UserResponse)
async def get_current_user_info(current_user: models.User = Depends(auth_utils.get_current_user)):
    """Get current authenticated user information"""
    
    return models.UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        profile_picture=current_user.profile_picture,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )


@router.post("/logout")
async def logout(current_user: models.User = Depends(auth_utils.get_current_user)):
    """Logout current user (client should delete tokens)"""
    
    # In a production app, you might want to blacklist the token here
    # For now, we just return success and let the client delete the token
    
    return {"message": "Successfully logged out"}
