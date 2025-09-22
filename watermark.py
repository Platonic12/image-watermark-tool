import os
import argparse
from PIL import Image, ImageDraw, ImageFont
import piexif
from datetime import datetime

def get_exif_date(image_path):
    """从图片EXIF信息中获取拍摄日期"""
    try:
        exif_dict = piexif.load(image_path)
        
        # 尝试从EXIF中获取原始日期时间
        if piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
            date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
            return date_str.split()[0]  # 只返回年月日部分
        
        # 如果没有原始日期，尝试获取一般日期时间
        if piexif.ImageIFD.DateTime in exif_dict["0th"]:
            date_str = exif_dict["0th"][piexif.ImageIFD.DateTime].decode('utf-8')
            return date_str.split()[0]
            
    except Exception as e:
        print(f"无法从 {image_path} 读取EXIF信息: {e}")
    
    return None

def add_watermark_to_image(image_path, output_path, text, font_size, color, position):
    """给图片添加水印"""
    try:
        # 打开图片
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        
        # 尝试使用系统字体，如果失败则使用默认字体
        try:
            font = ImageFont.truetype("Arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # 获取文本尺寸
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # 计算水印位置
        img_width, img_height = image.size
        
        if position == "top-left":
            x = 10
            y = 10
        elif position == "top-right":
            x = img_width - text_width - 10
            y = 10
        elif position == "bottom-left":
            x = 10
            y = img_height - text_height - 10
        elif position == "bottom-right":
            x = img_width - text_width - 10
            y = img_height - text_height - 10
        elif position == "center":
            x = (img_width - text_width) // 2
            y = (img_height - text_height) // 2
        else:
            x = 10
            y = 10
        
        # 添加水印
        draw.text((x, y), text, font=font, fill=color)
        
        # 保存图片
        image.save(output_path)
        print(f"已处理: {output_path}")
        
    except Exception as e:
        print(f"处理图片 {image_path} 时出错: {e}")

def process_images(input_path, font_size, color, position):
    """处理目录中的所有图片"""
    # 检查输入路径是否存在
    if not os.path.exists(input_path):
        print(f"错误: 路径 {input_path} 不存在")
        return
    
    # 创建输出目录
    base_dir = os.path.dirname(input_path) if os.path.isfile(input_path) else input_path
    output_dir = os.path.join(base_dir, f"{os.path.basename(base_dir)}_watermark")
    os.makedirs(output_dir, exist_ok=True)
    
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
            if not file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                continue
            
            # 获取EXIF日期
            date_str = get_exif_date(file_path)
            if not date_str:
                print(f"警告: 无法从 {os.path.basename(file_path)} 获取日期信息，跳过")
                continue
            
            # 生成输出路径
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            output_path = os.path.join(output_dir, f"{name}_watermark{ext}")
            
            # 添加水印
            add_watermark_to_image(file_path, output_path, date_str, font_size, color, position)
            processed_count += 1
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
    
    print(f"处理完成! 共处理了 {processed_count} 张图片，结果保存在 {output_dir}")

def parse_color(color_str):
    """解析颜色字符串为RGB元组"""
    if color_str.startswith('#'):
        # 十六进制颜色 #RRGGBB
        color_str = color_str[1:]
        if len(color_str) != 6:
            raise ValueError("颜色格式错误，应为 #RRGGBB")
        return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4))
    else:
        # 预定义颜色名称
        color_map = {
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
        }
        if color_str.lower() in color_map:
            return color_map[color_str.lower()]
        else:
            raise ValueError(f"不支持的颜色: {color_str}")

def main():
    parser = argparse.ArgumentParser(description="给图片添加基于EXIF日期的时间水印")
    parser.add_argument("input_path", help="图片文件或目录路径")
    parser.add_argument("-s", "--size", type=int, default=20, help="字体大小，默认20")
    parser.add_argument("-c", "--color", default="white", help="字体颜色，支持颜色名称或#RRGGBB格式，默认白色")
    parser.add_argument("-p", "--position", default="bottom-right", 
                        choices=["top-left", "top-right", "bottom-left", "bottom-right", "center"],
                        help="水印位置，默认右下角")
    
    args = parser.parse_args()
    
    try:
        color = parse_color(args.color)
        process_images(args.input_path, args.size, color, args.position)
    except ValueError as e:
        print(f"参数错误: {e}")
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()