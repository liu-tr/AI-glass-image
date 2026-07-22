"""心理语义提示词库 — 中文心理语义 / 杯型 → SD 英文描述映射。

数据来源：d:\trae\import random.txt
功能：
  1. 存储四维心理语义到 SD 英文外观描述的映射（SEMANTIC_MAP）
  2. 存储中文杯型名称到 SD 英文描述的映射（CUP_DICT）
  3. 支持用户输入中检测心理语义词并替换为对应描述
  4. 支持中文杯型名称精确/模糊匹配转译
  5. 提供翻译预览功能
"""

import re
import random

# ===================== 四维心理语义【中文key → 英文画面描述】 =====================
SEMANTIC_MAP = {
    "简约": "simple composition, centered object, plain solid background, no extra decorations, low visual density, ",
    "复杂": "multi-layer structure, rich textures, abundant details, stacked elements, complex scene layout, ",
    "柔和": "smooth curved lines, soft natural side light, soft shadow, low contrast, warm tone, rounded silhouette, ",
    "硬朗": "sharp straight edges, hard side lighting, harsh shadow, high contrast, cool geometric feeling, clear cutting light, ",
    "轻量": "thin glass wall, slender cup body, slender base, lightweight visual sense, transparent and airy, ",
    "重量": "thick glass wall, heavy thick base, solid volume sense, stable visual gravity, massive shape, ",
    "扩张": "wide opening, outward stretched outline, open shape, horizontally extended form, ",
    "收敛": "narrow rim, inward gathered outline, compact vertical shape, inward contracted lines, "
}

# ===================== 中文杯型词典【中文名称 → SD 英文描述】 =====================
CUP_DICT = {
    "直筒玻璃杯": "straight transparent glass tumbler",
    "带把手玻璃杯": "clear glass mug with curved side handle",
    "马克杯": "clear glass mug with curved side handle",
    "马天尼杯": "martini glass, tall stemmed cocktail glass, transparent crystal glass, triangular bowl, slender stem, round base",
    "古典威士忌杯": "thick bottom old fashioned whiskey glass, short transparent tumbler, heavy solid glass base",
    "香槟高脚杯": "tall champagne flute, slender stem, narrow tall bowl, transparent crystal glass",
    "红酒高脚杯": "wine goblet, tall slender thin stem, elongated tapered oval bowl, round flat crystal base, transparent glossy glass",
    "高脚杯": "transparent goblet glass cup, slender stem, round base, transparent crystal glass, smooth glossy surface, delicate glass refraction",
    "小烈酒杯": "small shot glass, short thick transparent glass cup, heavy solid base, cylindrical shape",
    "外扩腰型玻璃杯": "flared waist clear glass tumbler, curved outward rim, thick glass base",
    "海波直身杯": "tall straight highball glass, long cylindrical transparent glass cup",
    "沙漏型茶杯": "hourglass shaped tea glass, curved narrow waist, thick round base",
    "双层隔热玻璃杯": "double wall insulated clear glass cup, two-layer transparent borosilicate glass, hollow middle layer",
    "印花直筒玻璃杯": "transparent straight glass tumbler, mint green irregular color block print, delicate gold line botanical leaf pattern, thin gold trim on print edges",
    "金边直筒玻璃杯": "tall straight clear glass tumbler, thin delicate gold gilded rim, thick solid glass base",
    "浮雕花卉直筒杯": "tall transparent glass tumbler, deep etched embossed floral leaf cut crystal pattern, 3D relief flower carvings",
    "圆点几何浮雕古典杯": "short old fashioned glass, embossed dotted bubble band on upper body, diamond star geometric relief carving",
    "八角直筒玻璃杯": "octagonal transparent glass tumbler, multi-faceted angular straight walls, thick solid octagonal glass base",
    "星钻浮雕威士忌杯": "short crystal whiskey glass, deep cut starburst diamond embossed relief carvings, multi-faceted crystal texture",
    "大星型刻花玻璃杯": "tall transparent cut glass tumbler, large starburst triangular relief carving, layered diamond geometric etched pattern",
    "素面高直玻璃杯": "plain tall straight transparent glass tumbler, smooth unpatterned glass wall, thick flat glass base",
    "斜纹磨砂矮玻璃杯": "rounded short transparent glass tumbler, fine thin diagonal frosted brushed line etching, subtle matte swirl texture",
    "竖棱纹玻璃杯": "tall vertical ribbed fluted glass tumbler, uniform thin vertical linear texture on full cup body",
    "波浪曲面玻璃杯": "transparent wavy curve glass tumbler, double concave undulating side contour",
    "长方形玻璃杯": "tall rectangular clear glass tumbler, vertical rectangular body, thick solid rectangular glass base, sharp angular edges",
    "沙漏钟形玻璃杯": "hourglass bell-shaped glass tumbler, flared wide rim, bulging curved midsection, narrow short circular glass foot base",
    "方形水晶玻璃杯": "square transparent crystal glass cup, square top opening, thick heavy solid square base",
    "通体磨砂玻璃杯": "frosted matte glass tumbler, full uniform sandblasted frosted surface, translucent milky white opaque texture",
    "琥珀色把手玻璃杯": "amber tinted transparent glass mug, curved single side handle, warm light honey brown glass tone, rounded bulbous cup body",
    "带底座钟形玻璃杯": "bell shape footed glass tumbler, wide flared rim, rounded bulbous mid body, thin stacked circular glass pedestal base",
    "八面棱面玻璃杯": "octagonal faceted clear glass tumbler, eight flat vertical angular facets, thick solid octagonal glass base",
    "圆角方形古典杯": "rounded square crystal old fashioned glass, softly curved square rim, thick heavy square glass base",
    "八角斜切刻花玻璃杯": "octagonal diamond cut crystal glass tumbler, slanted diagonal faceted wall carving, multi-plane triangular geometric facets",
    "厚底矮直玻璃杯": "transparent short tumbler glass, extra thick layered heavy glass base, smooth vertical straight wall",
    "碟形鸡尾酒杯": "coupe cocktail glass, wide shallow rounded bowl, slender thin transparent stem, large flat circular glass base",
    "素面古典短杯": "old fashioned short glass tumbler, uniform thick solid glass base, smooth unpatterned straight clear glass wall",
    "三角棱刻花威士忌杯": "faceted cut crystal whiskey glass, deep triangular diamond relief carving, multi-angle geometric prism facets",
    "圆底矮杯（含威士忌）": "short rounded transparent glass tumbler, small amount of amber whiskey liquid at bottom, thick solid glass base",
    "上宽下窄锥形玻璃杯": "tapered transparent glass tumbler, wide flared rim, narrow shrinking base, smooth unadorned clear borosilicate glass",
    "迷你高脚烈酒杯": "tiny stemmed shot glass, small flared cup bowl, short compact glass stem, mini circular flat base",
    "把手玻璃杯（盛琥珀茶水）": "clear glass mug with curved side handle, thick layered heavy glass base, half filled golden amber tea liquid",
}

# 按 key 长度降序排列（长词优先匹配）
_SORTED_KEYS = sorted(SEMANTIC_MAP.keys(), key=len, reverse=True)
_SORTED_CUP_KEYS = sorted(CUP_DICT.keys(), key=len, reverse=True)


def translate_cup_type(cup_text: str, seed: int | None = None) -> tuple[str, str | None]:
    """将中文杯型名称转译为 SD 英文描述。

    匹配策略（与 import random.txt 的 build_prompt 一致）：
      1. 精确全词匹配：输入文本恰好等于某个杯型 key
      2. 模糊包含匹配：在所有 key 包含输入文本的候选杯中随机选取
      3. 兜底：返回原文

    Args:
        cup_text: 从中提取了心理语义词后剩下的杯型名称部分
        seed: 可选的随机种子（使模糊匹配结果可复现）

    Returns:
        tuple:
          - translated: 转译后的英文描述
          - matched_key: 匹配到的杯型 key（None 表示未匹配）
    """
    if not cup_text:
        return cup_text, None

    rng = random.Random(seed) if seed is not None else random

    # 步骤1：精确全词匹配（长词优先）
    for cn_cup in _SORTED_CUP_KEYS:
        if cn_cup == cup_text:
            return CUP_DICT[cn_cup], cn_cup

    # 步骤2：正向模糊匹配 → 用户文本是杯型名的子串（如"高脚"匹配"高脚杯"）
    candidates = [(cn, en) for cn, en in CUP_DICT.items() if cup_text in cn]
    if candidates:
        matched_key, cup_en = rng.choice(candidates)
        return cup_en, matched_key

    # 步骤3：反向模糊匹配 → 杯型名是用户文本的子串（如"简约高脚杯"匹配"高脚杯"）
    # 按 key 长度降序优先，选最长匹配（最具体）
    for cn_cup in _SORTED_CUP_KEYS:
        if cn_cup in cup_text:
            return CUP_DICT[cn_cup], cn_cup

    # 步骤4：兜底 — 返回原文
    return cup_text, None


def translate_semantic(text: str, seed: int | None = None) -> tuple[str, list[str], str]:

    """将输入文本完整转译（心理语义 + 杯型）。

    处理流程：
      1. 在输入文本中检测并提取心理语义词 → 替换为英文 SD 外观描述
      2. 剩余文本（或全部原文）视为杯型名称 → 调用杯型词典精确/模糊匹配
      3. 合并：英文外观描述 + 英文杯型描述

    两个子模块独立工作：无语义词时仍会尝试杯型匹配；无杯型时仍输出语义映射结果。

    Args:
        text: 用户输入的中文提示词
        seed: 可选的随机种子（使杯型模糊匹配结果可复现）

    Returns:
        tuple:
          - processed_text: 完整替换后的文本
          - matched_terms: 被匹配到的心理语义词列表
          - preview: 翻译预览文本（展示替换前后对比）
    """
    matched_terms: list[str] = []
    remaining = text

    # 步骤1：心理语义提取
    for key in _SORTED_KEYS:
        if key in remaining:
            remaining = remaining.replace(key, "")
            matched_terms.append(key)

    semantic_part = "".join(SEMANTIC_MAP[k] for k in matched_terms)
    cup_query = remaining.strip()

    # 步骤2：杯型匹配（无语义词时用全文匹配杯型）
    if not cup_query and not matched_terms:
        # 全语义匹配但无剩余 → 也尝试全文杯型匹配
        cup_en, cup_key = translate_cup_type(text, seed=seed)
    elif not matched_terms:
        # 无语义词 → 直接用全文匹配杯型
        cup_en, cup_key = translate_cup_type(text, seed=seed)
    else:
        cup_en, cup_key = translate_cup_type(cup_query, seed=seed)

    # 两个模块都没匹配到 → 返回原文
    if not matched_terms and not cup_key:
        return text, [], ""

    # 步骤3：合并输出
    processed = f"{semantic_part}{cup_en}".strip()
    if not processed:
        processed = text

    # 构建预览
    preview_parts = []
    for k in matched_terms:
        preview_parts.append(f"「{k}」→ {SEMANTIC_MAP[k].strip()}")
    if cup_key:
        preview_parts.append(f"「{cup_key}」→ {cup_en}")
    elif cup_query:
        preview_parts.append(f"杯型「{cup_query}」未匹配，保留原文")
    preview = "；".join(preview_parts)

    return processed, matched_terms, preview


def get_semantic_keys() -> list[str]:
    """返回所有支持的心理语义词列表。"""
    return list(SEMANTIC_MAP.keys())


def get_cup_keys() -> list[str]:
    """返回所有支持的杯型名称列表。"""
    return list(CUP_DICT.keys())


if __name__ == "__main__":
    # 简单自测
    tests = [
        # (原文, 预期行为)
        "简洁柔和轻量收敛高脚杯",        # 4语义 + 精确杯型匹配
        "硬朗复杂直筒玻璃杯",            # 2语义 + 精确杯型匹配
        "简洁八角直筒玻璃杯",            # 1语义 + 精确杯型匹配
        "简约圆柱形透明玻璃杯",          # 无语义词（保持原文）
        "轻量马天尼杯",                  # 1语义 + 精确杯型匹配
        "简洁高脚",                      # 1语义 + 杯型模糊匹配（高脚→高脚杯）
    ]
    for t in tests:
        result, matched, preview = translate_semantic(t, seed=42)
        print(f"输入: {t}")
        print(f"匹配: {matched}")
        print(f"预览: {preview}")
        print(f"替换后: {result}")
        print("---")
