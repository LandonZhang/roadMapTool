import pathlib
import pymysql
import os
import dotenv
import pandas as pd
from datetime import datetime
from typing import Dict, Any

# 加载数据库连接信息
dotenv.load_dotenv(".env")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
CHARSET = os.getenv("CHARSET")


class BaseDataService:
    """基础数据服务类，提供通用的数据库查询和数据转换功能"""

    def __init__(self):
        """初始化基础数据服务"""
        pass

    def get_db_connection(self):
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

    def query_project_info(self, project_name: str) -> Dict[str, Any]:
        """
        根据项目名称查询项目ID和租户ID

        Args:
            project_name: 项目名称

        Returns:
            Dict[str, Any]: 包含project_id和tenant_id的字典
        """
        print(f"查询项目信息: {project_name}")

        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT id, tenant_id FROM t_system_project WHERE name = %s"
                cursor.execute(sql, (project_name,))
                result = cursor.fetchone()

                if not result:
                    raise ValueError(f"项目 '{project_name}' 不存在")

                print(
                    f"项目查询成功: ID={result['id']}, tenant_id={result['tenant_id']}"
                )
                return {"project_id": result["id"], "tenant_id": result["tenant_id"]}
        finally:
            connection.close()

    def query_dict_value(self, dict_type: str, label: str) -> str:
        """
        根据字典类型和标签查询对应的值

        Args:
            dict_type: 字典类型
            label: 标签

        Returns:
            str: 对应的值
        """
        print(f"查询字典值: dict_type={dict_type}, label={label}")

        connection = self.get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT value FROM t_system_dict_data WHERE dict_type = %s AND label = %s"
                cursor.execute(sql, (dict_type, label))
                result = cursor.fetchone()

                if not result:
                    raise ValueError(
                        f"字典值不存在: dict_type={dict_type}, label={label}"
                    )

                print(f"字典查询成功: value={result['value']}")
                return result["value"]
        finally:
            connection.close()

    def query_company_id(self, company_name: str, company_type_label: str) -> int:
        """
        根据公司名称和类型查询公司ID

        Args:
            company_name: 公司名称
            company_type_label: 公司类型标签

        Returns:
            int: 公司ID
        """
        print(f"查询公司ID: 名称={company_name}, 类型={company_type_label}")

        connection = self.get_db_connection()
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
                sql2 = (
                    "SELECT id FROM t_system_dept WHERE name = %s AND company_type = %s"
                )
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

    def query_area_id(self, area_name: str) -> int:
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

    def convert_lane_count(self, lane_text: str) -> int:
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

    def convert_datetime_to_timestamp(self, date_str: str) -> int:
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
            print(
                f"日期转换成功: {date_str} -> {dt.strftime('%Y-%m-%d')} -> {timestamp}"
            )
            return timestamp

        except Exception as e:
            print(f"日期转换失败详情: 输入={date_str}, 类型={type(date_str)}, 错误={e}")
            raise ValueError(f"日期转换失败: {date_str}, 错误: {e}")

    def parse_drive_direction(self, direction_text: str) -> list[str]:
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
