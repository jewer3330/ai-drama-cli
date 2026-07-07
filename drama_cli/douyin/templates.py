"""抖音模板系统 - 10+ 专业短剧模板"""

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DramaTemplate:
    """短剧模板"""
    name: str
    genre: str
    description: str
    style: str
    typical_episodes: int = 3
    scenes_per_episode: int = 5
    # 角色预设
    character_archetypes: list = field(default_factory=list)
    # 剧情反转点
    twist_points: list = field(default_factory=list)
    # 视觉风格
    visual_style: str = ""
    color_palette: str = ""
    # BGM预设
    bgm_mood: str = ""
    # 标签
    tags: list = field(default_factory=list)
    # 系统提示词补充
    prompt_addon: str = ""


# ============================================================
# 10 套爆款模板
# ============================================================

TEMPLATES = {
    "霸道总裁": DramaTemplate(
        name="霸道总裁",
        genre="都市甜宠",
        description="霸道总裁爱上灰姑娘，契约婚姻遇真爱",
        style="爽文",
        visual_style="都市奢华",
        color_palette="#1a1a2e,#e94560,#0f3460",
        bgm_mood="romantic_intense",
        character_archetypes=[
            {"name": "男主", "role": "总裁", "personality": "冷酷霸道、深情专一", "voice_style": "霸气"},
            {"name": "女主", "role": "灰姑娘", "personality": "坚强独立、善良温柔", "voice_style": "温柔"},
            {"name": "女配", "role": "白月光/恶毒女配", "personality": "心机绿茶", "voice_style": "冷淡"},
            {"name": "男配", "role": "暖男备胎", "personality": "温柔体贴", "voice_style": "温柔"},
        ],
        twist_points=["身份反转", "车祸/失忆", "契约结束", "前任归来"],
        tags=["#霸道总裁", "#甜宠", "#契约婚姻", "#短剧"],
        prompt_addon="每个场景结尾要设计悬念或反转，对话要充满张力，总裁台词要霸气。"
    ),

    "穿越王妃": DramaTemplate(
        name="穿越王妃",
        genre="古装穿越",
        description="现代女孩穿越古代，与冷面王爷的爱恨纠葛",
        style="女频爽文",
        visual_style="古风宫廷",
        color_palette="#2d1b00,#8b4513,#ffd700",
        bgm_mood="ancient_epic",
        character_archetypes=[
            {"name": "女主", "role": "穿越者", "personality": "机智勇敢、现代思维", "voice_style": "活泼"},
            {"name": "男主", "role": "王爷", "personality": "冷面战神、腹黑深情", "voice_style": "霸气"},
            {"name": "女配", "role": "侧妃", "personality": "嫉妒狠毒", "voice_style": "冷淡"},
        ],
        twist_points=["身份暴露", "宫斗陷害", "王爷误会", "以死明志"],
        tags=["#穿越", "#古装", "#王爷", "#短剧"],
        prompt_addon="融入古代宫廷礼仪细节，女主用现代知识解决古代问题制造爽点。"
    ),

    "重生复仇": DramaTemplate(
        name="重生复仇",
        genre="都市复仇",
        description="被害死后重生，手撕渣男贱女，走上人生巅峰",
        style="复仇爽文",
        visual_style="暗黑都市",
        color_palette="#0d0d0d,#8b0000,#c0c0c0",
        bgm_mood="dark_intense",
        character_archetypes=[
            {"name": "女主", "role": "重生者", "personality": "冷静腹黑、步步为营", "voice_style": "冷淡"},
            {"name": "男主", "role": "商界大佬", "personality": "神秘强大、暗中守护", "voice_style": "霸气"},
            {"name": "反派女", "role": "塑料闺蜜", "personality": "虚伪狠毒", "voice_style": "活泼"},
            {"name": "反派男", "role": "渣男前任", "personality": "势利眼", "voice_style": "冷淡"},
        ],
        twist_points=["重生觉醒", "步步反击", "身份揭露", "顶级大佬现身"],
        tags=["#重生", "#复仇", "#打脸", "#短剧"],
        prompt_addon="每集至少一个打脸爽点，复仇节奏要快，台词要犀利。"
    ),

    "豪门千金": DramaTemplate(
        name="豪门千金",
        genre="豪门虐恋",
        description="豪门千金隐藏身份，与商界大佬的契约婚姻",
        style="豪门虐恋",
        visual_style="顶级奢华",
        color_palette="#1a1a2e,#d4af37,#ffffff",
        bgm_mood="elegant_dramatic",
        character_archetypes=[
            {"name": "女主", "role": "隐藏千金", "personality": "低调隐忍、实则强大", "voice_style": "温柔"},
            {"name": "男主", "role": "商界帝王", "personality": "冷酷毒舌、后知后爱", "voice_style": "霸气"},
            {"name": "女配", "role": "家族联姻对象", "personality": "高高在上", "voice_style": "冷淡"},
        ],
        twist_points=["身份揭露", "家族恩怨", "替身真相", "追妻火葬场"],
        tags=["#豪门", "#虐恋", "#追妻", "#短剧"],
        prompt_addon="突出阶级反差和身份冲突，虐要虐得狠，甜要甜得齁。"
    ),

    "悬疑惊悚": DramaTemplate(
        name="悬疑惊悚",
        genre="悬疑推理",
        description="连环案件背后，隐藏着惊天秘密",
        style="悬疑推理",
        visual_style="暗色调",
        color_palette="#000000,#1a1a2e,#8b0000",
        bgm_mood="suspense",
        character_archetypes=[
            {"name": "男主", "role": "刑警/侦探", "personality": "冷静敏锐、执着", "voice_style": "冷淡"},
            {"name": "女主", "role": "关键证人/搭档", "personality": "勇敢机智", "voice_style": "温柔"},
        ],
        twist_points=["案发现场", "线索反转", "凶手现身", "真相大白"],
        tags=["#悬疑", "#推理", "#烧脑", "#短剧"],
        prompt_addon="每集结尾必须留悬念，细节要经得起推敲，反转要出乎意料。"
    ),

    "校园甜宠": DramaTemplate(
        name="校园甜宠",
        genre="校园恋爱",
        description="学霸校草与学渣女主的甜蜜校园故事",
        style="甜宠",
        visual_style="清新校园",
        color_palette="#87ceeb,#ffb6c1,#ffffff",
        bgm_mood="sweet_light",
        character_archetypes=[
            {"name": "女主", "role": "学渣", "personality": "活泼可爱、不服输", "voice_style": "活泼"},
            {"name": "男主", "role": "学霸校草", "personality": "高冷但温柔", "voice_style": "霸气"},
            {"name": "女配", "role": "校花", "personality": "嫉妒挑衅", "voice_style": "冷淡"},
        ],
        twist_points=["意外同桌", "补习告白", "毕业分离", "重逢"],
        tags=["#校园", "#甜宠", "#青春", "#短剧"],
        prompt_addon="要有青春感，对话要自然，暧昧期要甜，名场面要有记忆点。"
    ),

    "战神归来": DramaTemplate(
        name="战神归来",
        genre="都市战神",
        description="退役战神回归都市，发现妻女受辱，一怒之下十万将士归来",
        style="战神爽文",
        visual_style="铁血都市",
        color_palette="#1a1a2e,#b8860b,#8b0000",
        bgm_mood="epic_intense",
        character_archetypes=[
            {"name": "男主", "role": "退役战神", "personality": "低调隐忍、战力爆表", "voice_style": "霸气"},
            {"name": "女主", "role": "妻子", "personality": "温柔坚强", "voice_style": "温柔"},
            {"name": "反派", "role": "豪门恶少", "personality": "嚣张跋扈", "voice_style": "冷淡"},
        ],
        twist_points=["身份揭露", "一怒为红颜", "十万将士", "跪地求饶"],
        tags=["#战神", "#爽文", "#打脸", "#短剧"],
        prompt_addon="每集必须有打脸名场面，战神一怒天地变色，台词要霸气侧漏。"
    ),

    "娱乐圈": DramaTemplate(
        name="娱乐圈",
        genre="娱乐圈",
        description="影帝男神与新人女演员的甜蜜恋爱",
        style="娱乐圈甜宠",
        visual_style="星光璀璨",
        color_palette="#2d1b4e,#ffd700,#ff69b4",
        bgm_mood="glamorous",
        character_archetypes=[
            {"name": "女主", "role": "新人演员", "personality": "努力上进、单纯", "voice_style": "温柔"},
            {"name": "男主", "role": "影帝", "personality": "高冷毒舌、实则宠溺", "voice_style": "霸气"},
            {"name": "女配", "role": "当红花旦", "personality": "嫉妒打压", "voice_style": "冷淡"},
        ],
        twist_points=["意外合作", "剧组绯闻", "公开恋情", "黑粉危机"],
        tags=["#娱乐圈", "#影帝", "#甜宠", "#短剧"],
        prompt_addon="加入娱乐圈元素：颁奖典礼、剧组拍摄、热搜、黑粉，增加真实感。"
    ),

    "末日求生": DramaTemplate(
        name="末日求生",
        genre="末日科幻",
        description="丧尸病毒爆发，末世中的人性考验",
        style="末日生存",
        visual_style="废土暗黑",
        color_palette="#2f4f4f,#8b0000,#696969",
        bgm_mood="dark_tension",
        character_archetypes=[
            {"name": "男主", "role": "幸存者领袖", "personality": "冷酷果断、重情义", "voice_style": "霸气"},
            {"name": "女主", "role": "异能者", "personality": "坚强冷静", "voice_style": "冷淡"},
        ],
        twist_points=["丧尸爆发", "人性抉择", "背叛", "希望曙光"],
        tags=["#末日", "#丧尸", "#生存", "#短剧"],
        prompt_addon="节奏要紧张，每一秒都是生死抉择，人性黑暗面要展现到位。"
    ),

    "玄幻修仙": DramaTemplate(
        name="玄幻修仙",
        genre="玄幻仙侠",
        description="废柴少年逆天改命，踏上修仙之路",
        style="玄幻爽文",
        visual_style="仙侠奇境",
        color_palette="#000080,#9400d3,#00ffff",
        bgm_mood="epic_fantasy",
        character_archetypes=[
            {"name": "男主", "role": "修仙者", "personality": "坚韧不拔、逆天改命", "voice_style": "霸气"},
            {"name": "女主", "role": "仙门圣女", "personality": "清冷高傲", "voice_style": "温柔"},
            {"name": "反派", "role": "魔道巨擘", "personality": "阴险狠毒", "voice_style": "冷淡"},
        ],
        twist_points=["觉醒灵根", "宗门大比", "秘境奇遇", "飞升渡劫"],
        tags=["#修仙", "#玄幻", "#爽文", "#短剧"],
        prompt_addon="要有修仙体系：灵根、境界、功法、法宝，打斗描写要精彩。"
    ),
}


def get_template(name: str) -> Optional[DramaTemplate]:
    """获取模板"""
    return TEMPLATES.get(name)


def list_templates() -> list[str]:
    """列出所有模板"""
    return list(TEMPLATES.keys())


def build_prompt(template: DramaTemplate, topic: str, episodes: int) -> str:
    """根据模板构建系统提示词"""
    char_desc = ""
    for c in template.character_archetypes:
        char_desc += f"- {c['name']}: {c['role']}, {c['personality']}\n"

    twists = " → ".join(template.twist_points)

    return f"""你是一位抖音短剧金牌编剧，擅长创作{template.genre}类短剧。

## 创作设定
- 类型: {template.genre}
- 风格: {template.style}
- 视觉风格: {template.visual_style}
- 集数: {episodes}

## 角色原型
{char_desc}

## 剧情节奏
反转点: {twists}

## 创作要求
{template.prompt_addon}

## 抖音短剧黄金法则
1. 前三秒必须有冲突或悬念
2. 每集结尾必须有钩子（hook）
3. 对话不超过3句，快速推进剧情
4. 每集至少1个爽点或反转
5. 台词要短，适合竖屏字幕阅读
6. 情绪要有起伏，不能平铺直叙
"""


def get_visual_config(template: DramaTemplate) -> dict:
    """获取视觉配置"""
    return {
        "visual_style": template.visual_style,
        "color_palette": template.color_palette,
        "bgm_mood": template.bgm_mood,
        "tags": template.tags,
    }