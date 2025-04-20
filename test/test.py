
from PIL import Image, ImageDraw, ImageFont
 
# 打开Clip文件
clip_file = r"E:\1EHV\[丸鳥の茶漬け (鳥茶丸)]\4. 画集\[#a]FANBOX 作品集 [kemono 截止 2023.11.29 标注发布时间 & 作品名称依次排序][丸鳥の茶漬け (鳥茶丸)]\[2020-02-16] [支援者さん向け] C97 原稿データ 3 ページ分配布\2020-02-16-[支援者さん向け] C97 原稿データ 3 ページ分配布 - page0005\page0006.clip"
clip_image = Image.open(clip_file)
 
# 转换为JPEG格式
# clip_image.save('output_image.jpg', 'JPEG')
 
# 保存结果到本地文件
clip_image.save('output_image.png', 'PNG')