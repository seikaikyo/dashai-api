from factory.routes.crud_factory import generate_crud_router
from factory.models.master import (
    Product, ProductCreate, ProductUpdate,
    Material, MaterialCreate, MaterialUpdate,
    Customer, CustomerCreate, CustomerUpdate,
    Supplier, SupplierCreate, SupplierUpdate,
    Equipment, EquipmentCreate, EquipmentUpdate,
    Employee, EmployeeCreate, EmployeeUpdate,
    Location, LocationCreate, LocationUpdate,
)

products_router = generate_crud_router(
    model=Product, create_model=ProductCreate, update_model=ProductUpdate,
    prefix='/master/products', tags=['Master - Products'],
)

materials_router = generate_crud_router(
    model=Material, create_model=MaterialCreate, update_model=MaterialUpdate,
    prefix='/master/materials', tags=['Master - Materials'],
)

customers_router = generate_crud_router(
    model=Customer, create_model=CustomerCreate, update_model=CustomerUpdate,
    prefix='/master/customers', tags=['Master - Customers'],
)

suppliers_router = generate_crud_router(
    model=Supplier, create_model=SupplierCreate, update_model=SupplierUpdate,
    prefix='/master/suppliers', tags=['Master - Suppliers'],
)

equipment_router = generate_crud_router(
    model=Equipment, create_model=EquipmentCreate, update_model=EquipmentUpdate,
    prefix='/master/equipment', tags=['Master - Equipment'],
)

employees_router = generate_crud_router(
    model=Employee, create_model=EmployeeCreate, update_model=EmployeeUpdate,
    prefix='/master/employees', tags=['Master - Employees'],
)

locations_router = generate_crud_router(
    model=Location, create_model=LocationCreate, update_model=LocationUpdate,
    prefix='/master/locations', tags=['Master - Locations'],
)
