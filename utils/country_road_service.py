import pandas as pd
import requests
import re
import json
from typing import List, Union, IO, Dict, Any, Tuple
from io import BytesIO
from utils.base_data_service import BaseDataService


class CountryRoadService(BaseDataService):
    """农村公路服务类，处理农村公路相关的Excel解析和路网创建"""

    def __init__(self, base_url: str, api_token: str):
        """
        初始化农村公路服务

        Args:
            base_url: API基础URL
            api_token: API认证token
        """
        super().__init__()
        self.base_url = base_url
        self.api_headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "client-type": "1",
        }
        self.created_level1_roads = {}  # 实例级别的字典，格式: {"道路名称": level1_id}

        # 农村公路必填字段
        self.required_fields = [
            "所属项目",
            "道路名称",
            "道路长度(km)",
            "车道数",
            "道路类型",
            "道路桩号",
            "道路结构名称",
            "行车方向",
            "养护开始时间(年、月、日)",
            "养护结束时间(年、月、日)",
        ]

    def parse_stake_range(self, stake_text: str) -> Tuple[List[Tuple[str, str]], float]:
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
            segment_end = min(
                current_m + 100, end_total_m
            )  # 取最小值，防止超出结束桩号

            start_stake = f"K{current_m // 1000}+{current_m % 1000:03d}"  # 一定是三位数
            end_stake = (
                f"K{segment_end // 1000}+{segment_end % 1000:03d}"  # 一定是三位数
            )

            segments.append((start_stake, end_stake))
            current_m = segment_end

        print(f"桩号解析成功: 总长度={total_length_km}km, 分段数={len(segments)}")
        return segments, total_length_km

    def validate_required_fields(self, file_input: Union[str, IO]) -> List[str]:
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
                for field in self.required_fields
                if pd.isna(row.get(field)) or str(row.get(field)).strip() == ""
            ]
            if missing:
                excel_row_number = idx + 3  # type: ignore
                errors.append(f"第{excel_row_number}行缺少：{', '.join(missing)}")
        return errors

    def process_excel_row(self, row: pd.Series, row_index: int) -> Dict[str, Any]:
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
            project_info = self.query_project_info(row["所属项目"])

            # 2. 转换车道数
            lane_count = self.convert_lane_count(row["车道数"])

            # 3. 查询道路类型
            road_type = self.query_dict_value("country_highways_type", row["道路类型"])

            # 4. 解析桩号
            stake_segments, _ = self.parse_stake_range(row["道路桩号"])
            total_length = float(row["道路长度(km)"])  # 使用用户填写的长度

            # 5. 查询道路结构名称
            structure_name = self.query_dict_value(
                "structure_name", row["道路结构名称"]
            )

            # 6. 解析行车方向
            direction_labels = self.parse_drive_direction(row["行车方向"])
            drive_direction_values = {}
            for label in direction_labels:
                value = self.query_dict_value("drive_direction", label)
                drive_direction_values[label] = value

            # 7. 转换时间
            maintenance_start = self.convert_datetime_to_timestamp(
                row["养护开始时间(年、月、日)"]
            )
            maintenance_end = self.convert_datetime_to_timestamp(
                row["养护结束时间(年、月、日)"]
            )

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
                        company_id = self.query_company_id(
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
                    district_id = self.query_area_id(str(row.get("行政辖区")).strip())
                    print(
                        f"行政辖区处理成功: {row.get('行政辖区')} -> ID={district_id}"
                    )
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

    def create_road_level1(self, road_data: Dict[str, Any]) -> int:
        """
        创建一级道路

        Args:
            road_data: 道路数据字典

        Returns:
            int: 创建成功的道路ID
        """
        print(f"开始创建一级道路: {road_data['name']}")

        url = f"{self.base_url}/create"
        headers = self.api_headers.copy()
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
        self,
        road_data: Dict[str, Any],
        parent_id: int,
        segment_start: str,
        segment_end: str,
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

        url = f"{self.base_url}/create"
        headers = self.api_headers.copy()
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
            payload["designerCom"] = company_fields["design_com_id"]
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
        self,
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

        url = f"{self.base_url}/create"
        headers = self.api_headers.copy()
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

    def create_road_network(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
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

            if road_name in self.created_level1_roads:
                # 使用已存在的一级道路
                level1_id = self.created_level1_roads[road_name]
                print(f"使用已存在的一级道路: {road_name} -> ID={level1_id}")
            else:
                # 创建新的一级道路（使用用户填写的总长度）
                level1_id = self.create_road_level1(processed_data)
                self.created_level1_roads[road_name] = level1_id
                print(f"创建新一级道路: {road_name} -> ID={level1_id}")

            results["level1_id"] = level1_id

            # 2. 为每个桩号段创建二级和三级道路
            for segment_start, segment_end in processed_data["stake_segments"]:
                try:
                    # 创建二级道路
                    level2_id = self.create_road_level2(
                        processed_data, level1_id, segment_start, segment_end
                    )
                    results["level2_ids"].append(level2_id)

                    # 为每个行车方向创建三级道路
                    for direction_label in processed_data["drive_direction_values"]:
                        try:
                            level3_id = self.create_road_level3(
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

    def process_country_road_import(self, file_input: Union[str, IO]) -> Dict[str, Any]:
        """
        处理农村公路导入的主函数

        Args:
            file_input: Excel文件路径或文件对象

        Returns:
            Dict[str, Any]: 处理结果
        """
        print("开始处理农村公路数据导入")

        # 清空已创建的一级道路字典
        self.created_level1_roads.clear()

        # 1. 验证必填字段
        print("步骤1: 验证必填字段")
        validation_errors = self.validate_required_fields(file_input)
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
                processed_data = self.process_excel_row(row, idx)  # type: ignore

                # 创建路网
                road_result = self.create_road_network(processed_data)
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
