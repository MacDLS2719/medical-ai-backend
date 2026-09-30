from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.deps import get_db
from app.models.doctor_bank_account import DoctorBankAccount
from app.models.doctor_payment_setting import DoctorPaymentSetting
from app.models.user import User
from app.schemas.doctor_payment import (
    DoctorBankAccountCreate,
    DoctorBankAccountUpdate,
    DoctorBankAccountResponse,
    DoctorPaymentSettingCreate,
    DoctorPaymentSettingUpdate,
    DoctorPaymentSettingResponse
)
from app.core.auth import get_current_user

router = APIRouter()

# --- Bank Accounts ---

@router.get("/bank-accounts", response_model=List[DoctorBankAccountResponse])
def get_bank_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get all bank accounts for the current doctor.
    """
    accounts = db.query(DoctorBankAccount).filter(DoctorBankAccount.doctor_id == current_user.id).all()
    return accounts

@router.post("/bank-accounts", response_model=DoctorBankAccountResponse)
def create_bank_account(
    account_in: DoctorBankAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create a new bank account.
    """
    db_account = DoctorBankAccount(
        doctor_id=current_user.id,
        **account_in.model_dump()
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.put("/bank-accounts/{account_id}", response_model=DoctorBankAccountResponse)
def update_bank_account(
    account_id: int,
    account_in: DoctorBankAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update a bank account.
    """
    db_account = db.query(DoctorBankAccount).filter(
        DoctorBankAccount.id == account_id,
        DoctorBankAccount.doctor_id == current_user.id
    ).first()
    
    if not db_account:
        raise HTTPException(status_code=404, detail="Bank account not found")
        
    update_data = account_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_account, field, value)
        
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.delete("/bank-accounts/{account_id}")
def delete_bank_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Delete a bank account.
    """
    db_account = db.query(DoctorBankAccount).filter(
        DoctorBankAccount.id == account_id,
        DoctorBankAccount.doctor_id == current_user.id
    ).first()
    
    if not db_account:
        raise HTTPException(status_code=404, detail="Bank account not found")
        
    db.delete(db_account)
    db.commit()
    return {"message": "Bank account deleted successfully"}


# --- Payment Settings (Tarifas) ---

@router.get("/settings", response_model=List[DoctorPaymentSettingResponse])
def get_payment_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get all payment settings for the current doctor.
    """
    settings = db.query(DoctorPaymentSetting).filter(DoctorPaymentSetting.doctor_id == current_user.id).all()
    return settings

@router.get("/settings/public/{doctor_id}", response_model=List[DoctorPaymentSettingResponse])
def get_public_payment_settings(
    doctor_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all active payment settings for a specific doctor.
    (Accessible by patients when booking)
    """
    settings = db.query(DoctorPaymentSetting).filter(
        DoctorPaymentSetting.doctor_id == doctor_id,
        DoctorPaymentSetting.is_active == True
    ).all()
    return settings

@router.post("/settings", response_model=DoctorPaymentSettingResponse)
def create_payment_setting(
    setting_in: DoctorPaymentSettingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create a new payment setting (rate).
    """
    db_setting = DoctorPaymentSetting(
        doctor_id=current_user.id,
        **setting_in.model_dump()
    )
    try:
        db.add(db_setting)
        db.commit()
        db.refresh(db_setting)
        return db_setting
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="A payment setting for this consultation type already exists for the doctor."
        )

@router.put("/settings/{setting_id}", response_model=DoctorPaymentSettingResponse)
def update_payment_setting(
    setting_id: int,
    setting_in: DoctorPaymentSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update a payment setting.
    """
    db_setting = db.query(DoctorPaymentSetting).filter(
        DoctorPaymentSetting.id == setting_id,
        DoctorPaymentSetting.doctor_id == current_user.id
    ).first()
    
    if not db_setting:
        raise HTTPException(status_code=404, detail="Payment setting not found")
        
    update_data = setting_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_setting, field, value)
        
    try:
        db.add(db_setting)
        db.commit()
        db.refresh(db_setting)
        return db_setting
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="A payment setting for this consultation type already exists for the doctor."
        )

@router.delete("/settings/{setting_id}")
def delete_payment_setting(
    setting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Delete a payment setting.
    """
    db_setting = db.query(DoctorPaymentSetting).filter(
        DoctorPaymentSetting.id == setting_id,
        DoctorPaymentSetting.doctor_id == current_user.id
    ).first()
    
    if not db_setting:
        raise HTTPException(status_code=404, detail="Payment setting not found")
        
    db.delete(db_setting)
    db.commit()
    return {"message": "Payment setting deleted successfully"}
