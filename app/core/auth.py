from fastapi import Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.deps import get_db

def get_current_user(user_id: int = Query(1), db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Fallbacks para IDs de desarrollo/demo hardcodeados en el frontend
        fallback_users = {
            1: User(id=1, email="patient@medical-ai.com", password_hash="nopass", role="patient", is_active=True),
            2: User(id=2, email="doctor@medical-ai.com", password_hash="nopass", role="doctor", is_active=True),
            27: User(id=27, email="verificador@medical-ai.com", password_hash="nopass", role="verifier", is_active=True),
        }
        if user_id in fallback_users:
            user = fallback_users[user_id]
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(status_code=404, detail="User not found")
    return user
