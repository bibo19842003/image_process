#!/usr/bin/env python3
"""
图片处理工具启动脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from image_processor import main

if __name__ == "__main__":
    print("启动图片处理工具...")
    main()