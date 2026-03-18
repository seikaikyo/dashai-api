from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# ==================== Product ====================
class ProductBase(SQLModel):
    code: str = Field(index=True, max_length=50)
    name: str = Field(max_length=200)
    category: str = Field(default='', max_length=100)
    unit: str = Field(default='PCS', max_length=20)
    standard_cost: float = Field(default=0)
    lead_time_days: int = Field(default=0)
    active: bool = Field(default=True)
    note: str = Field(default='')


class Product(ProductBase, table=True):
    __tablename__ = 'products'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(SQLModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    standard_cost: Optional[float] = None
    lead_time_days: Optional[int] = None
    active: Optional[bool] = None
    note: Optional[str] = None


# ==================== Material ====================
class MaterialBase(SQLModel):
    code: str = Field(index=True, max_length=50)
    name: str = Field(max_length=200)
    category: str = Field(default='', max_length=100)
    unit: str = Field(default='PCS', max_length=20)
    safety_stock: float = Field(default=0)
    reorder_point: float = Field(default=0)
    unit_cost: float = Field(default=0)
    supplier_id: Optional[int] = Field(default=None)
    active: bool = Field(default=True)
    note: str = Field(default='')


class Material(MaterialBase, table=True):
    __tablename__ = 'materials'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(SQLModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    safety_stock: Optional[float] = None
    reorder_point: Optional[float] = None
    unit_cost: Optional[float] = None
    supplier_id: Optional[int] = None
    active: Optional[bool] = None
    note: Optional[str] = None


# ==================== Customer ====================
class CustomerBase(SQLModel):
    code: str = Field(index=True, max_length=50)
    name: str = Field(max_length=200)
    contact: str = Field(default='', max_length=100)
    email: str = Field(default='', max_length=200)
    phone: str = Field(default='', max_length=50)
    address: str = Field(default='')
    credit_limit: float = Field(default=0)
    payment_terms: str = Field(default='NET30', max_length=50)
    active: bool = Field(default=True)
    note: str = Field(default='')


class Customer(CustomerBase, table=True):
    __tablename__ = 'customers'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(SQLModel):
    code: Optional[str] = None
    name: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Optional[float] = None
    payment_terms: Optional[str] = None
    active: Optional[bool] = None
    note: Optional[str] = None


# ==================== Supplier ====================
class SupplierBase(SQLModel):
    code: str = Field(index=True, max_length=50)
    name: str = Field(max_length=200)
    contact: str = Field(default='', max_length=100)
    email: str = Field(default='', max_length=200)
    phone: str = Field(default='', max_length=50)
    address: str = Field(default='')
    rating: str = Field(default='B', max_length=5)
    lead_time_days: int = Field(default=7)
    active: bool = Field(default=True)
    note: str = Field(default='')


class Supplier(SupplierBase, table=True):
    __tablename__ = 'suppliers'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(SQLModel):
    code: Optional[str] = None
    name: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[str] = None
    lead_time_days: Optional[int] = None
    active: Optional[bool] = None
    note: Optional[str] = None


# ==================== Equipment ====================
class EquipmentBase(SQLModel):
    code: str = Field(index=True, max_length=50)
    name: str = Field(max_length=200)
    line: str = Field(default='', max_length=100)
    equipment_type: str = Field(default='', max_length=100)
    manufacturer: str = Field(default='', max_length=200)
    model: str = Field(default='', max_length=100)
    install_date: Optional[str] = Field(default=None)
    status: str = Field(default='running', max_length=30)
    active: bool = Field(default=True)
    note: str = Field(default='')


class Equipment(EquipmentBase, table=True):
    __tablename__ = 'equipment'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(SQLModel):
    code: Optional[str] = None
    name: Optional[str] = None
    line: Optional[str] = None
    equipment_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    install_date: Optional[str] = None
    status: Optional[str] = None
    active: Optional[bool] = None
    note: Optional[str] = None


# ==================== Employee ====================
class EmployeeBase(SQLModel):
    code: str = Field(index=True, max_length=50)
    name: str = Field(max_length=100)
    department: str = Field(default='', max_length=100)
    role: str = Field(default='', max_length=100)
    shift: str = Field(default='day', max_length=20)
    skill_level: str = Field(default='L1', max_length=10)
    active: bool = Field(default=True)
    note: str = Field(default='')


class Employee(EmployeeBase, table=True):
    __tablename__ = 'employees'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(SQLModel):
    code: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    shift: Optional[str] = None
    skill_level: Optional[str] = None
    active: Optional[bool] = None
    note: Optional[str] = None


# ==================== Location ====================
class LocationBase(SQLModel):
    code: str = Field(index=True, max_length=50)
    name: str = Field(max_length=200)
    warehouse: str = Field(default='', max_length=100)
    zone: str = Field(default='', max_length=50)
    aisle: str = Field(default='', max_length=20)
    rack: str = Field(default='', max_length=20)
    level: str = Field(default='', max_length=20)
    location_type: str = Field(default='storage', max_length=30)
    max_weight_kg: float = Field(default=1000)
    active: bool = Field(default=True)
    note: str = Field(default='')


class Location(LocationBase, table=True):
    __tablename__ = 'locations'
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LocationCreate(LocationBase):
    pass


class LocationUpdate(SQLModel):
    code: Optional[str] = None
    name: Optional[str] = None
    warehouse: Optional[str] = None
    zone: Optional[str] = None
    aisle: Optional[str] = None
    rack: Optional[str] = None
    level: Optional[str] = None
    location_type: Optional[str] = None
    max_weight_kg: Optional[float] = None
    active: Optional[bool] = None
    note: Optional[str] = None
