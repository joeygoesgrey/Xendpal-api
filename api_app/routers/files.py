from datetime import datetime
from api_app.Oauth2 import get_current_user
from api_app import models, schema
from api_app.models import get_db
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks, Query, Request, status
from fastapi.exceptions import HTTPException
from fastapi import (
    File,
    UploadFile,
    Depends,
    APIRouter,
)
from pathlib import Path
from api_app.extras import send_share_email
import os
from fastapi import UploadFile, File
from pathlib import Path
from sqlalchemy.orm import aliased
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename


router = APIRouter(
    prefix="/file",
    tags={"File": "this is the route concerned with file  upload and group assigning"},
)


@router.post("/upload")
async def upload_file(
    request: Request,
    file_type: str = Query(...),
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    upload_folder = Path(f"Uploads/{current_user.email}")
    upload_folder.mkdir(exist_ok=True)

    file_content = await file.read()

    # Check if the file is a ZIP by reading its signature
    if file_content[:4] != b"PK\x03\x04":
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")

    # Get the size of the uploaded file
    file_size_bytes = len(file_content)

    remaining_space_bytes = current_user.max_space - current_user.space

    if int(file_size_bytes) > int(remaining_space_bytes):
        raise HTTPException(status_code=400, detail="Not enough space to upload file")

    filename = secure_filename(file.filename)

    file_location = upload_folder / filename

    with file_location.open("wb") as buffer:
        buffer.write(file_content)

    file_size_bytes = os.path.getsize(file_location)

    new_file = models.Upload(
        name=str(secure_filename(file.filename)),
        path=str(file_location),
        type=str(file_type) if file_type else "unknown",
        size=file_size_bytes,
        owner_id=current_user.email,
    )

    try:
        # Update the user's space
        current_user.space += file_size_bytes

        # Save the new file to the database
        db.add(new_file)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    # Return the new files' details
    return new_file


# tested


@router.get("/user_items")
async def get_user_content(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Query for owned uploads
    owned_uploads = (
        db.query(models.Upload)
        .filter(models.Upload.owner_id == current_user.email)
        .order_by(models.Upload.created_at.desc())
    )

    # Query for shared uploads
    shared_uploads = (
        db.query(models.Upload)
        .join(models.SharedUpload, models.Upload.id == models.SharedUpload.upload_id)
        .join(
            models.SharedRecipient,
            models.SharedUpload.id == models.SharedRecipient.shared_upload_id,
        )
        .filter(models.SharedRecipient.recipient_email == current_user.email)
        .order_by(models.Upload.created_at.desc())
    )

    # Combine the queries
    user_files = owned_uploads.union(shared_uploads).all()

    # Serialize the files and folders into a response format
    response = {
        "files": [schema.UploadModelSchema.from_orm(file) for file in user_files],
    }

    return response


@router.post("/share-upload")
async def share_upload(
    request: Request,
    share_request: schema.ShareUploadSchema,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Find the upload by ID
    upload = (
        db.query(models.Upload)
        .filter(models.Upload.id == share_request.upload_id)
        .first()
    )
    if not upload or upload.owner_id != current_user.email:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Create a new SharedUpload record
    shared_upload = models.SharedUpload(
        upload_id=share_request.upload_id,
        permission=share_request.permission,
        description=share_request.description,
    )

    # Create a new SharedRecipient record
    shared_recipient = models.SharedRecipient(
        shared_upload=shared_upload,
        recipient_email=share_request.recipient_email,
    )

    template_data = {
        "reciepient_email": share_request.recipient_email,
        "user_email": current_user.email,
        "description": share_request.description,
        "file_path": f"http://localhost:8080/{upload.path}",
        "file_name": upload.name,
        "current_year": datetime.now().year,
        "frontend_url": "xendpal.com.ng",
        "subject": "Xendpal File Share",
    }
    email = share_request.recipient_email
    subject = "Xendpal File Share"
    template_data = template_data
    background_tasks.add_task(send_share_email, email, subject, template_data)
    try:
        db.add(shared_upload)
        db.add(shared_recipient)
        db.commit()
        # Create a new history entry
        new_history_entry = models.History(
            message=f"Your file share - {upload.name} - to {share_request.recipient_email} was successful",
            user_email=current_user.email,
            created_at=datetime.utcnow(),
        )
        db.add(new_history_entry)
        db.commit()
        return status.HTTP_200_OK
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete_upload/{upload_id}")
async def delete_upload(
    request: Request,
    upload_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Find the upload by ID
    upload = db.query(models.Upload).filter(models.Upload.id == upload_id).first()
    if not upload or upload.owner_id != current_user.email:
        raise HTTPException(status_code=404, detail="Upload not found")

    user_folder_path = Path("Uploads") / current_user.email
    file_path = user_folder_path / upload.name

    try:
        # Delete the upload from the database
        db.delete(upload)

        # Update the user's space
        current_user.space -= upload.size
        db.add(current_user)
        db.commit()

        # Delete the specific file from the file system
        if file_path.exists():
            os.remove(file_path)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return status.HTTP_204_NO_CONTENT
