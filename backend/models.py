"""
数据模型定义 - Pydantic schema
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class TeacherBase(BaseModel):
    """教师基础信息"""
    name: Optional[str] = None
    gender: Optional[str] = None
    id_card: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    short_phone: Optional[str] = None
    birth_date: Optional[str] = None
    age: Optional[int] = None
    graduate_school: Optional[str] = None
    education: Optional[str] = None
    political_status: Optional[str] = None
    ethnicity: Optional[str] = None
    native_place: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    position: Optional[str] = None
    subject: Optional[str] = None
    hire_date: Optional[str] = None
    employee_id: Optional[str] = None
    tags: Optional[List[str]] = []


class TeacherCreate(TeacherBase):
    """创建教师"""
    extra_fields: Optional[Dict[str, str]] = {}


class TeacherUpdate(TeacherBase):
    """更新教师"""
    extra_fields: Optional[Dict[str, str]] = {}


class TeacherResponse(TeacherBase):
    """教师响应"""
    id: int
    extra_fields: Dict[str, str] = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class TeacherListResponse(BaseModel):
    """教师列表响应"""
    total: int
    page: int
    page_size: int
    total_pages: int
    data: List[TeacherResponse]


class QueryParams(BaseModel):
    """查询参数"""
    keyword: Optional[str] = None
    gender: Optional[str] = None
    political_status: Optional[str] = None
    education: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    tag: Optional[str] = None
    page: int = 1
    page_size: int = 20


class UploadResult(BaseModel):
    """上传结果"""
    filename: str
    total_records: int
    new_records: int
    updated_records: int
    skipped_records: int
    new_fields: List[str]
    errors: List[str]


class StatsResponse(BaseModel):
    """统计响应"""
    total_teachers: int
    gender_stats: Dict[str, int]
    age_stats: Dict[str, int]
    education_stats: Dict[str, int]
    political_stats: Dict[str, int]


class ChangeLogResponse(BaseModel):
    """变更日志"""
    id: int
    teacher_id: int
    teacher_name: Optional[str] = None
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: str
