import requests
import base64
import re
import logging

logger = logging.getLogger(__name__)


class GlassImageGenerator:
    """玻璃杯文生图 / 图生图生成器。

    仅接入本地 Stable Diffusion WebUI（A1111，需要启动时带 --api）。
    - txt2img: POST /sdapi/v1/txt2img
    - img2img: POST /sdapi/v1/img2img
    自动将中文 prompt 翻译为英文（提升 SD 生成效果）。
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

    # ── 中文→英文自动翻译 ──────────────────────────────────────
    _CHINESE_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')

    def _has_chinese(self, text):
        """检测是否包含中文字符。"""
        return bool(self._CHINESE_RE.search(text))

    def _translate_to_english(self, text):
        """将中文文本翻译为英文。翻译失败时返回原文。"""
        if not self._has_chinese(text):
            return text
        try:
            import translators as ts
            result = ts.translate_text(text, translator='bing', from_language='auto', to_language='en')
            if result and result.strip():
                logger.info('中文→英文翻译: "%s" → "%s"', text, result.strip())
                return result.strip()
        except Exception:
            try:
                import translators as ts
                result = ts.translate_text(text, translator='google', from_language='auto', to_language='en')
                if result and result.strip():
                    logger.info('中文→英文翻译(google): "%s" → "%s"', text, result.strip())
                    return result.strip()
            except Exception:
                pass
        logger.warning('中文翻译失败，保留原文: "%s"', text)
        return text

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

    def list_loras(self):
        """从 SD WebUI 获取当前可用的 LoRA 模型列表。

        返回格式：[{"name": "glasscup_lora", "filename": "glasscup_lora.safetensors"}, ...]
        若 SD WebUI 未连接或 API 不支持，返回空列表。
        """
        base = self.api_url.split("/sdapi/v1/")[0]
        try:
            resp = requests.get(f"{base}/sdapi/v1/loras", timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except requests.exceptions.RequestException:
            pass
        return []

    def refresh_loras(self):
        """通知 SD WebUI 重新扫描 LoRA 目录，让新放进去的 .safetensors 生效。

        返回 True 表示刷新请求已发送（无论成功与否都不影响后续使用）。
        """
        base = self.api_url.split("/sdapi/v1/")[0]
        try:
            requests.post(f"{base}/sdapi/v1/refresh-loras", timeout=10)
        except requests.exceptions.RequestException:
            pass
        return True

    def generate(self, prompt, num_images=4, lora_weight=0, sampler_name="Euler a", lora_model="glasscup_lora"):
        """文生图（txt2img）。返回base64 data URI列表。

        lora_model: LoRA 模型名（不含 .safetensors），默认 glasscup_lora
        自动将中文 prompt 翻译为英文。
        """
        prompt = self._translate_to_english(prompt)
        return self._generate_sd(prompt, num_images, lora_weight=lora_weight, sampler_name=sampler_name, lora_model=lora_model)

    def generate_img2img(self, init_image_b64, prompt, denoising_strength=0.55, num_images=4, lora_weight=0, sampler_name="Euler a", lora_model="glasscup_lora"):
        """图生图（img2img）。

        init_image_b64: base64 编码的起始图（不带 data:image/png;base64, 前缀）
        denoising_strength: 0.0~1.0，越高越偏离原图
        lora_model: LoRA 模型名（不含 .safetensors），默认 glasscup_lora
        自动将中文 prompt 翻译为英文。
        """
        prompt = self._translate_to_english(prompt)
        return self._generate_img2img(init_image_b64, prompt, denoising_strength, num_images, lora_weight=lora_weight, sampler_name=sampler_name, lora_model=lora_model)

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

    def _generate_sd(self, prompt, num_images=4, lora_weight=0, sampler_name="Euler a", lora_model="glasscup_lora"):
        """Stable Diffusion WebUI txt2img。"""
        if lora_weight > 0:
            prompt = f"glasscup {prompt} <lora:{lora_model}:{lora_weight:.2f}>"
        full_prompt = self.positive_template.format(prompt=prompt)
        payload = {
            "prompt": full_prompt,
            "negative_prompt": self.negative_prompt,
            "batch_size": num_images,
            "width": 512,
            "height": 512,
            "seed": -1,
            "steps": 25,
            "cfg_scale": 11,
            "sampler_name": sampler_name,
            "restore_faces": False,
            "enable_hr": False,
        }
        return self._post_sd("/txt2img", payload)

    def _generate_img2img(self, init_image_b64, prompt, denoising_strength=0.55, num_images=4, lora_weight=0, sampler_name="Euler a", lora_model="glasscup_lora"):
        """Stable Diffusion WebUI img2img。"""
        if lora_weight > 0:
            prompt = f"glasscup {prompt} <lora:{lora_model}:{lora_weight:.2f}>"
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
            "sampler_name": sampler_name,
            "restore_faces": False,
        }
        return self._post_sd("/img2img", payload)
