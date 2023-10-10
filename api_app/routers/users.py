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
from fastapi.responses import RedirectResponse
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
                USER_INFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            user_response.raise_for_status()  # Checking for HTTP errors
            user_info = user_response.json()  # Parsing the JSON response
            print(user_info)
        return user_info  # Returning the user's information

    except httpx.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

    return None  # Return None or some default value if an error occurs


@router.post("/login/google")
async def login_callback(
    response: Response,
    request: schema.GoogleLoginRequest,  # Use the Pydantic model here
    db: Session = Depends(get_db),
):
    # Here you can handle user login, such as creating a session or JWT

    current_user = await get_current_user(request.code)
    if current_user.get("sub") is None:
        user = (
            db.query(models.User)
            .filter(models.User.sub == current_user.get("sub"))
            .first()
        )
        if user is None:
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

            response = {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
    else:
        response.status_code = (
            status.HTTP_403_FORBIDDEN
        )  # Set the status code to 403 here
        response.content = {
            "detail": "Not authorized to perform requested action"
        }  # Set the content to a JSON object here

    return response


@router.post("/refresh-token")
async def refresh_token(refresh_token: schema.RefreshTokenSchema):
    refresh_token = refresh_token.refresh_token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = Oauth2.verify_access_token(refresh_token, credentials_exception)

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
    # Query the user's files that are directly in the "Uploads/{user_email}" directory
    user_info = (
        db.query(models.User).filter(models.User.email == current_user.email).first()
    )

    return user_info


@router.get("/google_redirect")
async def login():
    # Constructing the authorization URL for Google's OAuth2
    authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=email+profile"
    # return {"url": authorization_url}
    # Returning the URL to the client
    return RedirectResponse(authorization_url)


@router.post("/login/demo")
async def demo_account_login(
    response: Response,
    request: schema.DemoAccount,
    db: Session = Depends(get_db),
):
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
