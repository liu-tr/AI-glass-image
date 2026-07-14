import requests
import random
import urllib.parse
import base64
import time


class GlassImageGenerator:
    """玻璃杯文生图生成器。

    provider:
      - "pollinations": 使用 Pollinations.AI，免注册、免 API key，直接返回图片 URL（当前默认）。
      - "sd_webui":     使用本地 / 远程 Stable Diffusion WebUI 的 txt2img 接口。
    以后接入通义万相 / 硅基流动等带 key 的服务时，新增一个分支即可，app.py 只需改初始化参数。
    """

    POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"

    def __init__(self, provider="pollinations", api_url=None, api_key=None):
        self.provider = provider
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
        """测试API连接。失败时抛异常，由上层降级为mock模式。"""
        if self.provider == "pollinations":
            response = requests.get("https://image.pollinations.ai/", timeout=8)
            if response.status_code >= 500:
                raise Exception("Pollinations服务暂不可用")
            return

        # SD WebUI：用 /sdapi/v1/options 探活（仅在 --api 启动时存在）
        # 若返回 404，说明用户没在 webui-user.bat 加 --api 参数
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
        """调用文生图API生成图片，返回图片URL或data URI列表。"""
        if self.provider == "pollinations":
            return self._generate_pollinations(prompt, num_images)
        return self._generate_sd(prompt, num_images)

    def _generate_pollinations(self, prompt, num_images=4):
        """Pollinations：串行抓取 + 4 张 prompt 视角变体。

        反复实测后结论：Pollinations 免费档对同 IP 的实际并发上限约 1。
        任何"分批并发"都会让快的那张被限流拖到 ~130s 等慢的那张，反而更慢。
        串行节奏下单张 2~10s，4 张 ≈ 8~45s，且 4/4 真出图。

        4 张 prompt 末尾分别加 --view front/side/top/three-quarter 微扰，
        避免 Pollinations 把 4 个相同 prompt（仅 seed 不同）判为重复。
        """
        full_prompt_base = self.positive_template.format(prompt=prompt)

        view_suffixes = [
            " --view front",
            " --view side",
            " --view top",
            " --view three-quarter",
        ][:num_images]

        images = []
        for i in range(num_images):
            seed = random.randint(1, 1_000_000)
            encoded = urllib.parse.quote(full_prompt_base + view_suffixes[i], safe='')
            url = (f"{self.POLLINATIONS_BASE}{encoded}"
                   f"?width=512&height=512&nologo=true&seed={seed}&model=turbo")
            images.append(self._fetch_as_data_uri(url))
        return images

    def _fetch_as_data_uri(self, url, retries=1):
        """抓取图片字节转data URI。串行阶段重试 1 次避免 ORB 破图；兜底为占位图。"""
        for attempt in range(retries + 1):
            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                content_type = resp.headers.get('Content-Type', '')
                if content_type.startswith('image/') and resp.content:
                    b64 = base64.b64encode(resp.content).decode('ascii')
                    return f"data:{content_type};base64,{b64}"
            except requests.exceptions.RequestException:
                pass
            if attempt < retries:
                time.sleep(2)
        return f"https://picsum.photos/seed/{random.randint(1, 100000)}/512/512"

    def _generate_sd(self, prompt, num_images=4):
        """Stable Diffusion WebUI txt2img，返回base64 data URI列表。

        适配 B 站秋葉整合包（A1111 WebUI），默认地址 http://127.0.0.1:7860。
        启动时需要在 webui-user.bat 加 --api（整合包默认已带）。
        """
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

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            # 本地 GPU 推理 4 张约 10~30s，给足超时
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=180)
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

    def generate_mock(self, prompt, num_images=4):
        """模拟生成图片（当API不可用时使用占位图片）"""
        mock_images = []
        for _ in range(num_images):
            mock_images.append(f"https://picsum.photos/seed/{random.randint(1, 100000)}/512/512")
        return mock_images
