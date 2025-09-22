#!/usr/bin/env python3
"""
图片水印添加工具
基于EXIF信息中的拍摄时间添加水印到图片上
"""

import os
import argparse
import sys
from PIL import Image, ImageDraw, ImageFont, ImageColor
import exifread
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_exif_date(image_path):
    """
    从图片EXIF信息中获取拍摄日期
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        str: 年月日格式的日期字符串，如"2023:01:15"
    """
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
            # 尝试获取原始拍摄日期
            if 'EXIF DateTimeOriginal' in tags:
                date_str = str(tags['EXIF DateTimeOriginal'])
                return date_str.split()[0]  # 只返回日期部分
            
            # 如果没有原始日期，尝试获取一般日期
            elif 'Image DateTime' in tags:
                date_str = str(tags['Image DateTime'])
                return date_str.split()[0]
                
    except Exception as e:
        logger.warning(f"无法从 {os.path.basename(image_path)} 读取EXIF信息: {e}")
    
    return None

def calculate_position(img_width, img_height, text_width, text_height, position):
    """
    根据位置参数计算水印坐标
    
    Args:
        img_width: 图片宽度
        img_height: 图片高度
        text_width: 文本宽度
        text_height: 文本高度
        position: 位置参数
        
    Returns:
        tuple: (x, y) 坐标
    """
    padding = 20  # 边距
    
    position_map = {
        "top-left": (padding, padding),
        "top-right": (img_width - text_width - padding, padding),
        "bottom-left": (padding, img_height - text_height - padding),
        "bottom-right": (img_width - text_width - padding, img_height - text_height - padding),
        "center": ((img_width - text_width) // 2, (img_height - text_height) // 2)
    }
    
    return position_map.get(position, position_map["bottom-right"])

def get_font(font_size):
    """
    获取字体对象，支持多种字体回退方案
    """
    font_paths = [
        "Arial.ttf",
        "DejaVuSans.ttf",
        "Helvetica.ttf",
        "/System/Library/Fonts/SFNS.ttf",  # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux
    ]
    
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, font_size)
        except IOError:
            continue
    
    # 如果所有字体都失败，使用默认字体
    logger.warning("无法加载系统字体，使用默认字体")
    return ImageFont.load_default()

def add_watermark_to_image(image_path, output_path, text, font_size, color, position, opacity=0.8):
    """
    给图片添加水印
    
    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        text: 水印文本
        font_size: 字体大小
        color: 字体颜色
        position: 水印位置
        opacity: 水印透明度 (0-1)
    """
    try:
        # 打开图片
        with Image.open(image_path) as image:
            # 转换为RGB模式（确保兼容性）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            draw = ImageDraw.Draw(image)
            
            # 获取字体
            font = get_font(font_size)
            
            # 获取文本尺寸
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # 计算水印位置
            img_width, img_height = image.size
            x, y = calculate_position(img_width, img_height, text_width, text_height, position)
            
            # 添加文本阴影效果（提高可读性）
            shadow_color = (0, 0, 0) if color != (0, 0, 0) else (255, 255, 255)
            draw.text((x+1, y+1), text, font=font, fill=shadow_color)
            
            # 添加水印文本
            draw.text((x, y), text, font=font, fill=color)
            
            # 保存图片
            image.save(output_path, quality=95)
            logger.info(f"已处理: {os.path.basename(output_path)}")
            
    except Exception as e:
        logger.error(f"处理图片 {os.path.basename(image_path)} 时出错: {e}")
        raise

def process_directory(input_path, font_size, color, position):
    """
    处理目录中的所有图片
    
    Args:
        input_path: 输入目录路径
        font_size: 字体大小
        color: 字体颜色
        position: 水印位置
        
    Returns:
        bool: 处理是否成功
    """
    # 检查输入路径是否存在
    if not os.path.exists(input_path):
        logger.error(f"错误: 路径 {input_path} 不存在")
        return False
    
    # 创建输出目录
    base_dir = os.path.dirname(input_path) if os.path.isfile(input_path) else input_path
    dir_name = os.path.basename(base_dir.rstrip('/\\'))
    output_dir = os.path.join(base_dir, f"{dir_name}_watermark")
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"创建输出目录: {output_dir}")
    except Exception as e:
        logger.error(f"创建输出目录失败: {e}")
        return False
    
    # 支持的图片格式
    image_extensions = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif', '.webp')
    
    # 确定要处理的文件列表
    if os.path.isfile(input_path):
        files = [input_path]
    else:
        files = [os.path.join(input_path, f) for f in os.listdir(input_path) 
                if os.path.isfile(os.path.join(input_path, f))]
    
    # 处理每个文件
    processed_count = 0
    for file_path in files:
        try:
            # 检查是否为图片文件
            if not file_path.lower().endswith(image_extensions):
                continue
            
            # 获取EXIF日期
            date_str = get_exif_date(file_path)
            if not date_str:
                logger.warning(f"无法从 {os.path.basename(file_path)} 获取EXIF日期信息，使用当前日期")
                date_str = datetime.now().strftime("%Y:%m:%d")
            
            # 生成输出路径
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{name}_watermark{ext}")
            
            # 添加水印
            add_watermark_to_image(file_path, output_path, date_str, font_size, color, position)
            processed_count += 1
            
        except Exception as e:
            logger.error(f"处理文件 {os.path.basename(file_path)} 时出错: {e}")
            continue
    
    logger.info(f"处理完成! 共处理了 {processed_count} 张图片，结果保存在 {output_dir}")
    return processed_count > 0

def parse_color(color_str):
    """
    解析颜色字符串为RGB元组
    
    Args:
        color_str: 颜色字符串（名称或十六进制）
        
    Returns:
        tuple: RGB颜色元组
        
    Raises:
        ValueError: 颜色格式错误
    """
    # 预定义颜色名称映射
    color_map = {
        'black': (0, 0, 0),
        'white': (255, 255, 255),
        'red': (255, 0, 0),
        'green': (0, 128, 0),
        'blue': (0, 0, 255),
        'yellow': (255, 255, 0),
        'cyan': (0, 255, 255),
        'magenta': (255, 0, 255),
        'gray': (128, 128, 128),
        'grey': (128, 128, 128),
        'orange': (255, 165, 0),
        'purple': (128, 0, 128),
        'pink': (255, 192, 203),
        'brown': (165, 42, 42),
    }
    
    # 检查是否为预定义颜色
    if color_str.lower() in color_map:
        return color_map[color_str.lower()]
    
    # 检查是否为十六进制颜色
    if color_str.startswith('#'):
        try:
            return ImageColor.getrgb(color_str)
        except ValueError:
            raise ValueError(f"无效的十六进制颜色: {color_str}")
    
    # 尝试使用PIL的颜色解析
    try:
        return ImageColor.getrgb(color_str)
    except ValueError:
        raise ValueError(f"不支持的颜色: {color_str}。支持的颜色: {', '.join(color_map.keys())}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="给图片添加基于EXIF日期信息的水印",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s /path/to/images -s 30 -c white -p bottom-right
  %(prog)s /path/to/image.jpg -s 40 -c "#FF0000" -p center
  %(prog)s /path/to/photos -s 24 -c black -p top-left
"""
    )
    
    parser.add_argument("input_path", help="图片文件或目录路径")
    parser.add_argument("-s", "--size", type=int, default=20, 
                       help="字体大小，默认20")
    parser.add_argument("-c", "--color", default="white", 
                       help="字体颜色，支持颜色名称或#RRGGBB格式，默认白色")
    parser.add_argument("-p", "--position", default="bottom-right", 
                       choices=["top-left", "top-right", "bottom-left", "bottom-right", "center"],
                       help="水印位置，默认右下角")
    parser.add_argument("--verbose", action="store_true", 
                       help="显示详细日志信息")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        color = parse_color(args.color)
        success = process_directory(args.input_path, args.size, color, args.position)
        
        if not success:
            logger.error("处理失败，没有成功处理任何图片")
            sys.exit(1)
            
    except ValueError as e:
        logger.error(f"参数错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()