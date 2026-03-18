"""
文件上传与解析路由
"""
import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from backend.services.parser_excel import parse_excel
from backend.services.parser_word import parse_word
from backend.services.data_cleaner import process_records
from backend.models import UploadResult

router = APIRouter(prefix="/api/upload", tags=["文件上传"])


@router.post("/", response_model=UploadResult)
async def upload_file(file: UploadFile = File(...)):
    """
    上传并解析教师数据文件
    支持 .xlsx, .xls, .docx, .doc
    """
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
        if ext in (".xlsx", ".xls"):
            records, new_fields = parse_excel(file_path)
        elif ext in (".docx", ".doc"):
            records, new_fields = parse_word(file_path)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
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
    stats = process_records(records)

    return UploadResult(
        filename=filename,
        total_records=len(records),
        new_records=stats["new"],
        updated_records=stats["updated"],
        skipped_records=stats["skipped"],
        new_fields=new_fields,
        errors=stats["errors"]
    )


@router.post("/batch")
async def upload_batch(files: list[UploadFile] = File(...)):
    """批量上传多个文件"""
    results = []
    for file in files:
        try:
            result = await upload_file(file)
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
