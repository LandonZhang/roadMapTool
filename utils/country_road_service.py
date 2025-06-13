import pandas as pd
import requests
import re
import json
from typing import List, Union, IO, Dict, Any, Tuple
from io import BytesIO
from pathlib import Path
from utils.base_data_service import BaseDataService
from utils.road_track_service import BaiduMercatorRoadTrackGenerator


class CountryRoadService(BaseDataService):
    """农村公路服务类，处理农村公路相关的Excel解析和路网创建"""

    def __init__(self, base_url: str, api_token: str, baidu_ak: str):
        """
        初始化农村公路服务

        Args:
            base_url: API基础URL
            api_token: API认证token
            baidu_ak: 百度地图API密钥
        """
        super().__init__()
        self.base_url = base_url
        self.api_headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "client-type": "1",
        }
        self.created_level1_roads = {}  # 实例级别的字典，格式: {"道路名称": level1_id}

        # 初始化轨迹生成器
        self.track_generator = BaiduMercatorRoadTrackGenerator(baidu_ak=baidu_ak)

        # 加载方向映射配置
        self.load_direction_config()

        # 农村公路必填字段 - 更新字段列表
        self.required_fields = [
            "所属项目",
            "道路名称",
            "道路长度(km)",
            "道路宽度(m)",
            "车道数",
            "道路类型",
            "道路起点桩号",
            "道路终点桩号",
            "里程桩间隔(m)",
            "道路结构名称",
            "行车方向",
            "养护开始时间(年、月、日)",
            "养护结束时间(年、月、日)",
            "道路起点桩号位置",
            "道路终点桩号位置",
            "道路轨迹坐标",
        ]

    def load_direction_config(self):
        """加载方向映射配置文件"""
        try:
            config_path = (
                Path(__file__).parent.parent / "assets" / "direction_mapping.json"
            )
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.direction_mapping = config["direction_mapping"]
            print(f"方向映射配置加载成功: {len(self.direction_mapping)}个方向")
        except Exception as e:
            print(f"方向映射配置加载失败: {e}")
            # 提供默认配置
            self.direction_mapping = {
                "东侧": "right_track",
                "西侧": "left_track",
                "南侧": "right_track",
                "北侧": "left_track",
                "内圈": "right_track",
                "外圈": "left_track",
                "上行": "left_track",
                "下行": "right_track",
            }

    # 获取分段轨迹坐标
    def get_segment_coordinates(
        self, track_result: dict, direction_label: str, segment_index: int
    ) -> dict:
        """
        根据方向标签和分段索引获取对应的轨迹坐标

        Args:
            track_result: 轨迹生成结果
            direction_label: 方向标签（如"东侧"、"上行"等）
            segment_index: 分段索引

        Returns:
            dict: 包含start_coordinate, end_coordinate, length的分段信息
        """
        # 根据方向标签获取轨迹类型
        track_type = self.direction_mapping.get(direction_label)
        if not track_type:
            raise ValueError(f"未知的方向标签: {direction_label}")

        print(f"方向标签 '{direction_label}' 映射到轨迹类型: {track_type}")

        # 获取对应的分段数据
        if track_type == "left_track":
            segments = track_result.get("left_segments", [])
        else:
            segments = track_result.get("right_segments", [])

        if segment_index >= len(segments):
            raise ValueError(f"分段索引超出范围: {segment_index} >= {len(segments)}")

        segment_info = segments[segment_index]
        print(
            f"获取第{segment_index}个{track_type}分段，长度: {segment_info['length']:.2f}米"
        )

        return segment_info

    # 坐标转GeoJSON，用于接口传参
    def coordinates_to_geojson(
        self, start_coord: tuple, end_coord: tuple, length_meters: float
    ) -> str:
        """
        将坐标转换为GeoJSON格式字符串

        Args:
            start_coord: 起点坐标 (lng, lat)
            end_coord: 终点坐标 (lng, lat)
            length_meters: 路段长度（米）

        Returns:
            str: GeoJSON格式字符串
        """
        # 构建坐标数组，格式: [[lng, lat], [lng, lat]]
        coordinates = [[start_coord[0], start_coord[1]], [end_coord[0], end_coord[1]]]

        # 构建GeoJSON对象
        geojson = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                    "length": length_meters / 1000.0,  # 转换为公里
                },
            }
        ]

        # 转换为JSON字符串
        geojson_str = json.dumps(geojson, ensure_ascii=False)
        print(f"生成GeoJSON: 长度={length_meters:.2f}米, 坐标数={len(coordinates)}")

        return geojson_str

    def parse_stake_range(
        self, start_stake: str, end_stake: str, interval: int
    ) -> Tuple[List[Tuple[str, str]], float]:
        """
        解析桩号范围，返回按指定间隔分段的桩号列表和总长度

        Args:
            start_stake: 起点桩号（如：K0+000）
            end_stake: 终点桩号（如：K1+280）
            interval: 里程桩间隔（米）

        Returns:
            Tuple[List[Tuple[str, str]], float]: (桩号分段列表, 总长度km)
        """
        print(f"解析桩号范围: 起点={start_stake}, 终点={end_stake}, 间隔={interval}米")

        # 解析起点桩号 - 只支持K+格式
        start_pattern = r"K(\d+)\+(\d+)"
        start_match = re.match(start_pattern, start_stake.strip())
        if not start_match:
            raise ValueError(f"无效的起点桩号格式: {start_stake}，请使用K0+000格式")

        start_km, start_m = map(int, start_match.groups())
        start_total_m = start_km * 1000 + start_m
        print(f"起点桩号解析: {start_stake} -> {start_total_m}米")

        # 解析终点桩号 - 只支持K+格式
        end_pattern = r"K(\d+)\+(\d+)"
        end_match = re.match(end_pattern, end_stake.strip())
        if not end_match:
            raise ValueError(f"无效的终点桩号格式: {end_stake}，请使用K0+000格式")

        end_km, end_m = map(int, end_match.groups())
        end_total_m = end_km * 1000 + end_m
        print(f"终点桩号解析: {end_stake} -> {end_total_m}米")

        # 验证桩号范围
        if end_total_m <= start_total_m:
            raise ValueError(f"终点桩号({end_stake})必须大于起点桩号({start_stake})")

        # 计算总长度（km）
        total_length_km = (end_total_m - start_total_m) / 1000.0
        print(f"道路总长度: {total_length_km}km")

        # 验证间隔合理性
        if interval <= 0:
            raise ValueError(f"里程桩间隔必须大于0，当前值: {interval}")

        if interval > (end_total_m - start_total_m):
            raise ValueError(
                f"里程桩间隔({interval}米)不能大于道路总长度({end_total_m - start_total_m}米)"
            )

        # 按指定间隔分段生成桩号列表
        segments = []
        current_m = start_total_m

        while current_m < end_total_m:
            segment_end = min(
                current_m + interval, end_total_m
            )  # 取最小值，防止超出结束桩号

            segment_start_stake = f"K{current_m // 1000}+{current_m % 1000:03d}"
            segment_end_stake = f"K{segment_end // 1000}+{segment_end % 1000:03d}"

            segments.append((segment_start_stake, segment_end_stake))
            print(f"生成桩号段: {segment_start_stake} -> {segment_end_stake}")

            current_m = segment_end

        print(
            f"桩号解析成功: 总长度={total_length_km}km, 分段数={len(segments)}, 间隔={interval}米"
        )
        return segments, total_length_km

    def validate_required_fields(self, file_input: Union[str, IO]) -> List[str]:
        """
        校验Excel中的必填字段，支持文件路径或文件流对象

        Args:
            file_input: 文件路径（str）或文件对象（file-like, 支持.read()）

        Returns:
            List[str]: 缺失信息提示列表
        """
        print("开始验证Excel必填字段")

        # 读取第二行为表头，数据从第三行开始
        df = pd.read_excel(file_input, header=1, parse_dates=True)
        print(f"读取到Excel数据，共{len(df)}行")

        errors = []
        for idx, row in df.iterrows():
            excel_row_number = idx + 3  # type: ignore # Excel实际行号
            missing = []

            for field in self.required_fields:
                field_value = row.get(field)
                if pd.isna(field_value) or str(field_value).strip() == "":
                    missing.append(field)

            if missing:
                error_msg = f"第{excel_row_number}行缺少：{', '.join(missing)}"
                errors.append(error_msg)
                print(f"验证失败: {error_msg}")

        if not errors:
            print("所有必填字段验证通过")
        else:
            print(f"发现{len(errors)}个验证错误")

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
            project_name = str(row["所属项目"]).strip()
            print(f"查询项目信息: {project_name}")
            project_info = self.query_project_info(project_name)

            # 2. 转换车道数
            lane_text = str(row["车道数"]).strip()
            print(f"转换车道数: {lane_text}")
            lane_count = self.convert_lane_count(lane_text)

            # 3. 查询道路类型
            road_type_label = str(row["道路类型"]).strip()
            print(f"查询道路类型: {road_type_label}")
            road_type = self.query_dict_value("country_highways_type", road_type_label)

            # 4. 解析桩号 - 修改为读取三个字段
            start_stake = str(row["道路起点桩号"]).strip()
            end_stake = str(row["道路终点桩号"]).strip()
            interval = int(row["里程桩间隔(m)"])  # 转换为整数

            print(
                f"解析桩号信息: 起点={start_stake}, 终点={end_stake}, 间隔={interval}"
            )
            stake_segments, calculated_length = self.parse_stake_range(
                start_stake, end_stake, interval
            )

            # 使用用户填写的长度，但进行合理性检查
            user_length = float(row["道路长度(km)"])
            length_diff = abs(calculated_length - user_length)
            if length_diff > 0.1:  # 允许0.1km的误差
                print(
                    f"警告: 用户填写长度({user_length}km)与计算长度({calculated_length}km)差异较大"
                )

            total_length = user_length  # 使用用户填写的长度

            # 5. 查询道路结构名称
            structure_label = str(row["道路结构名称"]).strip()
            print(f"查询道路结构: {structure_label}")
            structure_name = self.query_dict_value("structure_name", structure_label)

            # 6. 解析行车方向
            direction_text = str(row["行车方向"]).strip()
            print(f"解析行车方向: {direction_text}")
            direction_labels = self.parse_drive_direction(direction_text)
            drive_direction_values = {}
            for label in direction_labels:
                value = self.query_dict_value("drive_direction", label)
                drive_direction_values[label] = value
                print(f"行车方向映射: {label} -> {value}")

            # 7. 转换时间
            maintenance_start_raw = row["养护开始时间(年、月、日)"]
            maintenance_end_raw = row["养护结束时间(年、月、日)"]
            print(
                f"转换养护时间: 开始={maintenance_start_raw}, 结束={maintenance_end_raw}"
            )

            maintenance_start = self.convert_datetime_to_timestamp(
                maintenance_start_raw
            )
            maintenance_end = self.convert_datetime_to_timestamp(maintenance_end_raw)

            # 构建处理后的数据
            processed_data = {
                "project_id": project_info["project_id"],
                "tenant_id": project_info["tenant_id"],
                "name": str(row["道路名称"]).strip(),
                "lane_count": lane_count,
                "road_type": road_type,
                "stake_segments": stake_segments,
                "total_length": total_length,
                "structure_name": structure_name,
                "drive_direction_values": drive_direction_values,
                "maintenance_start": maintenance_start,
                "maintenance_end": maintenance_end,
                "interval": interval,  # 保存间隔信息用于日志
            }

            # 道路宽度(m)
            road_width = float(row.get("道路宽度(m)"))  # type: ignore
            processed_data["road_width"] = road_width
            print(f"道路宽度: {road_width}米")

            # 读取并解析轨迹坐标
            center_coordinates_raw = row["道路轨迹坐标"]
            if isinstance(center_coordinates_raw, str):
                # 如果是字符串，需要解析
                center_coordinates = eval(center_coordinates_raw)
            else:
                center_coordinates = center_coordinates_raw

            print(f"道路中心线坐标点数: {len(center_coordinates)}")

            # 生成左右轨迹线和分段标点
            try:
                track_result = self.track_generator.generate_parallel_tracks(
                    bd09_coordinates=center_coordinates,
                    road_width=road_width,
                    create_markers=True,
                    marker_interval=interval,  # 使用用户配置的间隔
                )
                print(
                    f"轨迹生成成功: 左分段={len(track_result.get('left_segments', []))}个, "
                    f"右分段={len(track_result.get('right_segments', []))}个"
                )
            except Exception as e:
                raise Exception(f"轨迹生成失败: {e}")

            # 添加分段结果
            processed_data["track_result"] = track_result

            # 9. 处理可选字段
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
                        company_name = str(row.get(field_name)).strip()
                        company_id = self.query_company_id(company_name, field_name)
                        company_fields[key] = company_id
                        print(
                            f"{field_name}处理成功: {company_name} -> ID={company_id}"
                        )
                    except Exception as e:
                        print(f"{field_name}处理失败: {e}")

            processed_data["company_fields"] = company_fields

            # * 处理行政辖区字段
            district_id = None
            if (
                row.get("行政辖区")
                and not pd.isna(row.get("行政辖区"))
                and str(row.get("行政辖区")).strip()
            ):
                try:
                    district_name = str(row.get("行政辖区")).strip()
                    district_id = self.query_area_id(district_name)
                    print(f"行政辖区处理成功: {district_name} -> ID={district_id}")
                except Exception as e:
                    print(f"行政辖区处理失败: {e}")

            if district_id:
                processed_data["district_id"] = district_id

            # 数据处理完成
            print(f"第{excel_row_number}行数据处理成功，准备创建路网")
            print(f"- 道路名称: {processed_data['name']}")
            print(f"- 桩号分段数: {len(stake_segments)}")
            print(f"- 行车方向数: {len(drive_direction_values)}")

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

        # 计算当前段的长度（使用配置的间隔）
        segment_length = road_data.get(
            "interval", 100
        )  # 默认100m，但应该使用配置的间隔

        payload = {
            "name": segment_name,
            "parentId": parent_id,
            "length": segment_length,
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
        segment_index: int,  # 新增参数：分段索引
    ) -> int:
        """
        创建三级道路

        Args:
            road_data: 道路数据字典
            parent_id: 二级道路ID
            segment_start: 起始桩号
            segment_end: 结束桩号
            direction: 行车方向
            segment_index: 分段索引，用于获取对应的轨迹坐标

        Returns:
            int: 创建成功的道路ID
        """
        segment_name = f"({direction}){segment_start}-{segment_end}"
        print(f"开始创建三级道路: {segment_name}, 分段索引: {segment_index}")

        url = f"{self.base_url}/create"
        headers = self.api_headers.copy()
        headers.update(
            {
                "project-id": str(road_data["project_id"]),
                "tenant-id": str(road_data["tenant_id"]),
            }
        )

        # 三级道路车道数为一级道路的一半
        level3_lane_count = max(1, road_data["lane_count"] // 2)

        # 道路宽度除以2
        road_width = road_data.get("road_width", 10.0) / 2

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

        # 添加GeoJSON字段
        try:
            # 获取当前分段的轨迹坐标
            segment_coords = self.get_segment_coordinates(
                road_data["track_result"], direction, segment_index
            )

            # 生成GeoJSON
            geojson_str = self.coordinates_to_geojson(
                segment_coords["start_coordinate"],
                segment_coords["end_coordinate"],
                segment_coords["length"],  # 使用road_track_service计算的实际长度
            )

            payload["geojson"] = geojson_str
            print(f"已添加GeoJSON字段到三级道路")

        except Exception as e:
            print(f"GeoJSON生成失败，将跳过此字段: {e}")

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
                # 创建新的一级道路
                level1_id = self.create_road_level1(processed_data)
                self.created_level1_roads[road_name] = level1_id
                print(f"创建新一级道路: {road_name} -> ID={level1_id}")

            results["level1_id"] = level1_id

            # 2. 为每个桩号段创建二级和三级道路
            total_segments = len(processed_data["stake_segments"])
            print(f"需要创建{total_segments}个二级道路段")

            # 使用序列解包获得起始桩号和结束桩号
            for segment_idx, (segment_start, segment_end) in enumerate(
                processed_data["stake_segments"], 1
            ):
                print(
                    f"\n处理第{segment_idx}/{total_segments}个桩号段: {segment_start} -> {segment_end}"
                )

                try:
                    # 创建二级道路
                    level2_id = self.create_road_level2(
                        processed_data, level1_id, segment_start, segment_end
                    )
                    results["level2_ids"].append(level2_id)

                    # 为每个行车方向创建三级道路
                    direction_count = len(processed_data["drive_direction_values"])
                    print(f"为当前段创建{direction_count}个行车方向的三级道路")

                    for idx, direction_label in enumerate(
                        processed_data["drive_direction_values"]
                    ):
                        try:
                            # 第一个方向标签使用原始顺序，第二个方向标签反转起点终点
                            if idx == 0:
                                start_stake = segment_start
                                end_stake = segment_end
                            else:
                                start_stake = segment_end
                                end_stake = segment_start

                            level3_id = self.create_road_level3(
                                processed_data,
                                level2_id,
                                start_stake,
                                end_stake,
                                direction_label,
                                segment_idx - 1,  # 使用分段索引，从0开始
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
            print(f"- 一级道路: 1个")
            print(f"- 二级道路: {len(results['level2_ids'])}个")
            print(f"- 三级道路: {len(results['level3_ids'])}个")
            print(f"- 错误数量: {len(results['errors'])}个")

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
                "total_rows": 0,
                "processed_rows": 0,
                "failed_rows": 0,
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
