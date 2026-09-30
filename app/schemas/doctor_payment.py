from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, constr

# Doctor Bank Account Schemas
class DoctorBankAccountBase(BaseModel):
    account_holder: str = Field(..., max_length=255)
    bank_name: str = Field(..., max_length=100)
    account_type: str = Field(..., max_length=50)
    account_number: str = Field(..., max_length=100)
    country: str = Field(..., max_length=100)
    currency: str = Field(..., max_length=10)
    is_active: bool = True

class DoctorBankAccountCreate(DoctorBankAccountBase):
    pass

class DoctorBankAccountUpdate(BaseModel):
    account_holder: Optional[str] = Field(None, max_length=255)
    bank_name: Optional[str] = Field(None, max_length=100)
    account_type: Optional[str] = Field(None, max_length=50)
    account_number: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    currency: Optional[str] = Field(None, max_length=10)
    is_active: Optional[bool] = None

class DoctorBankAccountResponse(DoctorBankAccountBase):
    id: int
    doctor_id: int
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Doctor Payment Setting Schemas
class DoctorPaymentSettingBase(BaseModel):
    consultation_type: str = Field(..., max_length=50)
    price: float = Field(..., gt=0)
    currency: str = Field(default="COP", max_length=3)
    is_active: bool = True

class DoctorPaymentSettingCreate(DoctorPaymentSettingBase):
    pass

class DoctorPaymentSettingUpdate(BaseModel):
    consultation_type: Optional[str] = Field(None, max_length=50)
    price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=3)
    is_active: Optional[bool] = None

class DoctorPaymentSettingResponse(DoctorPaymentSettingBase):
    id: int
    doctor_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
