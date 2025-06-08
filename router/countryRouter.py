import pathlib
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import pymysql
import os
import dotenv
import json
import pandas as pd
import requests
import re
from datetime import datetime
from typing import List, Union, IO, Dict, Any, Tuple
from io import BytesIO

# 加载数据库连接信息
dotenv.load_dotenv(".env")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
CHARSET = os.getenv("CHARSET")

countryRouter = APIRouter()

# excel 文件中必填字段
REQUIRED_FIELDS = [
    "所属项目",
    "道路名称",
    "道路长度(km)",  # 新增必填字段
    "车道数",
    "道路类型",
    "道路桩号",
    "道路结构名称",
    "行车方向",
    "养护开始时间(年、月、日)",
    "养护结束时间(年、月、日)",
]

# 全局字典，用于存储已创建的一级道路
CREATED_LEVEL1_ROADS = {}  # 格式: {"道路名称": level1_id}

# 系统接口配置
API_BASE_URL = os.getenv("COUNTRY_API_BASE_URL")
API_HEADERS = {
    "Authorization": f"Bearer {os.getenv('API_TOKEN')}",
    "Content-Type": "application/json",
    "client-type": "1",
}


def get_db_connection():
    """
    获取数据库连接

    Returns:
        pymysql.Connection: 数据库连接对象
    """
    try:
        connection = pymysql.connect(
            host=HOST,  # type: ignore
            port=int(PORT),  # type: ignore
            user=USER,  # type: ignore
            password=PASSWORD,  # type: ignore
            database=DATABASE,  # type: ignore
            charset=CHARSET,  # type: ignore
            cursorclass=pymysql.cursors.DictCursor,  # type: ignore
        )
        print(f"数据库连接成功: {DATABASE}")
        return connection
    except Exception as e:
        print(f"数据库连接失败: {e}")
        raise


def query_project_info(project_name: str) -> Dict[str, Any]:
    """
    根据项目名称查询项目ID和租户ID

    Args:
        project_name: 项目名称

    Returns:
        Dict[str, Any]: 包含project_id和tenant_id的字典
    """
    print(f"查询项目信息: {project_name}")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, tenant_id FROM t_system_project WHERE name = %s"
            cursor.execute(sql, (project_name,))
            result = cursor.fetchone()

            if not result:
                raise ValueError(f"项目 '{project_name}' 不存在")

            print(f"项目查询成功: ID={result['id']}, tenant_id={result['tenant_id']}")
            return {"project_id": result["id"], "tenant_id": result["tenant_id"]}
    finally:
        connection.close()


def query_dict_value(dict_type: str, label: str) -> str:
    """
    根据字典类型和标签查询对应的值

    Args:
        dict_type: 字典类型
        label: 标签

    Returns:
        str: 对应的值
    """
    print(f"查询字典值: dict_type={dict_type}, label={label}")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT value FROM t_system_dict_data WHERE dict_type = %s AND label = %s"
            cursor.execute(sql, (dict_type, label))
            result = cursor.fetchone()

            if not result:
                raise ValueError(f"字典值不存在: dict_type={dict_type}, label={label}")

            print(f"字典查询成功: value={result['value']}")
            return result["value"]
    finally:
        connection.close()


def convert_lane_count(lane_text: str) -> int:
    """
    将车道数文本转换为数字

    Args:
        lane_text: 车道数文本（如：单车道、双车道等）

    Returns:
        int: 车道数字
    """
    print(f"转换车道数: {lane_text}")

    lane_mapping = {
        "单车道": 1,
        "双车道": 2,
        "三车道": 3,
        "四车道": 4,
        "五车道": 5,
        "六车道": 6,
        "七车道": 7,
        "八车道": 8,
    }

    if lane_text not in lane_mapping:
        raise ValueError(f"无效的车道数: {lane_text}")

    result = lane_mapping[lane_text]
    print(f"车道数转换成功: {lane_text} -> {result}")
    return result


def parse_stake_range(stake_text: str) -> Tuple[List[Tuple[str, str]], float]:
    """
    解析桩号范围，返回按100m分段的桩号列表和总长度

    Args:
        stake_text: 桩号文本（如：0-1.28 或 K0+000-K1+280）

    Returns:
        Tuple[List[Tuple[str, str]], float]: (桩号分段列表, 总长度km)
    """
    print(f"解析桩号范围: {stake_text}")

    # 处理两种格式：0-1.28 和 K0+000-K1+280
    if "K" in stake_text:
        # K0+000-K1+280 格式
        pattern = r"K(\d+)\+(\d+)-K(\d+)\+(\d+)"
        match = re.match(pattern, stake_text)
        if not match:
            raise ValueError(f"无效的桩号格式: {stake_text}")

        start_km, start_m, end_km, end_m = map(int, match.groups())
        start_total_m = start_km * 1000 + start_m
        end_total_m = end_km * 1000 + end_m
    else:
        # 0-1.28 格式
        try:
            start_km, end_km = map(float, stake_text.split("-"))
            start_total_m = int(start_km * 1000)
            end_total_m = int(end_km * 1000)
        except ValueError:
            raise ValueError(f"无效的桩号格式: {stake_text}")

    # 计算总长度（km）
    total_length_km = (end_total_m - start_total_m) / 1000.0

    # 按100m分段生成桩号列表
    segments = []
    current_m = start_total_m

    while current_m < end_total_m:
        segment_end = min(current_m + 100, end_total_m)  # 取最小值，防止超出结束桩号

        start_stake = f"K{current_m // 1000}+{current_m % 1000:03d}"  # 一定是三位数
        end_stake = f"K{segment_end // 1000}+{segment_end % 1000:03d}"  # 一定是三位数

        segments.append((start_stake, end_stake))
        current_m = segment_end

    print(f"桩号解析成功: 总长度={total_length_km}km, 分段数={len(segments)}")
    # print(f"分段详情: {segments}")

    return segments, total_length_km


def convert_datetime_to_timestamp(date_str: str) -> int:
    """
    将日期字符串转换为毫秒级时间戳

    Args:
        date_str: 日期字符串

    Returns:
        int: 毫秒级时间戳
    """
    print(f"转换日期时间: {date_str}")

    try:
        # 如果是数字，可能是Excel的日期序列号
        if isinstance(date_str, (int, float)) or (
            isinstance(date_str, str) and date_str.isdigit()
        ):
            excel_serial = float(date_str)
            print(f"检测到Excel日期序列号: {excel_serial}")

            # Excel日期序列号转换（Excel的1900年1月1日 = 1）
            # Python datetime的基准是1970年1月1日
            excel_base_date = datetime(1900, 1, 1)
            # Excel有一个已知的bug：认为1900年是闰年，需要减去2天
            excel_serial_corrected = excel_serial - 2
            dt = excel_base_date + pd.Timedelta(days=excel_serial_corrected)

            timestamp = int(dt.timestamp() * 1000)
            print(
                f"Excel序列号转换成功: {excel_serial} -> {dt.strftime('%Y-%m-%d')} -> {timestamp}"
            )
            return timestamp

        # 如果已经是pandas的Timestamp对象
        if isinstance(date_str, pd.Timestamp):
            dt = date_str.to_pydatetime()
            timestamp = int(dt.timestamp() * 1000)
            print(f"Pandas Timestamp转换成功: {date_str} -> {timestamp}")
            return timestamp

        # 尝试多种日期格式的字符串解析
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y.%m.%d",
            "%d.%m.%Y",
        ]
        dt = None

        for fmt in formats:
            try:
                dt = datetime.strptime(str(date_str).strip(), fmt)
                print(f"使用格式 {fmt} 解析成功")
                break
            except ValueError:
                continue

        if dt is None:
            raise ValueError(f"无法解析日期格式: {date_str}")

        timestamp = int(dt.timestamp() * 1000)
        print(f"日期转换成功: {date_str} -> {dt.strftime('%Y-%m-%d')} -> {timestamp}")
        return timestamp

    except Exception as e:
        print(f"日期转换失败详情: 输入={date_str}, 类型={type(date_str)}, 错误={e}")
        raise ValueError(f"日期转换失败: {date_str}, 错误: {e}")


def parse_drive_direction(direction_text: str) -> List[str]:
    """
    解析行车方向，返回需要查询的方向列表

    Args:
        direction_text: 行车方向文本

    Returns:
        List[str]: 方向列表
    """
    print(f"解析行车方向: {direction_text}")

    directions = []

    if "/" in direction_text:
        # 处理 东侧/西侧、南侧/北侧等格式
        parts = direction_text.split("/")
        for part in parts:
            directions.append(part.strip())
    else:
        directions.append(direction_text.strip())

    print(f"行车方向解析结果: {directions}")
    return directions


def query_company_id(company_name: str, company_type_label: str) -> int:
    """
    根据公司名称和类型查询公司ID

    Args:
        company_name: 公司名称
        company_type_label: 公司类型标签

    Returns:
        int: 公司ID
    """
    print(f"查询公司ID: 名称={company_name}, 类型={company_type_label}")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 第一步：查询公司类型value
            sql1 = "SELECT value FROM t_system_dict_data WHERE dict_type = 'company_type' AND label = %s"
            cursor.execute(sql1, (company_type_label,))
            dict_result = cursor.fetchone()

            if not dict_result:
                raise ValueError(f"公司类型不存在: {company_type_label}")

            company_type_value = dict_result["value"]
            print(f"公司类型查询成功: {company_type_label} -> {company_type_value}")

            # 第二步：根据value和name查询公司ID
            sql2 = "SELECT id FROM t_system_dept WHERE name = %s AND company_type = %s"
            cursor.execute(sql2, (company_name, company_type_value))
            dept_result = cursor.fetchone()

            if not dept_result:
                raise ValueError(
                    f"公司不存在: 名称={company_name}, 类型值={company_type_value}"
                )

            company_id = dept_result["id"]
            print(f"公司查询成功: ID={company_id}")
            return company_id

    finally:
        connection.close()


def query_area_id(area_name: str) -> int:
    """
    根据区域名称在area.csv中查询对应的ID

    Args:
        area_name: 区域名称

    Returns:
        int: 区域ID
    """
    print(f"查询区域ID: {area_name}")

    try:
        # 读取area.csv文件
        area_csv_path = pathlib.Path(__file__).parent.parent / "src" / "area.csv"
        if not area_csv_path.exists():
            raise FileNotFoundError(f"area.csv文件不存在: {area_csv_path}")

        df = pd.read_csv(area_csv_path)

        # 查找匹配的记录
        matched_rows = df[df["name"] == area_name]

        if matched_rows.empty:
            raise ValueError(f"区域不存在: {area_name}")

        area_id = int(matched_rows.iloc[0]["id"])
        print(f"区域查询成功: {area_name} -> ID={area_id}")
        return area_id

    except Exception as e:
        raise ValueError(f"区域查询失败: {area_name}, 错误: {e}")


def create_road_level1(road_data: Dict[str, Any]) -> int:
    """
    创建一级道路

    Args:
        road_data: 道路数据字典

    Returns:
        int: 创建成功的道路ID
    """
    print(f"开始创建一级道路: {road_data['name']}")

    url = f"{API_BASE_URL}/create"
    headers = API_HEADERS.copy()
    headers.update(
        {
            "project-id": str(road_data["project_id"]),
            "tenant-id": str(road_data["tenant_id"]),
        }
    )

    payload = {
        "name": road_data["name"],
        "length": road_data["total_length"],
        "ext3": str(road_data["lane_count"]),
        "administerFlag": True,
        "hierarchy": 1,
        "ext1": road_data["road_type"],
    }

    print(f"一级道路请求数据: {json.dumps(payload, ensure_ascii=False)}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"一级道路创建响应: {result}")

        if result.get("code") == 0:
            road_id = result.get("data")
            print(f"一级道路创建成功: ID={road_id}")
            return road_id
        else:
            raise Exception(f"一级道路创建失败: {result.get('msg', '未知错误')}")

    except requests.RequestException as e:
        raise Exception(f"一级道路创建请求失败: {e}")


def create_road_level2(
    road_data: Dict[str, Any], parent_id: int, segment_start: str, segment_end: str
) -> int:
    """
    创建二级道路

    Args:
        road_data: 道路数据字典
        parent_id: 一级道路ID
        segment_start: 起始桩号
        segment_end: 结束桩号

    Returns:
        int: 创建成功的道路ID
    """
    segment_name = f"{segment_start}-{segment_end}"
    print(f"开始创建二级道路: {segment_name}")

    url = f"{API_BASE_URL}/create"
    headers = API_HEADERS.copy()
    headers.update(
        {
            "project-id": str(road_data["project_id"]),
            "tenant-id": str(road_data["tenant_id"]),
        }
    )

    payload = {
        "name": segment_name,
        "parentId": parent_id,
        "length": 100,  # 默认100m
        "administerFlag": True,
        "hierarchy": 2,
        "segmentStartId": segment_start,
        "segmentEndId": segment_end,
        "optStartDate": road_data["maintenance_start"],
        "optEndDate": road_data["maintenance_end"],
        "ext2": road_data["structure_name"],
    }

    # 添加可选的公司字段
    company_fields = road_data.get("company_fields", {})
    if company_fields.get("manager_com_id"):
        payload["managerCom"] = company_fields["manager_com_id"]
    if company_fields.get("owner_com_id"):
        payload["ownerCom"] = company_fields["owner_com_id"]
    if company_fields.get("supervision_com_id"):
        payload["supervisionCom"] = company_fields["supervision_com_id"]
    if company_fields.get("operation_com_id"):
        payload["operationCom"] = company_fields["operation_com_id"]
    if company_fields.get("design_com_id"):
        payload["designCom"] = company_fields["design_com_id"]
    if company_fields.get("construction_com_id"):
        payload["constructionCom"] = company_fields["construction_com_id"]

    # 添加行政辖区字段
    if road_data.get("district_id"):
        payload["district"] = road_data["district_id"]

    print(f"二级道路请求数据: {json.dumps(payload, ensure_ascii=False)}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"二级道路创建响应: {result}")

        if result.get("code") == 0:
            road_id = result.get("data")
            print(f"二级道路创建成功: ID={road_id}")
            return road_id
        else:
            raise Exception(f"二级道路创建失败: {result.get('msg', '未知错误')}")

    except requests.RequestException as e:
        raise Exception(f"二级道路创建请求失败: {e}")


def create_road_level3(
    road_data: Dict[str, Any],
    parent_id: int,
    segment_start: str,
    segment_end: str,
    direction: str,
) -> int:
    """
    创建三级道路

    Args:
        road_data: 道路数据字典
        parent_id: 二级道路ID
        segment_start: 起始桩号
        segment_end: 结束桩号
        direction: 行车方向

    Returns:
        int: 创建成功的道路ID
    """
    segment_name = f"({direction}){segment_start}-{segment_end}"
    print(f"开始创建三级道路: {segment_name}")

    url = f"{API_BASE_URL}/create"
    headers = API_HEADERS.copy()
    headers.update(
        {
            "project-id": str(road_data["project_id"]),
            "tenant-id": str(road_data["tenant_id"]),
        }
    )

    # 三级道路车道数为一级道路的一半
    level3_lane_count = max(1, road_data["lane_count"] // 2)  # type: ignore

    # 道路宽度除以2
    road_width = road_data.get("road_width", 10) / 2

    payload = {
        "name": segment_name,
        "parentId": parent_id,
        "ext3": str(level3_lane_count),
        "administerFlag": True,
        "hierarchy": 3,
        "segmentStartId": segment_start,
        "segmentEndId": segment_end,
        "driveDirection": road_data["drive_direction_values"][direction],
        "width": road_width,
    }

    print(f"三级道路请求数据: {json.dumps(payload, ensure_ascii=False)}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"三级道路创建响应: {result}")

        if result.get("code") == 0:
            road_id = result.get("data")
            print(f"三级道路创建成功: ID={road_id}")
            return road_id
        else:
            raise Exception(f"三级道路创建失败: {result.get('msg', '未知错误')}")

    except requests.RequestException as e:
        raise Exception(f"三级道路创建请求失败: {e}")


def process_excel_row(row: pd.Series, row_index: int) -> Dict[str, Any]:
    """
    处理Excel中的单行数据

    Args:
        row: 数据行
        row_index: 行索引（用于错误提示）

    Returns:
        Dict[str, Any]: 处理后的数据字典
    """
    excel_row_number = row_index + 3  # Excel实际行号
    print(f"\n开始处理第{excel_row_number}行数据")

    try:
        # 1. 查询项目信息
        project_info = query_project_info(row["所属项目"])

        # 2. 转换车道数
        lane_count = convert_lane_count(row["车道数"])

        # 3. 查询道路类型
        road_type = query_dict_value("country_highways_type", row["道路类型"])

        # 4. 解析桩号
        stake_segments, _ = parse_stake_range(row["道路桩号"])
        total_length = float(row["道路长度(km)"])  # 使用用户填写的长度

        # 5. 查询道路结构名称
        structure_name = query_dict_value("structure_name", row["道路结构名称"])

        # 6. 解析行车方向
        direction_labels = parse_drive_direction(row["行车方向"])
        drive_direction_values = {}
        for label in direction_labels:
            value = query_dict_value("drive_direction", label)
            drive_direction_values[label] = value

        # 7. 转换时间
        maintenance_start = convert_datetime_to_timestamp(
            row["养护开始时间(年、月、日)"]
        )
        maintenance_end = convert_datetime_to_timestamp(row["养护结束时间(年、月、日)"])

        processed_data = {
            "project_id": project_info["project_id"],
            "tenant_id": project_info["tenant_id"],
            "name": row["道路名称"],
            "lane_count": lane_count,
            "road_type": road_type,
            "stake_segments": stake_segments,
            "total_length": total_length,
            "structure_name": structure_name,
            "drive_direction_values": drive_direction_values,
            "maintenance_start": maintenance_start,
            "maintenance_end": maintenance_end,
        }

        # 8. 处理可选字段
        # * 道路宽度(m)
        if row.get("道路宽度(m)") and not pd.isna(
            row.get("道路宽度(m)")
        ):  # 存在且不为空
            road_width = float(row.get("道路宽度(m)"))  # type: ignore
            processed_data["road_width"] = road_width

        # * 处理可选的公司字段
        company_fields = {}
        optional_companies = {
            "设计单位": "design_com_id",
            "施工单位": "construction_com_id",
            "管理单位": "manager_com_id",
            "建设单位": "owner_com_id",
            "监理单位": "supervision_com_id",
            "养护单位": "operation_com_id",
        }

        for field_name, key in optional_companies.items():
            if (
                row.get(field_name)
                and not pd.isna(row.get(field_name))
                and str(row.get(field_name)).strip()
            ):
                try:
                    company_id = query_company_id(
                        str(row.get(field_name)).strip(), field_name
                    )
                    company_fields[key] = company_id
                    print(
                        f"{field_name}处理成功: {row.get(field_name)} -> ID={company_id}"
                    )
                except Exception as e:
                    print(f"{field_name}处理失败: {e}")

        processed_data["company_fields"] = company_fields  # type: ignore

        # * 处理行政辖区字段
        district_id = None
        if (
            row.get("行政辖区")
            and not pd.isna(row.get("行政辖区"))
            and str(row.get("行政辖区")).strip()
        ):
            try:
                district_id = query_area_id(str(row.get("行政辖区")).strip())
                print(f"行政辖区处理成功: {row.get('行政辖区')} -> ID={district_id}")
            except Exception as e:
                print(f"行政辖区处理失败: {e}")
        if district_id:
            processed_data["district_id"] = district_id

        # 数据处理完成
        print(f"第{excel_row_number}行数据处理成功，开始创建路网")
        return processed_data

    except Exception as e:
        error_msg = f"第{excel_row_number}行数据处理失败: {e}"
        print(error_msg)
        raise Exception(error_msg)


def create_road_network(processed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建完整的三级路网

    Args:
        processed_data: 处理后的数据字典

    Returns:
        Dict[str, Any]: 创建结果
    """
    print(f"\n开始创建路网: {processed_data['name']}")

    results = {
        "road_name": processed_data["name"],
        "level1_id": None,
        "level2_ids": [],
        "level3_ids": [],
        "errors": [],
    }

    try:
        # 1. 创建或获取一级道路
        road_name = processed_data["name"]

        if road_name in CREATED_LEVEL1_ROADS:
            # 使用已存在的一级道路
            level1_id = CREATED_LEVEL1_ROADS[road_name]
            print(f"使用已存在的一级道路: {road_name} -> ID={level1_id}")
        else:
            # 创建新的一级道路（使用用户填写的总长度）
            level1_id = create_road_level1(processed_data)
            CREATED_LEVEL1_ROADS[road_name] = level1_id
            print(f"创建新一级道路: {road_name} -> ID={level1_id}")

        results["level1_id"] = level1_id

        # 2. 为每个桩号段创建二级和三级道路
        for segment_start, segment_end in processed_data["stake_segments"]:
            try:
                # 创建二级道路
                level2_id = create_road_level2(
                    processed_data, level1_id, segment_start, segment_end
                )
                results["level2_ids"].append(level2_id)

                # 为每个行车方向创建三级道路
                for direction_label in processed_data["drive_direction_values"]:
                    try:
                        level3_id = create_road_level3(
                            processed_data,
                            level2_id,
                            segment_start,
                            segment_end,
                            direction_label,
                        )
                        results["level3_ids"].append(level3_id)

                    except Exception as e:
                        error_msg = f"三级道路创建失败({direction_label}): {e}"
                        print(error_msg)
                        results["errors"].append(error_msg)

            except Exception as e:
                error_msg = f"二级道路创建失败({segment_start}-{segment_end}): {e}"
                print(error_msg)
                results["errors"].append(error_msg)

        print(f"路网创建完成: {processed_data['name']}")
        return results

    except Exception as e:
        error_msg = f"一级道路创建失败: {e}"
        print(error_msg)
        results["errors"].append(error_msg)
        return results


def validate_required_fields(file_input: Union[str, IO]) -> List[str]:
    """
    校验Excel中的必填字段，支持文件路径或文件流对象

    Args:
        file_input: 文件路径（str）或文件对象（file-like, 支持.read()）

    Returns:
        List[str]: 缺失信息提示列表
    """
    # 读取第二行为表头，数据从第三行开始
    df = pd.read_excel(file_input, header=1, parse_dates=True)
    errors = []
    for idx, row in df.iterrows():
        missing = [
            field
            for field in REQUIRED_FIELDS
            if pd.isna(row.get(field)) or str(row.get(field)).strip() == ""
        ]
        if missing:
            excel_row_number = idx + 3  # type: ignore
            errors.append(f"第{excel_row_number}行缺少：{', '.join(missing)}")
    return errors


def process_country_road_import(file_input: Union[str, IO]) -> Dict[str, Any]:
    """
    处理农村公路导入的主函数

    Args:
        file_input: Excel文件路径或文件对象

    Returns:
        Dict[str, Any]: 处理结果
    """
    print("开始处理农村公路数据导入")

    # 清空已创建的一级道路字典
    global CREATED_LEVEL1_ROADS
    CREATED_LEVEL1_ROADS.clear()

    # 1. 验证必填字段
    print("步骤1: 验证必填字段")
    validation_errors = validate_required_fields(file_input)
    if validation_errors:
        return {
            "success": False,
            "message": "数据验证失败",
            "errors": validation_errors,
        }
    print("必填字段验证通过")

    # 2. 读取Excel数据
    print("步骤2: 读取Excel数据")
    df = pd.read_excel(file_input, header=1, parse_dates=True)
    print(f"共读取到 {len(df)} 行数据")

    # 3. 处理每一行数据
    results = {
        "success": True,
        "total_rows": len(df),
        "processed_rows": 0,
        "failed_rows": 0,
        "road_results": [],
        "errors": [],
    }

    for idx, row in df.iterrows():
        try:
            print(f"\n{'=' * 50}")
            print(f"处理第 {idx + 1}/{len(df)} 行数据")  # type: ignore

            # 处理数据
            processed_data = process_excel_row(row, idx)  # type: ignore

            # 创建路网
            road_result = create_road_network(processed_data)
            results["road_results"].append(road_result)

            if road_result["errors"]:
                results["failed_rows"] += 1
                results["errors"].extend(road_result["errors"])
            else:
                results["processed_rows"] += 1

        except Exception as e:
            results["failed_rows"] += 1
            error_msg = f"第{idx + 3}行处理失败: {e}"  # type: ignore
            results["errors"].append(error_msg)
            print(error_msg)

    # 4. 生成最终结果
    if results["failed_rows"] > 0:
        results["success"] = False
        results["message"] = (
            f"部分数据处理失败: 成功{results['processed_rows']}行，失败{results['failed_rows']}行"
        )
    else:
        results["message"] = f"所有数据处理成功: 共{results['processed_rows']}行"

    print(f"\n{'=' * 50}")
    print("农村公路数据导入处理完成")
    print(f"处理结果: {results['message']}")

    return results


# 模板下载接口
@countryRouter.get("/download_template")
async def download_template():
    """模板下载接口

    Returns:
        模板文件
    """
    file_path = (
        pathlib.Path(__file__).parent.parent / "src" / "农村公路导入模板_V1.0.xlsx"
    )
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="模板文件不存在")
    return FileResponse(
        path=file_path,
        filename="农村公路导入模板.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# 数据导入接口
@countryRouter.post("/import_data")
async def import_country_roads(file: UploadFile = File(...)):
    """农村公路数据导入接口

    Args:
        file: 上传的Excel文件

    Returns:
        处理结果
    """
    print(f"接收到文件上传请求: {file.filename}")

    # 验证文件格式
    if not file.filename.endswith((".xlsx", ".xls")):  # type: ignore
        raise HTTPException(
            status_code=400, detail="文件格式错误，请上传Excel文件(.xlsx或.xls)"
        )

    try:
        # 读取文件内容
        file_content = await file.read()
        print(f"文件读取成功，大小: {len(file_content)} bytes")

        # 转化为文件类对象，供 pd.read_excel 使用
        file_stream = BytesIO(file_content)

        # 调用处理函数
        result = process_country_road_import(file_stream)

        # 根据处理结果返回相应的HTTP状态码
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "code": 0,
                    "message": result["message"],
                    "data": {
                        "total_rows": result["total_rows"],
                        "processed_rows": result["processed_rows"],
                        "failed_rows": result["failed_rows"],
                        "road_results": result["road_results"],
                    },
                },
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "code": 1,
                    "message": result["message"],
                    "data": {
                        "total_rows": result["total_rows"],
                        "processed_rows": result["processed_rows"],
                        "failed_rows": result["failed_rows"],
                        "errors": result["errors"][:10],  # 只返回前10个错误信息
                    },
                },
            )

    except Exception as e:
        error_msg = f"文件处理异常: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
