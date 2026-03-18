"""
Excel 文件解析服务
支持 .xlsx / .xls 格式
"""
import pandas as pd
from backend.services.field_detector import map_headers, normalize_field_name


def parse_excel(file_path: str) -> tuple[list[dict], list[str]]:
    """
    解析 Excel 文件，返回教师记录列表和新发现的字段

    Returns:
        (records, new_fields)
    """
    records = []
    all_new_fields = []

    try:
        # 读取所有 sheet
        xl = pd.ExcelFile(file_path)
        for sheet_name in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet_name, dtype=str)

            if df.empty:
                continue

            # 清理列名
            df.columns = [str(col).strip() for col in df.columns]

            # 跳过没有有效列名的 sheet
            valid_cols = [col for col in df.columns if col and col != "nan" and not col.startswith("Unnamed")]
            if not valid_cols:
                continue

            # 映射表头
            headers = list(df.columns)
            header_mapping, new_fields = map_headers(headers)
            all_new_fields.extend(new_fields)

            if not header_mapping:
                continue

            # 逐行处理
            for _, row in df.iterrows():
                record = {}
                has_data = False

                for col_idx, (field_name, is_builtin) in header_mapping.items():
                    if col_idx < len(row):
                        value = row.iloc[col_idx]
                        if pd.notna(value) and str(value).strip():
                            record[field_name] = str(value).strip()
                            has_data = True

                # 只添加有数据的行
                if has_data and record:
                    records.append(record)

    except Exception as e:
        raise ValueError(f"Excel 解析错误: {str(e)}")

    return records, list(set(all_new_fields))
