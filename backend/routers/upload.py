"""
文件上传与解析路由
"""
import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from backend.config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from backend.services.parser_excel import parse_excel
from backend.services.parser_word import parse_word
from backend.services.data_cleaner import process_records, analyze_records, MERGE_POLICIES
from backend.models import UploadResult
from backend.services.auth_utils import get_current_user, require_admin

router = APIRouter(prefix="/api/upload", tags=["文件上传"])


def _parse_file_by_ext(file_path: str, ext: str) -> tuple[list[dict], list[str]]:
    if ext in (".xlsx", ".xls"):
        return parse_excel(file_path)
    if ext in (".docx", ".doc"):
        return parse_word(file_path)
    raise HTTPException(status_code=400, detail="不支持的文件类型")


def _validate_merge_policy(merge_policy: str) -> str:
    policy = (merge_policy or "fill_missing").strip()
    if policy not in MERGE_POLICIES:
        raise HTTPException(status_code=400, detail=f"不支持的合并策略: {policy}")
    return policy


@router.post("/", response_model=UploadResult)
async def upload_file(
    file: UploadFile = File(...),
    merge_policy: str = Form("fill_missing"),
    user: dict = Depends(get_current_user)
):
    """
    上传并解析教师数据文件
    支持 .xlsx, .xls, .docx, .doc
    """
    require_admin(user)
    merge_policy = _validate_merge_policy(merge_policy)

    # 检查文件类型
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，请上传 Excel (.xlsx/.xls) 或 Word (.docx/.doc) 文件"
        )

    # 保存上传文件
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # 解析文件
    try:
        records, new_fields = _parse_file_by_ext(file_path, ext)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")

    if not records:
        return UploadResult(
            filename=filename,
            total_records=0,
            new_records=0,
            updated_records=0,
            skipped_records=0,
            new_fields=new_fields,
            errors=["未能从文件中解析到任何教师数据"]
        )

    # 处理数据（清洗、去重、合并）
    stats = process_records(records, merge_policy=merge_policy)

    return UploadResult(
        filename=filename,
        total_records=len(records),
        new_records=stats["new"],
        updated_records=stats["updated"],
        skipped_records=stats["skipped"],
        new_fields=new_fields,
        errors=stats["errors"]
    )


@router.post("/preview")
async def upload_preview(
    file: UploadFile = File(...),
    merge_policy: str = Form("fill_missing"),
    user: dict = Depends(get_current_user)
):
    """预览导入影响（不写入数据库）"""
    require_admin(user)
    merge_policy = _validate_merge_policy(merge_policy)

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，请上传 Excel (.xlsx/.xls) 或 Word (.docx/.doc) 文件"
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    try:
        records, new_fields = _parse_file_by_ext(file_path, ext)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")

    if not records:
        return {
            "filename": filename,
            "merge_policy": merge_policy,
            "total_records": 0,
            "new_records": 0,
            "updated_records": 0,
            "skipped_records": 0,
            "new_fields": new_fields,
            "errors": ["未能从文件中解析到任何教师数据"],
            "samples": []
        }

    stats = analyze_records(records, merge_policy=merge_policy)
    return {
        "filename": filename,
        "merge_policy": merge_policy,
        "total_records": len(records),
        "new_records": stats["new"],
        "updated_records": stats["updated"],
        "skipped_records": stats["skipped"],
        "new_fields": new_fields,
        "errors": stats["errors"],
        "samples": stats["samples"]
    }


@router.post("/batch")
async def upload_batch(
    files: list[UploadFile] = File(...),
    merge_policy: str = Form("fill_missing"),
    user: dict = Depends(get_current_user)
):
    """批量上传多个文件"""
    require_admin(user)
    _validate_merge_policy(merge_policy)
    results = []
    for file in files:
        try:
            result = await upload_file(file, merge_policy=merge_policy, user=user)
            results.append(result)
        except HTTPException as e:
            results.append(UploadResult(
                filename=file.filename or "unknown",
                total_records=0,
                new_records=0,
                updated_records=0,
                skipped_records=0,
                new_fields=[],
                errors=[e.detail]
            ))
    return results
