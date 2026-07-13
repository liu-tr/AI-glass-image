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
            "low quality, bad lighting"
        )

    def test_connection(self):
        """测试API连接。失败时抛异常，由上层降级为mock模式。"""
        if self.provider == "pollinations":
            response = requests.get("https://image.pollinations.ai/", timeout=8)
            if response.status_code >= 500:
                raise Exception("Pollinations服务暂不可用")
            return

        response = requests.get(self.api_url.replace('/txt2img', ''), timeout=5)
        if response.status_code != 200:
            raise Exception("API连接失败")

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
        """Stable Diffusion WebUI txt2img，返回base64 data URI列表。"""
        full_prompt = self.positive_template.format(prompt=prompt)

        payload = {
            "prompt": full_prompt,
            "negative_prompt": self.negative_prompt,
            "batch_size": num_images,
            "width": 512,
            "height": 512,
            "seed": -1,
            "steps": 20,
            "cfg_scale": 7
        }

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()

            result = response.json()
            if "images" in result:
                return [f"data:image/png;base64,{img}" for img in result["images"]]
            elif "error" in result:
                raise Exception(result["error"])
            else:
                raise Exception("未知错误")
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {str(e)}")

    def generate_mock(self, prompt, num_images=4):
        """模拟生成图片（当API不可用时使用占位图片）"""
        mock_images = []
        for _ in range(num_images):
            mock_images.append(f"https://picsum.photos/seed/{random.randint(1, 100000)}/512/512")
        return mock_images
