"""玻璃杯图像特征提取器。

功能：
  1. 从 base64 图片中提取玻璃杯轮廓和几何特征
  2. 计算轮廓复杂度 C（0~1），用于 MOPSO 动态调整目标函数系数
  3. 提取几何特征（高宽比、对称度、边缘密度等）

实现说明：
  - 仅依赖 Pillow + numpy，无需 OpenCV
  - 输入：base64 编码的 PNG/JPEG 图片
  - 输出：特征字典
"""

import base64
import io
import numpy as np
from PIL import Image


class FeatureExtractor:
    """玻璃杯图像特征提取器。"""

    @staticmethod
    def decode_b64(image_b64: str) -> np.ndarray:
        """将 base64 data URI 或裸 base64 解码为 numpy 灰度数组 (H, W)。"""
        # 去除 "data:image/...;base64," 前缀
        if image_b64.startswith("data:"):
            _, b64_data = image_b64.split(",", 1)
        else:
            b64_data = image_b64
        raw = base64.b64decode(b64_data)
        img = Image.open(io.BytesIO(raw)).convert("L")  # 灰度图
        return np.array(img, dtype=np.float32)

    @staticmethod
    def _gaussian_blur(arr: np.ndarray, kernel_size: int = 5, sigma: float = 1.0) -> np.ndarray:
        """简单高斯模糊（避免引入外部依赖）。"""
        k = kernel_size
        ax = np.arange(-k // 2 + 1, k // 2 + 1)
        gauss = np.exp(-0.5 * (ax / sigma) ** 2)
        gauss /= gauss.sum()
        # 先水平再垂直（分离式卷积）
        blurred = np.apply_along_axis(lambda x: np.convolve(x, gauss, mode="same"), axis=1, arr=arr)
        blurred = np.apply_along_axis(lambda x: np.convolve(x, gauss, mode="same"), axis=0, arr=blurred)
        return blurred

    @staticmethod
    def _sobel_edges(gray: np.ndarray) -> np.ndarray:
        """Sobel 边缘检测，返回边缘强度图 (H, W)。"""
        # Sobel X / Y 核
        Kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
        Ky = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
        h, w = gray.shape
        Gx = np.zeros_like(gray)
        Gy = np.zeros_like(gray)
        # 手动卷积（避免 scipy.ndimage 依赖）
        padded = np.pad(gray, ((1, 1), (1, 1)), mode="constant")
        for i in range(h):
            for j in range(w):
                patch = padded[i:i + 3, j:j + 3]
                Gx[i, j] = np.sum(patch * Kx)
                Gy[i, j] = np.sum(patch * Ky)
        return np.sqrt(Gx ** 2 + Gy ** 2)

    @staticmethod
    def _non_max_suppression(mag: np.ndarray, angle: np.ndarray) -> np.ndarray:
        """非极大值抑制，细化边缘到单像素。"""
        h, w = mag.shape
        nms = np.zeros_like(mag)
        angle = np.deg2rad(angle)
        for i in range(1, h - 1):
            for j in range(1, w - 1):
                # 梯度方向
                theta = angle[i, j]
                if (-np.pi / 8 <= theta < np.pi / 8) or (7 * np.pi / 8 <= theta or theta < -7 * np.pi / 8):
                    p1, p2 = mag[i, j - 1], mag[i, j + 1]
                elif (np.pi / 8 <= theta < 3 * np.pi / 8) or (-7 * np.pi / 8 <= theta < -5 * np.pi / 8):
                    p1, p2 = mag[i - 1, j - 1], mag[i + 1, j + 1]
                elif (3 * np.pi / 8 <= theta < 5 * np.pi / 8) or (-5 * np.pi / 8 <= theta < -3 * np.pi / 8):
                    p1, p2 = mag[i - 1, j], mag[i + 1, j]
                else:
                    p1, p2 = mag[i - 1, j + 1], mag[i + 1, j - 1]
                if mag[i, j] >= p1 and mag[i, j] >= p2:
                    nms[i, j] = mag[i, j]
        return nms

    @staticmethod
    def _double_threshold(nms: np.ndarray, low: float, high: float) -> np.ndarray:
        """双阈值法，用高阈值确定强边缘，低阈值连接弱边缘。"""
        h, w = nms.shape
        strong = 255
        weak = 75
        result = np.zeros_like(nms, dtype=np.uint8)
        si, sj = np.where(nms >= high)
        wi, wj = np.where((nms >= low) & (nms < high))
        result[si, sj] = strong
        result[wi, wj] = weak
        # 通过连通性将弱边缘连接到强边缘
        for i in range(1, h - 1):
            for j in range(1, w - 1):
                if result[i, j] == weak:
                    if np.any(result[i - 1:i + 2, j - 1:j + 2] == strong):
                        result[i, j] = strong
                    else:
                        result[i, j] = 0
        return (result > 0).astype(np.float32)

    def canny(self, gray: np.ndarray, low_thresh: float = 30, high_thresh: float = 90) -> np.ndarray:
        """完整 Canny 边缘检测，返回二值边缘图 (H, W)。"""
        # 1. 高斯模糊降噪
        blurred = self._gaussian_blur(gray)
        # 2. Sobel 梯度
        sobel_x = self._sobel_edges(blurred)
        # 重新计算带方向的 Sobel
        Kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
        Ky = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
        h, w = blurred.shape
        padded = np.pad(blurred, ((1, 1), (1, 1)), mode="constant")
        Gx = np.zeros_like(blurred)
        Gy = np.zeros_like(blurred)
        for i in range(h):
            for j in range(w):
                patch = padded[i:i + 3, j:j + 3]
                Gx[i, j] = np.sum(patch * Kx)
                Gy[i, j] = np.sum(patch * Ky)
        mag = np.sqrt(Gx ** 2 + Gy ** 2)
        angle = np.rad2deg(np.arctan2(Gy, Gx + 1e-8))
        # 3. NMS
        nms = self._non_max_suppression(mag, angle)
        # 4. 双阈值
        return self._double_threshold(nms, low_thresh, high_thresh)

    def extract(self, image_b64: str, return_edge_map: bool = False) -> dict:
        """从玻璃杯图片提取特征。

        Args:
            image_b64: base64 编码的图片（可以带 data: URI 前缀）
            return_edge_map: 是否在返回结果中附带边缘图（调试用途）

        Returns:
            dict: {
                "complexity": float,      # 轮廓复杂度 0~1
                "height_ratio": float,    # 高度占图片比例 0~1
                "width_ratio": float,     # 宽度占图片比例 0~1
                "aspect_ratio": float,    # 高宽比（>1 瘦高，<1 矮胖）
                "symmetry": float,        # 左右对称度 0~1
                "edge_density": float,    # 边缘像素密度 0~1
                "contour_variation": float # 轮廓变化率 0~1（复杂度辅助指标）
            }
            如果 return_edge_map=True，额外包含 "edge_map": np.ndarray
        """
        gray = self.decode_b64(image_b64)
        h, w = gray.shape

        # ---------- 步骤 1：杯体分割 ----------
        # 玻璃杯在白背景上通常比背景暗，取 <200 为杯体区域
        # 先用 Otsu 风格的自动阈值：取灰度中值作为分割参考
        bg_sample = gray[:, :20]  # 假设左上角为背景
        bg_mean = np.mean(bg_sample)
        # 背景偏亮则阈值取 bg_mean - 30，偏暗则用固定 128
        threshold = max(80, bg_mean - 30) if bg_mean > 128 else 128
        mask = (gray < threshold).astype(np.float32)

        # 形态学去噪：去掉小孤立点（简单中值滤波）
        mask = self._median_filter(mask, kernel_size=3)
        # 取最大连通区域（主杯体）
        mask = self._largest_blob(mask)

        # ---------- 步骤 2：边缘检测 ----------
        edges = self.canny(gray, low_thresh=20, high_thresh=60)
        # 只取 mask 范围内的边缘（去除背景噪声）
        foreground_edges = edges * mask

        # ---------- 步骤 3：轮廓提取 ----------
        # 从边缘图中提取杯体轮廓点
        ys, xs = np.where(foreground_edges > 0)
        if len(xs) < 10:  # 边缘点太少，说明分割或检测失败
            return self._fallback_features(h, w)

        # ---------- 步骤 4：边界框 ----------
        y_min, y_max = int(ys.min()), int(ys.max())
        x_min, x_max = int(xs.min()), int(xs.max())
        cup_h = y_max - y_min + 1
        cup_w = x_max - x_min + 1

        # ---------- 步骤 5：计算特征 ----------

        # 5a. 高宽比
        aspect_ratio = cup_h / max(cup_w, 1)
        height_ratio = cup_h / h
        width_ratio = cup_w / w

        # 5b. 边缘密度
        edge_density = float(np.sum(foreground_edges) / max(np.sum(mask), 1))

        # 5c. 对称度：取杯体区域左右两半的像素分布差异
        center_x = (x_min + x_max) / 2
        left = mask[y_min:y_max + 1, x_min:int(center_x) + 1]
        right = mask[y_min:y_max + 1, int(center_x):x_max + 1]
        # 将右半部分左右翻转
        right_flipped = np.fliplr(right)
        # 对齐尺寸
        min_cols = min(left.shape[1], right_flipped.shape[1])
        if min_cols > 0:
            left_aligned = left[:, :min_cols]
            right_aligned = right_flipped[:, :min_cols]
            diff = np.abs(left_aligned - right_aligned)
            symmetry = 1.0 - float(np.mean(diff))
        else:
            symmetry = 0.5

        # 5d. 轮廓复杂度
        # 取杯体左右两侧的轮廓（y 方向每行最左和最右的 x 坐标）
        left_profile = []
        right_profile = []
        for y in range(y_min, y_max + 1):
            row = mask[y, x_min:x_max + 1]
            edge_pixels = np.where(row > 0)[0]
            if len(edge_pixels) > 1:
                left_profile.append(edge_pixels[0] + x_min)
                right_profile.append(edge_pixels[-1] + x_min)
            elif len(edge_pixels) == 1:
                left_profile.append(edge_pixels[0] + x_min)
                right_profile.append(edge_pixels[0] + x_min)

        if len(left_profile) > 5:
            # 计算轮廓变化率：相邻行之间轮廓位置的差异标准差
            left_var = float(np.std(np.diff(left_profile))) if len(left_profile) > 1 else 0
            right_var = float(np.std(np.diff(right_profile))) if len(right_profile) > 1 else 0
            # 归一化到 0~1（用杯宽归一化）
            nom = max(cup_w, 1)
            contour_var_left = min(left_var / nom * 10, 1.0)   # 乘系数放大
            contour_var_right = min(right_var / nom * 10, 1.0)  # 差异
            contour_variation = (contour_var_left + contour_var_right) / 2
        else:
            contour_variation = 0.5

        # 5e. 综合复杂度
        # 由多个指标加权：
        #   - contour_variation 占 50%（轮廓越曲折 -> 越复杂）
        #   - 1 - symmetry 占 20%（越不对称 -> 越复杂）
        #   - edge_density 占 30%（边缘细节越多 -> 越复杂）
        complexity = (
            0.50 * contour_variation +
            0.20 * (1.0 - symmetry) +
            0.30 * min(edge_density * 3, 1.0)
        )
        # 确保 0~1 范围
        complexity = max(0.0, min(1.0, complexity))

        result = {
            "complexity": round(complexity, 4),
            "height_ratio": round(height_ratio, 4),
            "width_ratio": round(width_ratio, 4),
            "aspect_ratio": round(aspect_ratio, 4),
            "symmetry": round(symmetry, 4),
            "edge_density": round(edge_density, 4),
            "contour_variation": round(contour_variation, 4),
        }

        if return_edge_map:
            result["edge_map"] = foreground_edges

        return result

    # ---- 辅助方法 ----

    @staticmethod
    def _median_filter(arr: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """中值滤波去噪。"""
        from scipy.ndimage import median_filter as mf
        try:
            return mf(arr, size=kernel_size)
        except ImportError:
            # fallback：简单实现
            h, w = arr.shape
            k = kernel_size // 2
            result = arr.copy()
            for i in range(k, h - k):
                for j in range(k, w - k):
                    result[i, j] = np.median(arr[i - k:i + k + 1, j - k:j + k + 1])
            return result

    @staticmethod
    def _largest_blob(mask: np.ndarray) -> np.ndarray:
        """取 mask 中最大的连通区域（主杯体），去掉噪点。"""
        from scipy.ndimage import label as nd_label
        try:
            labeled, num = nd_label(mask)
            if num == 0:
                return mask
            sizes = np.bincount(labeled.ravel())
            # 排除背景（label=0）
            largest_label = np.argmax(sizes[1:]) + 1
            return (labeled == largest_label).astype(np.float32)
        except ImportError:
            return mask  # 无 scipy 时直接返回原 mask

    @staticmethod
    def _fallback_features(h: int, w: int) -> dict:
        """特征提取失败时的默认返回值。"""
        return {
            "complexity": 0.5,
            "height_ratio": 0.5,
            "width_ratio": 0.3,
            "aspect_ratio": 1.0,
            "symmetry": 0.7,
            "edge_density": 0.1,
            "contour_variation": 0.3,
        }
