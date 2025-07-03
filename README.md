# PsdConvert

一个用于批量转换 PSD 文件格式的工具。

## 功能

*   将 PSD 文件转换为其他常见的图片格式。
*   支持转换 PDF 文件为图片。
*   支持转换 CLIP 文件为图片（通过先转换为PSD）。
*   支持递归解压所有压缩文件。
*   多进程加速处理，提高转换效率。
*   智能内存管理，根据系统资源自动调整进程数。

## 多进程功能

为了提高处理效率，PsdConvert 支持多进程加速功能：

*   可以为不同类型的文件（PSD、PDF、CLIP）配置不同的进程数。
*   智能内存监控，根据系统资源使用情况动态调整进程数。
*   支持通过命令行参数或配置文件调整多进程行为。

### 相关命令行参数

```
--disable-multiprocessing    禁用多进程处理，使用单进程模式
--max-processes NUM          指定最大进程数，适用于所有处理类型
--max-psd-processes NUM      指定PSD处理的最大进程数
--max-pdf-processes NUM      指定PDF处理的最大进程数
--max-clip-processes NUM     指定CLIP处理的最大进程数
--disable-auto-adjust        禁用自动调整进程数，始终使用指定的最大进程数
```

### 配置文件设置

在配置文件中可以设置多进程相关选项：

```json
{
  "multiprocessing": {
    "enabled": true,
    "auto_adjust": true,
    "max_processes": {
      "psd": 8,
      "pdf": 4,
      "clip": 4
    }
  }
}
```

## 使用示例

基本使用：
```
python -m psdconvert
```

使用8个进程处理所有文件类型：
```
python -m psdconvert --max-processes 8
```

对PSD文件使用更多进程，对PDF和CLIP使用较少进程：
```
python -m psdconvert --max-psd-processes 12 --max-pdf-processes 4 --max-clip-processes 2
```

禁用多进程处理：
```
python -m psdconvert --disable-multiprocessing
```