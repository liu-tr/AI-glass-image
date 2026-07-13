"""输入合规校验：检测用户 prompt 中的工业负面词并返回拒绝原因。

设计目的
--------
- 课题要求"配置玻璃行业专用正负向提示词，规避畸形生成"。
- 命中工业负面词的 prompt 几乎必然触发 Pollinations 内容过滤，
  4 张图大概率混入 picsum 占位图，污染设计结果。
- 在生成前直接拒绝并返回"无法生成图片"提示图，链路更清晰可解释。
"""


INDUSTRY_NEGATIVE_TERMS = {
    # 英文（玻璃行业最常见负面描述）
    "deformed", "broken", "crack", "cracked", "dirty", "ugly",
    "worst quality", "smashed", "shattered", "damaged",
    # 中文（覆盖中文 prompt 的单字 + 词组）
    "变形", "破损", "裂纹", "裂痕", "碎裂", "破碎", "粉碎", "断裂",
    "脏", "脏污", "肮脏", "污", "丑", "丑陋", "最差",
    "碎片", "损伤", "损坏", "坏", "破",
}


def find_blocked_term(prompt: str):
    """在 prompt 中查找第一个命中的工业负面词（小写匹配）。未命中返回 None。"""
    if not prompt:
        return None
    p = prompt.lower()
    for term in INDUSTRY_NEGATIVE_TERMS:
        if term in p:
            return term
    return None


def is_input_blocked(prompt: str) -> bool:
    return find_blocked_term(prompt) is not None


def build_rejection_image(reason: str, blocked_term: str) -> str:
    """生成一张 512×512 的 SVG 提示图，返回 data URI。

    SVG 内联到 data URI 中，无新增依赖；与正常图走同一通道，
    前端/数据库/优化逻辑零修改。
    """
    reason_zh = {
        "deformed":       "形态变形（deformed）",
        "broken":         "破损（broken）",
        "cracked":        "开裂（cracked）",
        "dirty":          "脏污（dirty）",
        "ugly":           "外观丑化（ugly）",
        "worst quality":  "质量反转（worst quality）",
        "smashed":        "粉碎（smashed）",
        "shattered":      "碎片（shattered）",
        "damaged":        "损伤（damaged）",
    }.get(blocked_term, f"工业敏感词（{blocked_term}）")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fafbfc"/>
      <stop offset="100%" stop-color="#eef0f3"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" fill="url(#bg)"/>
  <g transform="translate(256 220)">
    <circle r="64" fill="none" stroke="#c9cdd4" stroke-width="6"/>
    <text x="0" y="22" text-anchor="middle" font-family="Microsoft YaHei, sans-serif"
          font-size="80" fill="#8a919e">⚠</text>
  </g>
  <text x="256" y="360" text-anchor="middle" font-family="Microsoft YaHei, sans-serif"
        font-size="34" font-weight="600" fill="#8a919e">无法生成</text>
  <text x="256" y="408" text-anchor="middle" font-family="Microsoft YaHei, sans-serif"
        font-size="18" fill="#8a919e">原因：{reason_zh}</text>
  <text x="256" y="450" text-anchor="middle" font-family="Microsoft YaHei, sans-serif"
        font-size="14" fill="#a3a9b3">请描述风格 / 颜色 / 杯型 / 场景，避免破损、脏污等词</text>
</svg>'''
    import base64
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"
