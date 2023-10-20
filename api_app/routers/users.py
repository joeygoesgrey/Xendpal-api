import datetime
from sqlalchemy import extract, func
from api_app.config import settings
from .. import models, Oauth2, schema
from ..models import get_db
from ..config import settings
from sqlalchemy.orm import Session
from fastapi import Response, status
from fastapi import (
    Depends,
    APIRouter,
)
import httpx
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import HTTPException
from datetime import datetime, timedelta
from sqlalchemy import func, cast, Date
from datetime import date

router = APIRouter(
    prefix="/user",
    tags={"Users": ""},
)


CLIENT_ID = settings.CLIENT_ID
CLIENT_SECRET = settings.CLIENT_SECRET
REDIRECT_URI = settings.REDIRECT_URI
TOKEN_URL = settings.TOKEN_URL
USER_INFO_URL = settings.USER_INFO_URL


# Function to get the monthly usage
def get_monthly_usage(db: Session, email: str):
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    total_size = (
        db.query(func.sum(models.Upload.size))
        .filter(
            models.Upload.owner_id == email, models.Upload.created_at >= one_month_ago
        )
        .scalar()
    )
    return total_size or 0


async def get_current_user(request: str):
    try:
        # Extracting the authorization code from the request's query parameters
        authorization_code = request

        # Preparing the data to exchange the authorization code for an access token
        token_data = {
            "code": authorization_code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        # Creating an HTTP client
        async with httpx.AsyncClient() as client:
            # Sending a POST request to exchange the authorization code for an access token
            token_response = await client.post(TOKEN_URL, data=token_data)
            token_response.raise_for_status()  # Checking for HTTP errors
            token_info = token_response.json()  # Parsing the JSON response

            # Extracting the access token
            access_token = token_info["access_token"]

            # Sending a GET request to fetch the user's information using the access token
            user_response = await client.get(
                USER_INFO_URL, headers={
                    "Authorization": f"Bearer {access_token}"}
            )
            user_response.raise_for_status()  # Checking for HTTP errors
            user_info = user_response.json()  # Parsing the JSON response
        return user_info  # Returning the user's information

    except httpx.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

    return None  # Return None or some default value if an error occurs


@router.post("/login/google")
async def login_callback(
    request: schema.GoogleLoginRequest,  # Use the Pydantic model here
    db: Session = Depends(get_db),
):
    """
    Handles the callback from Google OAuth2 login, and creates or retrieves the user's account in the database.

    Parameters:
    - request: a Pydantic model representing the incoming HTTP request google callback code returned from the frontend, containing the authorization code
    - db: the database session dependency

    Returns:
    - A dictionary containing the access token and refresh token, if the user is successfully authenticated

    Raises:
    - HTTP 403 Forbidden if the user is not authorized to perform the requested action
    """
    # Here you can handle user login, such as creating a session or JWT
    current_user = await get_current_user(request.code)
    if current_user.get("sub"):
        user = (
            db.query(models.User)
            .filter(models.User.sub == current_user.get("sub"))
            .first()
        )
        if not user:
            new_user = models.User(
                email=current_user.get("email"),
                sub=current_user.get("sub"),
                name=current_user.get("name"),  # Changed from email to name
                picture=current_user.get("picture"),
            )
            db.add(new_user)
            db.commit()
            user = new_user  # Update the user variable to reference the new user

        access_token, refresh_token = Oauth2.create_access_token(
            data={"user_email": user.email}
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Not authorized to perform requested action"},
        )


@router.post("/refresh-token")
async def refresh_token(refresh_token: schema.RefreshTokenSchema):
    """
    Refreshes an access token using a refresh token, and returns a new access token.

    Parameters:
    - refresh_token: a Pydantic model representing the refresh token

    Returns:
    - A dictionary containing the new access token

    Raises:
    - HTTP 401 Unauthorized if the refresh token is invalid or expired
    """
    refresh_token = refresh_token.refresh_token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = Oauth2.verify_access_token(
        refresh_token, credentials_exception)

    user_email = token_data.email
    new_access_token = Oauth2.create_access_token(
        {"user_email": user_email}, give=False
    )

    return {
        "access_token": new_access_token,
    }


@router.get("/get-yearly-usage")
async def get_yearly_usage(
    current_user: models.User = Depends(Oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the total size of uploaded files for each month of the current year, for the authenticated user.

    Parameters:
    - current_user: the authenticated user, obtained from the access token
    - db: the database session dependency

    Returns:
    - A dictionary containing two lists: the months (as strings) and the corresponding total usage (in bytes) for each month

    Raises:
    - None
    """
    yearly_usage = (
        db.query(
            extract("month", models.Upload.created_at).label("month"),
            func.sum(models.Upload.size).label("total_size"),
        )
        .filter(
            models.Upload.owner_id == current_user.email,
            extract("year", models.Upload.created_at)
            == func.extract("year", func.current_date()),
        )
        .group_by(extract("month", models.Upload.created_at))
        .all()
    )

    months = [str(record.month) for record in yearly_usage]
    usages = [record.total_size for record in yearly_usage]

    return {"month": months, "usage": usages}


@router.get("/info", response_model=schema.UserBase)
async def get_user_information(
    current_user: models.User = Depends(Oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the user information for the authenticated user.

    Parameters:
    - current_user: the authenticated user, obtained from the access token
    - db: the database session dependency

    Returns:
    - A Pydantic model representing the user information, including the email, name, and profile picture

    Raises:
    - None
    """
    user_info = (
        db.query(models.User).filter(
            models.User.email == current_user.email).first()
    )

    return user_info


@router.get("/google_redirect")
async def login():
    """
    Takes the user to the google callback 
    """
    # Constructing the authorization URL for Google's OAuth2
    authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=email+profile"
    return RedirectResponse(authorization_url)


@router.post("/login/demo")
async def demo_account_login(
    response: Response,
    request: schema.DemoAccount,
    db: Session = Depends(get_db),
):
    """
    Logs in a user with a demo account, or returns an error if the account does not exist.

    Parameters:
    - response: the outgoing HTTP response
    - request: a Pydantic model representing the demo account credentials (email and password)
    - db: the database session dependency

    Returns:
    - A dictionary containing the access token and refresh token, if the user is successfully authenticated

    Raises:
    - HTTP 403 Forbidden if the demo account credentials are invalid
    """
    user = (
        db.query(models.User)
        .filter(models.User.sub == request.password, models.User.email == request.email)
        .first()
    )

    if user is None:
        demo_user = models.User(
            email="demouser@email.com",
            sub="10660460994372209672$",
            picture="https://images.unsplash.com/photo-1510915228340-29c85a43dcfe?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MjB8fHByb2dyYW1tZXIlMjB3b3JraW5nfGVufDB8fDB8fHww&auto=format&fit=crop&w=500&q=60",
            name="Demo User",
        )
        db.add(demo_user)
        db.commit()

    user = (
        db.query(models.User)
        .filter(models.User.sub == request.password, models.User.email == request.email)
        .first()
    )

    if user is None:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {"detail": "Forbidden"}

    else:
        access_token, refresh_token = Oauth2.create_access_token(
            data={"user_email": user.email}
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }


@router.get("/history", response_model=list[schema.HistorySchema])
async def user_history(
    current_user: models.User = Depends(Oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the history of shared uploads for the authenticated user, for the current day.

    Parameters:
    - current_user: the authenticated user, obtained from the access token
    - db: the database session dependency

    Returns:
    - A list of Pydantic models representing the history entries, including the file name, size, and timestamp

    Raises:
    - None
    """
    # Calculate the current date
    today = date.today()

    # Query for history entries for the current day
    user_history = (
        db.query(models.History)
        .filter(models.History.user_email == current_user.email)
        .filter(cast(models.History.created_at, Date) == today)
        .all()
    )

    return user_history
