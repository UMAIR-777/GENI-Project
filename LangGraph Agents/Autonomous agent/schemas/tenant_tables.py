from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Request Models
class TableCreateRequest(BaseModel):
    table_name: str = Field(..., description="Name of the table to create")
    database_name: str = Field(..., description="Name of the database where the table will be created")
    columns: List[Dict[str, str]] = Field(
        ..., 
        description="List of columns to create in the table",
        example=[
            {"name": "id", "type": "VARCHAR", "options": "PRIMARY KEY"},
            {"name": "name", "type": "VARCHAR", "options": "NOT NULL"},
            
        ]
    )
class RecordInsertRequest(BaseModel):
    database_name: str
    table_name: str
    records: List[Dict[str, Any]]

class UpdateOperation(BaseModel):
    set_values: Dict[str, Any]
    where_conditions: Dict[str, Any]

class RecordUpdateRequest(BaseModel):
    updates: List[UpdateOperation] = Field(
        description="List of update operations with set values and where conditions",
        example=[{
            "set_values": {"name": "Updated Name", "age": 31},
            "where_conditions": {"id": "123"}
        }]
    )

# Response Models
class TableResponse(BaseModel):
    id:str
    name: str
    database_name: str
    tenant_id: str

class TableListItem(BaseModel):
    id: str
    name: str
    columns: List[Dict[str, str]]  # This will contain the schema definition

class TableListResponse(BaseModel):
    tables: List[TableListItem]

# Add this to your schemas file
class TableRenameRequest(BaseModel):
    old_table_name: str
    new_table_name: str

class TableColumnSchema(BaseModel):
    name: str
    type: str
    options: Optional[str] = None


class TableDeleteResponse(BaseModel):
    status: str
    message: str

# Schema for column modifications
class ColumnUpdate(BaseModel):
    current_name: str = Field(..., description="Current name of the column")
    new_name: Optional[str] = Field(None, description="New name for the column (if renaming)")
    new_type: Optional[str] = Field(None, description="New data type for the column (if changing type)")
    new_options: Optional[str] = Field(None, description="New constraints/options for the column")

# Schema for adding new columns
class ColumnAdd(BaseModel):
    name: str = Field(..., description="Name of the new column")
    type: str = Field(..., description="Data type of the new column")
    options: Optional[str] = Field(None, description="Constraints/options for the new column")

# Schema for dropping columns
class ColumnDrop(BaseModel):
    name: str = Field(..., description="Name of the column to drop")

# Combined schema for table column operations
class TableColumnOperation(BaseModel):
    update_columns: Optional[List[ColumnUpdate]] = Field(None, description="Columns to modify")
    add_columns: Optional[List[ColumnAdd]] = Field(None, description="New columns to add")
    drop_columns: Optional[List[ColumnDrop]] = Field(None, description="Columns to drop")

# Request schema for updating table columns
class TableUpdateRequest(BaseModel):
    operations: TableColumnOperation = Field(
        ..., 
        description="Column operations to perform",
        example={
            "update_columns": [
                {"current_name": "name", "new_name": "full_name", "new_type": "VARCHAR", "new_options": "NOT NULL"},
                {"current_name": "age", "new_type": "NUMERIC(5,2)"}
            ],
            "add_columns": [
                {"name": "email", "type": "VARCHAR", "options": "UNIQUE"},
                {"name": "created_at", "type": "TIMESTAMP", "options": "DEFAULT CURRENT_TIMESTAMP"}
            ],
            "drop_columns": [
                {"name": "temporary_field"}
            ]
        }
    )