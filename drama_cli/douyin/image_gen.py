"""AI场景图生成引擎 - 支持 Pollinations免费 / AI场景图 / 角色合成 / 程序化生成"""

import json
import subprocess
import urllib.parse
import urllib.request
import ssl
from pathlib import Path
from typing import Optional
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import colorsys
import random
import os


class ImageGenerator:
    """AI场景图生成器（v3: 免费优先）"""

    # 角色图片目录（由外部设置）
    CHARACTER_DIR = None
    # AI场景图目录（优先使用）
    SCENE_DIR = None
    # Pollinations.ai 免费API（无需Key）
    POLLINATIONS_URL = "https://image.pollinations.ai/prompt"

    def __init__(self, api_key: str = "", base_url: str = "https://api.openai.com/v1"):
        self.client = OpenAI(api_key=api_key or "sk-placeholder", base_url=base_url)
        self.api_key = api_key

    def generate_scene(
        self, scene: dict, episode_num: int, output_path: Path,
        width: int = 1080, height: int = 1920,
        visual_style: str = "cinematic",
        color_palette: str = "#1a1a2e,#e94560",
        scene_key: str = ""
    ) -> Path:
        """生成场景图（v3: 免费API优先）"""
        # 1. 优先检查本地AI场景图
        if scene_key and self.SCENE_DIR:
            ai_scene_path = self._find_ai_scene(scene_key)
            if ai_scene_path:
                return self._use_ai_scene(ai_scene_path, episode_num, width, height, output_path)

        # 2. 尝试 Pollinations.ai 免费生成
        location = scene.get("location", "")
        desc = scene.get("visual_description", "")
        time_str = scene.get("time", "")
        if self._pollinations_generate(location, desc, time_str, width, height, output_path):
            return output_path

        # 3. 付费API生成（需要API key）
        location = scene.get("location", "")
        desc = scene.get("visual_description", "")
        time_str = scene.get("time", "")

        if self.api_key:
            return self._ai_generate(location, desc, time_str, visual_style,
                                     color_palette, width, height, output_path)
        else:
            return self._procedural_generate(scene, episode_num, visual_style,
                                             color_palette, width, height, output_path)

    def _find_ai_scene(self, scene_key: str) -> Optional[Path]:
        """查找AI预生成的场景图"""
        if not self.SCENE_DIR:
            return None
        scene_dir = Path(self.SCENE_DIR)
        for ext in ['.jpg', '.png', '.jpeg']:
            candidate = scene_dir / f"{scene_key}{ext}"
            if candidate.exists():
                return candidate
        return None

    def _use_ai_scene(self, ai_path: Path, episode_num: int, width: int, height: int, output_path: Path) -> Path:
        """使用AI场景图并添加集数标签"""
        img = Image.open(ai_path).convert("RGB")
        img = img.resize((width, height), Image.LANCZOS)
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        try:
            font_md = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 36)
            font_sm = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 28)
        except:
            font_md = font_sm = ImageFont.load_default()
        draw.rounded_rectangle([30, 30, 220, 85], radius=15, fill=(0, 0, 0, 180))
        draw.text((125, 57), f"第 {episode_num} 集", fill=(255, 215, 0), font=font_md, anchor="mm")
        draw.rounded_rectangle([width // 4, height - 100, 3 * width // 4, height - 60], radius=10, fill=(255, 215, 0, 60))
        draw.text((width // 2, height - 80), "DramaCLI Pro", fill=(200, 200, 200), font=font_sm, anchor="mm")
        img = img.convert("RGB")
        img.save(output_path, quality=95)
        return output_path

    def _pollinations_generate(self, location: str, desc: str, time_str: str, width: int, height: int, output_path: Path) -> bool:
        """使用 Pollinations.ai 免费API生成（无需API Key）"""
        import requests
        prompt = (
            f"Vertical 9:16 cinematic short drama scene, {location}, {desc}. Time: {time_str}. "
            f"Dramatic lighting, cinematic composition, 1080x1920, film grain, sharp focus, suitable for Douyin short drama. "
            f"No text, no subtitles, no watermarks."
        )
        encoded = urllib.parse.quote(prompt)
        url = f"{self.POLLINATIONS_URL}/{encoded}?width={width}&height={height}&model=flux&seed={random.randint(1,1000000)}"

        try:
            # 禁用SSL验证避免证书问题
            response = requests.get(url, timeout=30, verify=False)
            if response.status_code == 200 and len(response.content) > 10000:
                output_path.write_bytes(response.content)
                print(f"  ✅ Pollinations.ai 免费生成成功: {output_path.name}")
                return True
            else:
                print(f"  ⚠️ Pollinations 失败: status={response.status_code}")
                return False
        except Exception as e:
            print(f"  ⚠️ Pollinations 调用失败: {e}")
            return False

    def _ai_generate(self, location, desc, time_str, visual_style,
                     color_palette, width, height, output_path):
        """使用 DALL-E 生成（付费，需要API key）"""
        colors = color_palette.split(",") if color_palette else ["#1a1a2e", "#e94560"]
        dominant = colors[0].replace("#", "")
        accent = colors[-1].replace("#", "")

        prompt = (
            f"Vertical cinematic scene for a short drama: {location}, {desc}. "
            f"Time: {time_str}. Style: {visual_style}, 9:16 vertical composition, "
            f"dramatic lighting, color grading with deep {dominant} tones and {accent} accents, "
            f"cinematic depth of field, suitable for Douyin/TikTok short drama. "
            f"No text, no subtitles, no watermarks."
        )

        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1792",  # 竖屏比例
                quality="standard",
                n=1,
            )

            # Download image
            import requests
            img_url = response.data[0].url
            img_data = requests.get(img_url).content

            # Save and resize
            temp_path = output_path.with_suffix(".temp.png")
            temp_path.write_bytes(img_data)

            img = Image.open(temp_path)
            img = img.resize((width, height), Image.LANCZOS)
            img.save(output_path)
            temp_path.unlink()

            return output_path
        except Exception as e:
            print(f"  AI图像生成失败: {e}，使用程序化生成")
            return output_path  # fallback handled by caller

    def _procedural_generate(self, scene, episode_num, visual_style,
                             color_palette, width, height, output_path):
        """程序化生成场景图（v2: 含角色合成）"""
        from PIL import ImageDraw, ImageFont

        colors = color_palette.split(",") if color_palette else ["#1a1a2e", "#e94560", "#0f3460"]
        color1 = self._hex_to_rgb(colors[0].strip())
        color2 = self._hex_to_rgb(colors[-1].strip())
        if len(colors) > 2:
            color3 = self._hex_to_rgb(colors[1].strip())
        else:
            color3 = self._hex_to_rgb("#0f3460")

        img = Image.new("RGB", (width, height), color1)
        draw = ImageDraw.Draw(img)

        # 多层渐变背景
        for y in range(height):
            ratio = y / height
            if ratio < 0.5:
                r = ratio * 2
                r_col = self._lerp_rgb(color1, color2, r)
            else:
                r = (ratio - 0.5) * 2
                r_col = self._lerp_rgb(color2, color3, r)
            draw.line([(0, y), (width, y)], fill=r_col)

        # 添加光效
        for i in range(3):
            cx = random.randint(0, width)
            cy = random.randint(0, height // 2)
            cr = random.randint(200, 500)
            for r in range(cr, 0, -5):
                alpha = int(40 * r / cr)
                draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                             fill=(alpha, alpha, alpha))

        # 添加装饰粒子
        for _ in range(50):
            px = random.randint(0, width)
            py = random.randint(0, height)
            ps = random.randint(1, 3)
            brightness = random.randint(100, 255)
            draw.ellipse([px, py, px + ps, py + ps],
                         fill=(brightness, brightness, brightness))

        # 文字
        try:
            font_lg = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 56)
            font_md = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 36)
            font_sm = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 28)
            font_name = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 28)
        except:
            font_lg = font_md = font_sm = font_name = ImageFont.load_default()

        loc = scene.get("location", "")
        desc = scene.get("visual_description", "")[:80]
        time_str = scene.get("time", "")
        ep_text = f"第 {episode_num} 集"

        # 装饰线
        gold = (255, 215, 0)
        draw.rectangle([80, height // 2 - 160, width - 80, height // 2 - 155], fill=gold)
        draw.rectangle([80, height // 2 + 155, width - 80, height // 2 + 160], fill=gold)

        # 左上角集数标签
        draw.rounded_rectangle([30, 30, 200, 80], radius=15, fill=(0, 0, 0, 180))
        draw.text((115, 55), ep_text, fill=gold, font=font_md, anchor="mm")

        # 中央场景信息
        draw.text((width // 2, height // 2 - 130), f"场景: {loc}", fill=(255, 255, 255), font=font_lg, anchor="mm")
        draw.text((width // 2, height // 2 - 60), time_str, fill=(200, 200, 200), font=font_md, anchor="mm")
        draw.text((width // 2, height // 2 + 20), desc, fill=(180, 180, 180), font=font_sm, anchor="mm")

        # 底部装饰
        draw.rounded_rectangle([width // 4, height - 100, 3 * width // 4, height - 60],
                               radius=10, fill=(255, 215, 0, 60))
        draw.text((width // 2, height - 80), "DramaCLI Pro", fill=(200, 200, 200), font=font_sm, anchor="mm")

        img.save(output_path, quality=95)

        # ── 角色合成 ──
        if self.CHARACTER_DIR:
            scene_chars = [d.get('character', '') for d in scene.get('dialogues', [])]
            if scene_chars:
                img = self._composite_characters(img, scene_chars, width, height, font_name)
                img.save(output_path, quality=95)

        return output_path

    def _composite_characters(self, bg, scene_chars, width, height, font_name):
        """将角色柔边合成到背景上"""
        char_dir = Path(self.CHARACTER_DIR) if self.CHARACTER_DIR else None
        if not char_dir or not char_dir.exists():
            return bg

        # 加载角色图片
        char_images = {}
        for f in char_dir.glob("*.jpg"):
            name = f.stem
            img = Image.open(f).convert("RGBA")
            h_ratio = 650 / img.height
            img = img.resize((int(img.width * h_ratio), 650), Image.LANCZOS)
            char_images[name] = img

        # 角色名映射（中文名 → 文件名）
        name_map = {
            "陆景琛": "lu_jingchen", "沈若溪": "shen_ruoxi",
            "顾曼妮": "gu_manni", "陆管家": "lu_guanjia"
        }

        bg = bg.convert("RGBA")
        present = list(dict.fromkeys([n for n in scene_chars if n in name_map and name_map[n] in char_images]))
        if not present:
            return bg.convert("RGB")

        n = len(present)
        char_bottom = height - 320

        for i, name in enumerate(present):
            char_img = char_images[name_map[name]].copy()
            cw, ch = char_img.size

            # 降饱和+压暗
            enhancer = ImageEnhance.Color(char_img.convert("RGB"))
            char_img = enhancer.enhance(0.85).convert("RGBA")
            enhancer = ImageEnhance.Brightness(char_img.convert("RGB"))
            char_img = enhancer.enhance(0.9).convert("RGBA")

            # 柔边遮罩
            mask = self._soft_edge_mask((cw, ch), feather=90)

            # 位置
            if n == 1:
                cx = width // 2 - cw // 2 - 80
            elif n == 2:
                cx = 50 if i == 0 else width - cw - 50
            else:
                gap = (width - cw * n) // (n + 1)
                cx = gap + i * (cw + gap)
            cy = char_bottom - ch

            # 阴影
            shadow = Image.new("RGBA", (cw + 60, ch + 60), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            sd.ellipse([30 + cw // 4, 30 + ch - 10, 30 + cw * 3 // 4, 30 + ch + 30], fill=(0, 0, 0, 110))
            bg.paste(shadow, (cx - 30, cy - 30), shadow)

            # 合成
            char_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            char_layer.paste(char_img, (0, 0))
            char_layer.putalpha(mask)
            bg.paste(char_layer, (cx, cy), char_layer)

            # 名字标签
            draw = ImageDraw.Draw(bg)
            name_w = len(name) * 30 + 20
            name_x = cx + cw // 2 - name_w // 2
            draw.rounded_rectangle([name_x, cy - 45, name_x + name_w, cy - 9], radius=10, fill=(0, 0, 0, 200))
            draw.text((cx + cw // 2, cy - 27), name, fill=(255, 215, 0), font=font_name, anchor='mm')

        # 暗角
        vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        for y in range(height):
            a = 0
            if y < 150: a = int(100 * (1 - y / 150))
            elif y > height - 150: a = int(100 * (1 - (height - y) / 150))
            if a > 0: vd.line([(0, y), (width, y)], fill=(0, 0, 0, a))
        for x in range(width):
            a = 0
            if x < 80: a = int(80 * (1 - x / 80))
            elif x > width - 80: a = int(80 * (1 - (width - x) / 80))
            if a > 0: vd.line([(x, 0), (x, height)], fill=(0, 0, 0, a))
        bg.paste(vignette, (0, 0), vignette)

        return bg.convert("RGB")

    @staticmethod
    def _soft_edge_mask(size, feather=80):
        """柔边渐变遮罩"""
        w, h = size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        for x in range(w):
            if x < feather:
                alpha = int(255 * x / feather)
            elif x > w - feather:
                alpha = int(255 * (w - x) / feather)
            else:
                alpha = 255
            draw.line([(x, 0), (x, h)], fill=alpha)
        for y in range(h - feather, h):
            alpha_bottom = int(255 * (h - y) / feather)
            for x in range(w):
                current = mask.getpixel((x, y))
                mask.putpixel((x, y), min(current, alpha_bottom))
        return mask

    def _hex_to_rgb(self, hex_color: str):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def _lerp_rgb(self, c1, c2, t):
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    def generate_cover(self, title: str, genre: str, visual_style: str,
                       color_palette: str, output_path: Path,
                       width: int = 1080, height: int = 1920):
        """生成封面图"""
        colors = color_palette.split(",") if color_palette else ["#1a1a2e", "#e94560"]
        c1 = self._hex_to_rgb(colors[0].strip())
        c2 = self._hex_to_rgb(colors[-1].strip())

        img = Image.new("RGB", (width, height), c1)
        draw = ImageDraw.Draw(img)

        # 渐变背景
        for y in range(height):
            r = y / height
            draw.line([(0, y), (width, y)], self._lerp_rgb(c1, c2, r))

        try:
            font_title = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 72)
            font_genre = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 36)
            font_watermark = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
        except:
            font_title = font_genre = font_watermark = ImageFont.load_default()

        # 标题
        draw.text((width // 2, height // 2 - 60), title, fill=(255, 215, 0), font=font_title, anchor="mm")
        draw.text((width // 2, height // 2 + 30), genre, fill=(255, 255, 255), font=font_genre, anchor="mm")

        # 装饰线
        draw.rectangle([width // 4, height // 2 + 80, 3 * width // 4, height // 2 + 82], fill=(255, 215, 0))

        # 水印
        draw.text((width // 2, height - 60), "DramaCLI Pro · AI短剧工厂", fill=(150, 150, 150), font=font_watermark, anchor="mm")

        img.save(output_path, quality=95)
        return output_path