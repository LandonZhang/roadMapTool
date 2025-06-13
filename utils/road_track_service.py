import requests
from typing import List, Tuple, Dict, Any, Union
from shapely.geometry import LineString
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaiduMercatorRoadTrackGenerator:
    """基于百度墨卡托坐标系的道路轨迹线生成器

    使用BD-09MC(百度墨卡托米制坐标)进行几何计算，减少坐标转换步骤，提升精度
    转换流程：BD-09 → BD-09MC → 几何计算 → BD-09MC → BD-09
    """

    def __init__(self, baidu_ak: str):
        """
        初始化道路轨迹线生成器

        Args:
            baidu_ak (str): 百度地图API的AK密钥
        """
        self.baidu_ak = baidu_ak
        self.baidu_api_base = "https://api.map.baidu.com/geoconv/v1/"

        logger.info("百度墨卡托道路轨迹线生成器初始化完成")

    def normalize_coordinates(
        self, coordinates: Union[List[Tuple[float, float]], List[List[float]]]
    ) -> List[Tuple[float, float]]:
        """
        标准化坐标格式，将各种输入格式转换为元组列表

        Args:
            coordinates: 坐标数据，支持 [(x,y),...] 或 [[x,y],...]

        Returns:
            List[Tuple[float, float]]: 标准化的元组列表格式
        """
        if not coordinates:
            raise ValueError("坐标列表不能为空")

        # 检查第一个元素的类型来判断格式
        first_item = coordinates[0]

        if isinstance(first_item, (list, tuple)) and len(first_item) == 2:
            # 转换为元组列表格式
            normalized = [(float(coord[0]), float(coord[1])) for coord in coordinates]
            logger.info(
                f"坐标格式标准化完成: {type(first_item).__name__} -> tuple, 共{len(normalized)}个点"
            )
            return normalized
        else:
            raise ValueError(
                f"无效的坐标格式: {type(first_item)}, 期望格式: [(x,y),...] 或 [[x,y],...]"
            )

    def bd09_to_bd09mc(
        self, coordinates: Union[List[Tuple[float, float]], List[List[float]]]
    ) -> List[Tuple[float, float]]:
        """
        使用百度API将BD-09坐标转换为BD-09MC坐标（墨卡托米制）

        Args:
            coordinates: BD-09坐标列表 [(lng, lat), ...]

        Returns:
            BD-09MC坐标列表 [(x, y), ...] 单位：米
        """
        # 将输入的坐标列表转换为元组列表格式
        coordinates = self.normalize_coordinates(coordinates)
        logger.info(f"开始BD-09转BD-09MC坐标转换，共{len(coordinates)}个点")

        # 百度API一次最多处理100个坐标点
        batch_size = 100
        result_coords = []

        for i in range(0, len(coordinates), batch_size):
            batch = coordinates[i : i + batch_size]

            # 构造坐标字符串
            coords_str = ";".join([f"{lng},{lat}" for lng, lat in batch])

            params = {
                "coords": coords_str,
                "from": "5",  # BD-09经纬度坐标
                "to": "6",  # BD-09墨卡托米制坐标
                "ak": self.baidu_ak,
                "output": "json",
            }

            try:
                response = requests.get(self.baidu_api_base, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()

                if data.get("status") == 0:
                    for point in data.get("result", []):
                        result_coords.append((point["x"], point["y"]))
                else:
                    raise Exception(f"百度API错误: {data.get('message', '未知错误')}")

                # 避免API调用过频
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"BD-09转BD-09MC失败: {e}")
                raise

        logger.info(f"BD-09转BD-09MC转换完成，转换了{len(result_coords)}个点")
        return result_coords

    def bd09mc_to_bd09(
        self, coordinates: Union[List[Tuple[float, float]], List[List[float]]]
    ) -> List[Tuple[float, float]]:
        """
        使用百度API将BD-09MC坐标转换为BD-09坐标

        Args:
            coordinates: BD-09MC坐标列表 [(x, y), ...] 单位：米

        Returns:
            BD-09坐标列表 [(lng, lat), ...]
        """
        coordinates = self.normalize_coordinates(coordinates)
        logger.info(f"开始BD-09MC转BD-09坐标转换，共{len(coordinates)}个点")

        # 百度API一次最多处理100个坐标点
        batch_size = 100
        result_coords = []

        for i in range(0, len(coordinates), batch_size):
            batch = coordinates[i : i + batch_size]

            # 构造坐标字符串（使用序列解包）
            coords_str = ";".join([f"{x},{y}" for x, y in batch])

            params = {
                "coords": coords_str,
                "from": "6",  # BD-09墨卡托米制坐标
                "to": "5",  # BD-09经纬度坐标
                "ak": self.baidu_ak,
                "output": "json",
            }

            try:
                response = requests.get(self.baidu_api_base, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()

                if data.get("status") == 0:
                    for point in data.get("result", []):
                        result_coords.append((point["x"], point["y"]))
                else:
                    raise Exception(f"百度API错误: {data.get('message', '未知错误')}")

                # 避免API调用过频
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"BD-09MC转BD-09失败: {e}")
                raise

        logger.info(f"BD-09MC转BD-09转换完成，转换了{len(result_coords)}个点")

        return result_coords

    def convert_segments_to_bd09(
        self, segments_mc: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """将路段的MC坐标转换为BD-09坐标"""

        # 提取所有起点和终点的MC坐标
        all_mc_coords = []
        for segment in segments_mc:
            all_mc_coords.append(segment["start_coordinate"])
            all_mc_coords.append(segment["end_coordinate"])

        # 批量转换为BD-09坐标
        all_bd09_coords = self.bd09mc_to_bd09(all_mc_coords)

        # 重新组装路段信息
        segments_bd09 = []
        for i, segment in enumerate(segments_mc):
            # 每个路段有两个点，所以需要乘以2来越过前一个道路
            start_idx = i * 2
            end_idx = i * 2 + 1

            segment_bd09 = {
                "start_coordinate": all_bd09_coords[start_idx],  # BD-09起点
                "end_coordinate": all_bd09_coords[end_idx],  # BD-09终点
                "length": segment["length"],  # 路段长度（米）
                "start_distance": segment["start_distance"],  # 距总起点距离
                "end_distance": segment["end_distance"],  # 距总起点距离
            }
            segments_bd09.append(segment_bd09)

        return segments_bd09

    def create_road_segments_along_track(
        self, mc_coordinates: List[Tuple[float, float]], interval_meters: float = 100
    ) -> List[Dict[str, Any]]:
        """
        沿轨迹线按间隔创建路段信息
        每个路段包含：起点、终点、长度

        Args:
            mc_coordinates: BD-09MC坐标列表
            interval_meters: 路段间隔（米）

        Returns:
            路段信息列表，每个路段包含起点、终点坐标和长度
        """
        logger.info(f"开始沿轨迹线创建路段，间隔: {interval_meters}米")

        line = LineString(mc_coordinates)
        total_length = line.length
        logger.info(f"轨迹线总长度: {total_length:.2f}米")

        segments = []
        distance = 0

        while distance < total_length:
            # 计算当前路段的起点和终点距离
            start_distance = distance
            end_distance = min(distance + interval_meters, total_length)

            # 获取起点和终点坐标
            start_point = line.interpolate(start_distance)
            end_point = line.interpolate(end_distance)

            # 计算实际路段长度
            actual_length = end_distance - start_distance

            # 创建路段信息
            segment = {
                "start_coordinate": (start_point.x, start_point.y),  # 起点MC坐标
                "end_coordinate": (end_point.x, end_point.y),  # 终点MC坐标
                "length": actual_length,  # 路段长度（米）
                "start_distance": start_distance,  # 距总起点距离
                "end_distance": end_distance,  # 距总起点距离
            }

            segments.append(segment)
            distance += interval_meters

        logger.info(f"创建了 {len(segments)} 个路段")
        return segments

    def create_offset_line(
        self,
        mc_coordinates: List[Tuple[float, float]],
        offset_distance: float,
        side: str,
    ) -> List[Tuple[float, float]]:
        """
        在BD-09MC坐标系下创建偏移线（米制坐标系，直接适用）

        Args:
            mc_coordinates: BD-09MC坐标列表 [(x, y), ...] 单位：米
            offset_distance: 偏移距离（米）
            side: 偏移方向 ('left' 或 'right')

        Returns:
            偏移后的BD-09MC坐标列表 [(x, y), ...] 单位：米
        """
        logger.info(f"开始创建{side}侧偏移线，偏移距离: {offset_distance}米")

        try:
            # 创建LineString对象
            line = LineString(mc_coordinates)

            # 创建平行偏移线
            # 在墨卡托坐标系中，单位已经是米，可以直接使用offset_distance
            offset_line = line.parallel_offset(
                offset_distance,
                side,
                resolution=16,
                join_style="round",
            )

            # 处理可能的MultiLineString结果
            if offset_line.geom_type == "LineString":
                offset_coords = list(offset_line.coords)
            elif offset_line.geom_type == "MultiLineString":
                # 如果结果是MultiLineString，取最长的那一段
                longest_line = max(offset_line.geoms, key=lambda x: x.length)  # type: ignore
                offset_coords = list(longest_line.coords)
            elif offset_line.geom_type == "Point":
                # 如果道路太短，可能会退化为点
                logger.warning("偏移线退化为点，可能是道路太短")
                offset_coords = [offset_line.coords[0], offset_line.coords[0]]
            else:
                raise Exception(f"意外的几何类型: {offset_line.geom_type}")

            logger.info(f"{side}侧偏移线创建完成，共{len(offset_coords)}个点")
            return offset_coords

        except Exception as e:
            logger.error(f"创建偏移线失败: {e}")
            raise

    def generate_parallel_tracks(
        self,
        bd09_coordinates: Union[List[Tuple[float, float]], List[List[float]]],
        road_width: float,
        create_markers: bool = False,
        marker_interval: float = 100.0,
    ) -> Dict[str, List[Tuple[float, float]]]:
        """
        生成道路的左右轨迹线（使用百度墨卡托坐标系）

        Args:
            bd09_coordinates: 道路中心线的BD-09坐标列表 [(lng, lat), ...]
            road_width: 道路宽度（米）

        Returns:
            包含左右轨迹线坐标的字典:
            {
                'center_line': [(lng, lat), ...],  # 中心线BD-09坐标
                'left_track': [(lng, lat), ...],   # 左轨迹线BD-09坐标
                'right_track': [(lng, lat), ...]   # 右轨迹线BD-09坐标
            }
        """
        bd09_coordinates = self.normalize_coordinates(bd09_coordinates)
        logger.info(
            f"开始生成道路轨迹线，中心线点数: {len(bd09_coordinates)}, 道路宽度: {road_width}米"
        )

        # 验证输入参数
        if len(bd09_coordinates) < 2:
            raise ValueError("至少需要2个坐标点才能构成道路中心线")

        if road_width <= 0:
            raise ValueError("道路宽度必须大于0")

        try:
            # 步骤1: BD-09 → BD-09MC (使用百度API)
            logger.info("步骤1: BD-09坐标转换为BD-09MC墨卡托坐标")
            mc_coords = self.bd09_to_bd09mc(bd09_coordinates)

            # 步骤2: 在BD-09MC坐标系下创建左右偏移线
            logger.info("步骤2: 在墨卡托坐标系中创建左右偏移线")
            offset_distance = road_width / 2.0

            left_mc_coords = self.create_offset_line(mc_coords, offset_distance, "left")
            right_mc_coords = self.create_offset_line(
                mc_coords, offset_distance, "right"
            )

            # 步骤2.5: 每隔 marker_interval 创造一个标点
            if create_markers:
                logger.info(f"步骤2.5: 创建标点，间隔{marker_interval}米")
                left_markers_mc = self.create_road_segments_along_track(
                    left_mc_coords, marker_interval
                )
                right_markers_mc = self.create_road_segments_along_track(
                    right_mc_coords, marker_interval
                )

            # 步骤3: BD-09MC → BD-09 (使用百度API)
            logger.info("步骤3: BD-09MC墨卡托坐标转换为BD-09坐标")
            left_bd09_coords = self.bd09mc_to_bd09(left_mc_coords)
            right_bd09_coords = self.bd09mc_to_bd09(right_mc_coords)

            result = {
                "center_line": bd09_coordinates,
                "left_track": left_bd09_coords,
                "right_track": right_bd09_coords,
            }

            # 添加标点到结果中（如果创建了）
            if create_markers:
                left_segments_bd09 = self.convert_segments_to_bd09(left_markers_mc)  # type: ignore
                right_segments_bd09 = self.convert_segments_to_bd09(right_markers_mc)  # type: ignore

                result["left_segments"] = left_segments_bd09  # type: ignore
                result["right_segments"] = right_segments_bd09  # type: ignore

                logger.info(f"左轨迹标点数: {len(left_segments_bd09)}")
                logger.info(f"右轨迹标点数: {len(right_segments_bd09)}")

                logger.info("道路轨迹线生成完成")
                logger.info(f"左轨迹线点数: {len(result['left_track'])}")
                logger.info(f"右轨迹线点数: {len(result['right_track'])}")

            return result

        except Exception as e:
            logger.error(f"生成道路轨迹线失败: {e}")
            raise

    def validate_coordinates(
        self, coordinates: Union[List[Tuple[float, float]], List[List[float]]]
    ) -> bool:
        """
        验证坐标的有效性

        Args:
            coordinates: 坐标列表 [(lng, lat), ...]

        Returns:
            bool: 坐标是否有效
        """
        coordinates = self.normalize_coordinates(coordinates)
        for lng, lat in coordinates:
            # 检查经纬度范围（BD-09坐标系的大致范围）
            if not (-180 <= lng <= 180) or not (-90 <= lat <= 90):
                logger.warning(f"坐标超出有效范围: ({lng}, {lat})")
                return False

        return True


def main():
    """示例测试函数"""
    # 使用您的百度地图AK
    BAIDU_AK = "xjbkCycMo4IPSBeZoT8cShecVazZ33Iq"
    CREATE_MARKERS = False

    # 创建优化的道路轨迹线生成器实例
    generator = BaiduMercatorRoadTrackGenerator(baidu_ak=BAIDU_AK)

    # test_center_line = [
    #     (121.355267, 31.161052),
    #     (121.357351, 31.162087),
    #     (121.357702, 31.162195),
    #     (121.360693, 31.162578),
    # ]

    # test_road_width = 28.9548

    test_center_line = [
        [103.93815560196539, 30.59308015442757],
        [103.94047249559775, 30.59441859058116],
        [103.94047249559775, 30.59441859058116],
    ]

    test_road_width = 12.88

    try:
        # 验证输入坐标
        if not generator.validate_coordinates(test_center_line):
            print("输入坐标验证失败")
            return

        # 生成左右轨迹线
        print("开始生成道路轨迹线...")
        result = generator.generate_parallel_tracks(
            test_center_line,
            test_road_width,
            create_markers=CREATE_MARKERS,
            marker_interval=100,
        )

        # 打印结果
        print("=" * 50)
        print("道路轨迹线生成结果")
        print("=" * 50)

        print(f"\n中心线坐标 (BD-09):")
        center_line_str = ";".join(
            [f"{lng:.6f},{lat:.6f}" for lng, lat in result["center_line"]]
        )
        print(center_line_str)

        print(f"\n左轨迹线坐标 (BD-09):")
        left_track_str = ";".join(
            [f"{lng:.6f},{lat:.6f}" for lng, lat in result["left_track"]]
        )
        print(left_track_str)

        print(f"\n右轨迹线坐标 (BD-09):")
        right_track_str = ";".join(
            [f"{lng:.6f},{lat:.6f}" for lng, lat in result["right_track"]]
        )
        print(right_track_str)

        if CREATE_MARKERS:
            print(f"\n左轨迹路段标点坐标 (BD-09):")

            left_points = []
            # 添加所有路段的起点
            for segment in result["left_segments"]:
                start = segment["start_coordinate"]  # type: ignore
                left_points.append(f"{start[0]:.6f},{start[1]:.6f}")

            # 添加最后一个路段的终点
            if result["left_segments"]:
                last_segment = result["left_segments"][-1]
                end = last_segment["end_coordinate"]  # type: ignore
                left_points.append(f"{end[0]:.6f},{end[1]:.6f}")

            left_points_str = ";".join(left_points)
            print(left_points_str)

            print(f"\n右轨迹路段标点坐标 (BD-09):")
            right_points = []
            # 添加所有路段的起点
            for segment in result["right_segments"]:
                start = segment["start_coordinate"]  # type: ignore
                right_points.append(f"{start[0]:.6f},{start[1]:.6f}")

            # 添加最后一个路段的终点
            if result["right_segments"]:
                last_segment = result["right_segments"][-1]
                end = last_segment["end_coordinate"]  # type: ignore
                right_points.append(f"{end[0]:.6f},{end[1]:.6f}")

            right_points_str = ";".join(right_points)
            print(right_points_str)

            print("\n" + "=" * 50)
            print("处理完成！您可以将上述坐标复制到HTML页面中进行可视化验证")
            print("=" * 50)

    except Exception as e:
        print(f"处理失败: {e}")


if __name__ == "__main__":
    main()
