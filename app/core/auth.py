from fastapi import Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.deps import get_db

def get_current_user(user_id: int = Query(1), db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
