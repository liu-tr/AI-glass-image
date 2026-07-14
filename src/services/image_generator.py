import requests
import base64


class GlassImageGenerator:
    """玻璃杯文生图 / 图生图生成器。

    仅接入本地 Stable Diffusion WebUI（A1111，需要启动时带 --api）。
    - txt2img: POST /sdapi/v1/txt2img
    - img2img: POST /sdapi/v1/img2img
    """

    def __init__(self, api_url=None, api_key=None):
        self.api_url = api_url
        self.api_key = api_key

        # 玻璃行业专用提示词
        self.positive_template = (
            "{prompt}, glass cup, transparent glass, elegant design, smooth surface, "
            "professional product photography, studio lighting, white background, "
            "high quality, 8k resolution, photorealistic, clear glass texture"
        )
        self.negative_prompt = (
            "deformed, broken, cracked, uneven thickness, distorted, blurry, watermark, "
            "text, logo, ugly, unrealistic, cartoon style, anime, drawing, sketch, "
            "indoor, room, scene, person, character, 2d, illustration, painting, "
            "low quality, bad lighting"
        )

    def test_connection(self):
        """测试SD WebUI连接。用 /sdapi/v1/options 探活（仅在 --api 启动时存在）。
        若返回 404，说明用户没在 webui-user.bat 加 --api 参数。
        """
        base = self.api_url.split("/sdapi/v1/")[0]
        try:
            response = requests.get(f"{base}/sdapi/v1/options", timeout=5)
        except requests.exceptions.RequestException as e:
            raise Exception(f"无法连接 SD WebUI ({base}): {e}")
        if response.status_code == 404:
            raise Exception(
                "SD WebUI 启用了页面但未开启 API。请在 webui-user.bat 的 "
                "set COMMANDLINE_ARGS= 末尾加上 --api 后重启"
            )
        if response.status_code != 200:
            raise Exception(f"SD WebUI 探活失败，HTTP {response.status_code}")

    def generate(self, prompt, num_images=4):
        """文生图（txt2img）。返回base64 data URI列表。"""
        return self._generate_sd(prompt, num_images)

    def generate_img2img(self, init_image_b64, prompt, denoising_strength=0.55, num_images=4):
        """图生图（img2img）。

        init_image_b64: base64 编码的起始图（不带 data:image/png;base64, 前缀）
        denoising_strength: 0.0~1.0，越高越偏离原图
        """
        return self._generate_img2img(init_image_b64, prompt, denoising_strength, num_images)

    def _post_sd(self, endpoint, payload):
        """统一的 SD WebUI POST 助手。"""
        url = self.api_url.replace("/txt2img", endpoint)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            # 本地 GPU 推理 4 张约 10~30s，给足超时
            response = requests.post(url, json=payload, headers=headers, timeout=180)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise Exception("SD WebUI 生成超时（>180s）。请检查 GPU 是否在跑、模型是否过大")
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求 SD WebUI 失败: {e}")

        try:
            result = response.json()
        except ValueError:
            raise Exception(f"SD WebUI 返回非 JSON: {response.text[:200]}")

        if "images" in result and result["images"]:
            return [f"data:image/png;base64,{img}" for img in result["images"]]
        if "error" in result:
            raise Exception(f"SD WebUI 报错: {result['error']}")
        raise Exception("SD WebUI 返回为空")

    def _generate_sd(self, prompt, num_images=4):
        """Stable Diffusion WebUI txt2img。"""
        full_prompt = self.positive_template.format(prompt=prompt)
        payload = {
            "prompt": full_prompt,
            "negative_prompt": self.negative_prompt,
            "batch_size": num_images,
            "width": 512,
            "height": 512,
            "seed": -1,                 # -1 = 随机
            "steps": 25,                # SD1.5 出图 20~30 比较稳定
            "cfg_scale": 11,
            "sampler_name": "Euler a",  # 整合包预置，秋葉默认推荐
            "restore_faces": False,
            "enable_hr": False,
        }
        return self._post_sd("/txt2img", payload)

    def _generate_img2img(self, init_image_b64, prompt, denoising_strength=0.55, num_images=4):
        """Stable Diffusion WebUI img2img。

        init_image_b64: base64 编码的起始图（不带 data:image/png;base64, 前缀）
        denoising_strength: 0.0~1.0，越高越偏离原图
        """
        full_prompt = self.positive_template.format(prompt=prompt)
        payload = {
            "init_images": [init_image_b64],
            "prompt": full_prompt,
            "negative_prompt": self.negative_prompt,
            "denoising_strength": max(0.0, min(1.0, denoising_strength)),
            "batch_size": num_images,
            "width": 512,
            "height": 512,
            "seed": -1,
            "steps": 25,
            "cfg_scale": 11,
            "sampler_name": "Euler a",
            "restore_faces": False,
        }
        return self._post_sd("/img2img", payload)
