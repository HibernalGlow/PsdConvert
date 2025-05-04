import os
import subprocess
from pathlib import Path
import logging
# 在调用7-Zip命令前设置环境变量
os.environ['TMP'] = 'D:/temp'
os.environ['TEMP'] = 'D:/temp'
# 支持的压缩包格式
ARCHIVE_EXTENSIONS = ['.zip', '.7z', '.rar', '.cbz']

# 在文件顶部添加这个变量定义
TARGET_FORMATS = ['.psd', '.pdf', '.clip']

def extract_all_archives_recursive(directory, depth=0, max_depth=5, delete_original=True, target_formats=None):
    """递归解压指定目录下的所有压缩文件
    
    参数:
    directory -- 要处理的目录
    depth -- 当前递归深度
    max_depth -- 最大递归深度，防止无限递归
    delete_original -- 是否删除原始压缩文件
    target_formats -- 目标格式列表，用于检查压缩包内容是否包含这些格式
    """
    if depth >= max_depth:
        print(f"警告: 达到最大递归深度 {max_depth}，停止递归解压")
        return
    
    if target_formats is None:
        target_formats = ['.psd', '.pdf', '.clip']
    
    extracted_dirs = []
    
    # 第一遍：解压所有压缩文件
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS):
                archive_path = os.path.join(root, file)
                
                # 先检查是否包含其他压缩文件
                contains_archives = check_archive_content(archive_path, tuple(ARCHIVE_EXTENSIONS))
                
                # 情况1：如果包含压缩文件，直接解压并递归处理
                if contains_archives:
                    print(f"压缩包 {archive_path} 包含嵌套压缩文件，执行解压")
                    extract_path = extract_archive(archive_path, delete_original=delete_original)
                    if extract_path:
                        extracted_dirs.append(extract_path)
                        print(f"成功解压: {archive_path} 到 {extract_path}")
                else:
                    # 情况2：如果不包含压缩文件，检查是否包含目标格式文件
                    contains_target_formats = check_archive_content(archive_path, tuple(target_formats))
                    
                    if contains_target_formats:
                        print(f"压缩包 {archive_path} 包含目标格式文件，执行解压")
                        extract_path = extract_archive(archive_path, delete_original=delete_original)
                        if extract_path:
                            extracted_dirs.append(extract_path)
                            print(f"成功解压: {archive_path} 到 {extract_path}")
                    else:
                        print(f"压缩包 {archive_path} 既不包含压缩文件也不包含目标格式文件，跳过")
    
    # 第二遍：递归处理刚刚解压出的目录中的压缩文件
    for extracted_dir in extracted_dirs:
        print(f"递归检查解压目录: {extracted_dir} (深度: {depth+1})")
        extract_all_archives_recursive(extracted_dir, depth+1, max_depth, delete_original, target_formats)

# 修复check_archive_content函数，增加对None结果的处理
def check_archive_content(archive_path, extensions):
    """检查压缩包内是否包含指定扩展名的文件，统一使用7z
    
    参数:
    archive_path -- 压缩包路径
    extensions -- 要查找的扩展名元组
    
    返回:
    bool -- 是否包含指定扩展名的文件
    """
    try:
        archive_path = Path(archive_path)
        
        # 统一使用7z检查压缩包内容
        cmd = [
            '7z', 'l',
            str(archive_path),
            '-slt',
        ]
        
        result = _run_subprocess_with_encoding(cmd)
        
        if result is None:
            logging.error(f"检查压缩包内容失败: {archive_path}")
            return False
            
        # 检查输出中是否包含指定扩展名的文件
        found_files = []
        
        # 按行分析输出
        for line in result.split('\n'):
            line = line.strip().lower()
            if line.startswith('path = ') or line.startswith('name = '):
                file_path = line.split(' = ', 1)[1] if ' = ' in line else ""
                if any(file_path.lower().endswith(ext.lower()) for ext in extensions):
                    ext = os.path.splitext(file_path)[1]
                    found_files.append((file_path, ext))
        
        if found_files:
            # 打印找到的文件和扩展名，便于调试
            logging.info(f"在压缩包 {archive_path.name} 中找到以下文件:")
            for file_path, ext in found_files[:5]:  # 最多显示5个
                logging.info(f"  - {file_path} ({ext})")
            if len(found_files) > 5:
                logging.info(f"  ... 以及其他 {len(found_files)-5} 个文件")
            return True
        
        logging.info(f"压缩包 {archive_path.name} 中未找到指定扩展名的文件")
        return False
                
    except Exception as e:
        logging.error(f"检查压缩包内容时出错 {archive_path}: {e}")
        return False

# 修复_run_subprocess_with_encoding函数，增强编码处理能力
def _run_subprocess_with_encoding(cmd, encoding_list=['utf-8', 'cp932', 'gbk', 'shift-jis', 'cp1252']):
    """
    运行子进程并处理多种可能的编码
    
    参数:
    cmd -- 要执行的命令
    encoding_list -- 尝试的编码列表
    """
    # 首先尝试二进制模式运行
    try:
        result = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 如果命令执行失败
        if result.returncode != 0:
            logging.error(f"子进程执行失败，返回码：{result.returncode}")
            logging.error(f"命令: {' '.join(cmd)}")
            return None
            
        # 尝试不同的编码解码输出
        for encoding in encoding_list:
            try:
                output = result.stdout.decode(encoding, errors='replace')
                return output
            except UnicodeDecodeError:
                continue
                
        # 所有编码都失败了，使用'replace'策略强制解码
        logging.warning("所有尝试的编码都失败，使用replace策略解码")
        return result.stdout.decode('utf-8', errors='replace')
        
    except Exception as e:
        logging.error(f"执行子进程时发生错误: {e}")
        return None

def extract_archive(archive_path, delete_original=True):
    """解压缩文件并返回解压目录路径
    
    参数:
    archive_path -- 压缩包路径
    delete_original -- 是否删除原始压缩文件，默认为True
    
    返回:
    str -- 解压目录路径，解压失败则返回None
    """
    try:
        archive_path = Path(archive_path)
        dir_path = archive_path.parent
        file_name = archive_path.stem
        extract_path = dir_path / file_name
        
        # 创建解压目标文件夹
        os.makedirs(extract_path, exist_ok=True)

        # 统一使用7z进行解压
        cmd = [
            '7z', 'x',
            str(archive_path),
            f'-o{str(extract_path)}',
            '-scsUTF-8',
            '-aoa',  # 覆盖已存在的文件
            '-y'     # 自动回答yes
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"7z解压失败: {result.stderr}")
            return None
            
        # 解压成功后，根据参数决定是否删除原压缩文件
        if delete_original:
            os.remove(archive_path)
            print(f"已解压并删除: {archive_path}")
        else:
            print(f"已解压: {archive_path}")
            
        return extract_path
            
    except Exception as e:
        print(f"处理文件时出错 {archive_path}: {e}")
        return None

# 在子进程调用部分添加错误处理
def _run_subprocess_with_encoding(cmd, encoding_list=['utf-8', 'gbk', 'shift-jis', 'cp1252']):
    """
    运行子进程并处理多种可能的编码
    
    参数:
    cmd -- 要执行的命令
    encoding_list -- 尝试的编码列表
    """
    try:
        # 使用errors='replace'来替代无法解码的字符
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              encoding='utf-8', errors='replace')
        return result.stdout
    except subprocess.CalledProcessError as e:
        # 处理命令执行失败的情况
        logging.error(f"子进程执行失败: {e}")
        if e.stdout:
            logging.error(f"标准输出: {e.stdout}")
        if e.stderr:
            logging.error(f"错误输出: {e.stderr}")
        return None
    except UnicodeDecodeError:
        # 如果utf-8解码失败，尝试其他编码
        for encoding in encoding_list[1:]:
            try:
                result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      encoding=encoding)
                return result.stdout
            except (UnicodeDecodeError, subprocess.CalledProcessError):
                continue
        # 所有编码都失败了，使用二进制模式并忽略编码错误
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            return result.stdout.decode('utf-8', errors='replace')
        except:
            logging.error(f"无法解码子进程输出")
            return None

# 修改压缩文件检查函数，添加None检查
def extract_archive(archive_path, output_dir=None, delete_original=False, target_formats=None):
    """
    提取压缩文件到指定目录
    
    参数:
    archive_path -- 压缩文件路径
    output_dir -- 输出目录，默认为与压缩文件相同的目录
    delete_original -- 是否删除原始压缩文件
    target_formats -- 目标文件格式列表
    
    返回:
    Path/str -- 解压目录路径，解压失败则返回None
    """
    try:
        archive_path = Path(archive_path)
        
        # 如果没有提供输出目录，则使用压缩文件所在目录/文件名作为输出目录
        if output_dir is None:
            dir_path = archive_path.parent
            file_name = archive_path.stem
            extract_path = dir_path / file_name
        else:
            extract_path = Path(output_dir)
        
        # 添加空值检查
        if target_formats is None:
            target_formats = TARGET_FORMATS
        
        # 创建解压目标文件夹
        os.makedirs(extract_path, exist_ok=True)

        # 统一使用7z进行解压
        cmd = [
            '7z', 'x',
            str(archive_path),
            f'-o{str(extract_path)}',
            '-scsUTF-8',
            '-aoa',  # 覆盖已存在的文件
            '-y'     # 自动回答yes
        ]
        
        result = _run_subprocess_with_encoding(cmd)
        
        if result is None:
            logging.error(f"解压失败: {archive_path}")
            return None
            
        # 解压成功后，根据参数决定是否删除原压缩文件
        if delete_original:
            os.remove(archive_path)
            logging.info(f"已解压并删除: {archive_path}")
        else:
            logging.info(f"已解压: {archive_path}")
            
        return extract_path
            
    except Exception as e:
        logging.error(f"处理文件时出错 {archive_path}: {e}")
        return None
