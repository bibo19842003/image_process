import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QSlider, QFileDialog,
                            QGroupBox, QFrame, QGridLayout, QCheckBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QIcon
import cv2
import numpy as np


class ResizableImageLabel(QLabel):
    """支持图片大小自动调整的QLabel"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setMinimumSize(300, 300)
        self.current_image = None
        self.current_pixmap = None
    
    def resizeEvent(self, event):
        """窗口大小变化时重新调整图片大小"""
        super().resizeEvent(event)
        if self.current_image is not None and self.current_pixmap is not None:
            # 重新调整图片大小以适应新的标签大小
            # 获取标签的当前可用尺寸（考虑布局和边距）
            label_width = self.width() - 20  # 减去边距
            label_height = self.height() - 20  # 减去边距
            
            # 确保最小显示尺寸
            display_width = max(label_width, 200)
            display_height = max(label_height, 200)
            
            # 获取原始图片尺寸
            h, w = self.current_image.shape[:2]
            
            # 计算缩放比例，尽量填满显示区域
            width_ratio = display_width / w
            height_ratio = display_height / h
            
            # 选择较小的缩放比例，确保图片完全显示
            scale_ratio = min(width_ratio, height_ratio)
            
            # 计算最终显示尺寸
            final_width = int(w * scale_ratio)
            final_height = int(h * scale_ratio)
            
            # 直接缩放当前pixmap，避免重新创建QImage
            scaled_pixmap = self.current_pixmap.scaled(final_width, final_height, 
                                                    Qt.AspectRatioMode.KeepAspectRatio, 
                                                    Qt.TransformationMode.SmoothTransformation)
            
            self.setPixmap(scaled_pixmap)


class DragDropLabel(ResizableImageLabel):
    """支持拖拽功能的QLabel"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查文件是否为图片格式
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if self.is_image_file(file_path):
                    event.acceptProposedAction()
                    self.setText("释放图片文件")
                    # 使用CSS属性来设置拖拽状态，避免直接调用unpolish/polish
                    self.setProperty("dragEnter", "true")
                    # 使用update()而不是unpolish/polish来触发重绘
                    self.update()
                else:
                    event.ignore()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self.setText("原始图片")
        # 清除拖拽状态属性
        self.setProperty("dragEnter", "false")
        # 使用update()而不是unpolish/polish来触发重绘
        self.update()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        """释放拖拽文件事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if self.is_image_file(file_path):
                    # 通知主窗口加载图片 - 通过窗口层次结构找到ImageProcessor实例
                    main_window = self.window()
                    if hasattr(main_window, 'load_image_from_path'):
                        main_window.load_image_from_path(file_path)
                    event.acceptProposedAction()
                else:
                    event.ignore()
        
        # 恢复样式，但不设置文字（图片显示会清除文字）
        # 清除拖拽状态属性
        self.setProperty("dragEnter", "false")
        # 使用update()而不是unpolish/polish来触发重绘
        self.update()
    
    def is_image_file(self, file_path):
        """检查文件是否为支持的图片格式"""
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp']
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in image_extensions


class ImageProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.original_image = None
        self.processed_image = None
        self.original_image_path = None  # 存储原始图片文件路径
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("图片处理工具 - V1.3")
        self.setGeometry(100, 100, 1200, 1000)
        
        # 设置窗口图标（标题栏logo）
        if os.path.exists("logo.png"):
            self.setWindowIcon(QIcon("logo.png"))
        
        # 设置简洁的配色方案，避免复杂的渐变效果以减少QPainter错误
        self.setStyleSheet("""
            QMainWindow {
                background: #f8fafc;
                color: #1e293b;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 13px;
                color: #475569;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: rgba(255, 255, 255, 0.9);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 4px 16px;
                background: #6366f1;
                color: white;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QPushButton {
                background: #6366f1;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                min-height: 32px;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background: #818cf8;
            }
            QPushButton:pressed {
                background: #4f46e5;
            }
            QPushButton:disabled {
                background: #cbd5e1;
                color: #64748b;
            }
            QLabel {
                color: #475569;
                font-size: 13px;
                font-weight: 500;
            }
            QCheckBox {
                spacing: 8px;
                font-size: 13px;
                color: #475569;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border: 2px solid #cbd5e1;
                border-radius: 4px;
                background: white;
            }
            QCheckBox::indicator:checked {
                background: #6366f1;
                border: 2px solid #6366f1;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #94a3b8;
            }
            QCheckBox::indicator:checked:hover {
                border: 2px solid #818cf8;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #e2e8f0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #6366f1;
                border: 2px solid white;
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 50%;
            }
            QSlider::handle:horizontal:hover {
                background: #818cf8;
            }
            QSlider::handle:horizontal:pressed {
                background: #4f46e5;
            }
            QSlider::sub-page:horizontal {
                background: #6366f1;
                border-radius: 2px;
            }
            /* 图片显示区域特殊样式 */
            ResizableImageLabel, DragDropLabel {
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                background: #f8fafc;
                color: #94a3b8;
                font-size: 14px;
                font-weight: 600;
                font-style: italic;
            }
            DragDropLabel[dragEnter="true"] {
                background: #e0e7ff;
                border: 2px dashed #6366f1;
                color: #6366f1;
            }
        """)
        
        # 创建中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 - 垂直布局，分为上下两个大区域
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 上面的大区域 - 水平布局，分为左右两个相等的区域
        top_layout = QHBoxLayout()
        
        # 左侧区域 - 图片选择和显示
        left_frame = self.create_image_selection_frame()
        top_layout.addWidget(left_frame, 1)
        
        # 右侧区域 - 结果显示
        right_frame = self.create_result_frame()
        top_layout.addWidget(right_frame, 1)
        
        # 将上面的大区域添加到主布局
        top_widget = QWidget()
        top_widget.setLayout(top_layout)
        main_layout.addWidget(top_widget, 3)  # 上面区域占3/4高度
        
        # 下面的大区域 - 参数调节
        # 创建一个容器来确保参数调节区域与上面两个区域对齐
        bottom_container = QWidget()
        bottom_container_layout = QHBoxLayout()
        # bottom_container_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        bottom_frame = self.create_parameter_frame()
        bottom_container_layout.addWidget(bottom_frame)
        
        bottom_container.setLayout(bottom_container_layout)
        main_layout.addWidget(bottom_container, 1)  # 下面区域占1/4高度
        
    def create_image_selection_frame(self):
        frame = QGroupBox("图片选择及显示")
        layout = QVBoxLayout()
        
        # 选择图片按钮
        self.select_button = QPushButton("选择图片")
        self.select_button.clicked.connect(self.select_image)
        layout.addWidget(self.select_button)
        
        # 原始图片显示（支持拖拽）
        self.original_label = DragDropLabel("原始图片")
        self.original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_label.setFrameStyle(QFrame.Shape.Box)
        self.original_label.setMinimumSize(300, 300)
        layout.addWidget(self.original_label)
        
        frame.setLayout(layout)
        return frame
    
    def create_parameter_frame(self):
        frame = QGroupBox("参数调节")
        layout = QHBoxLayout()
        layout.setSpacing(7)  # 设置列间距（从15减小到7）
        
        # 第一列：基础调节功能（15%宽度）
        basic_column = QVBoxLayout()
        basic_column.setSpacing(50)  # 设置控件间距
        
        # 对比增强滑块
        contrast_group = QGroupBox("对比增强")
        contrast_layout = QVBoxLayout()
        contrast_layout.setSpacing(5)
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(0, 200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.update_processed_image)
        contrast_layout.addWidget(QLabel("对比度: 100%"))
        contrast_layout.addWidget(self.contrast_slider)
        contrast_group.setLayout(contrast_layout)
        basic_column.addWidget(contrast_group)
        
        # 亮度调节滑块
        brightness_group = QGroupBox("亮度调节")
        brightness_layout = QVBoxLayout()
        brightness_layout.setSpacing(5)
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(self.update_processed_image)
        brightness_layout.addWidget(QLabel("亮度: 0"))
        brightness_layout.addWidget(self.brightness_slider)
        brightness_group.setLayout(brightness_layout)
        basic_column.addWidget(brightness_group)
        
        # 清晰度调节滑块
        sharpness_group = QGroupBox("清晰度调节")
        sharpness_layout = QVBoxLayout()
        sharpness_layout.setSpacing(5)
        self.sharpness_slider = QSlider(Qt.Orientation.Horizontal)
        self.sharpness_slider.setRange(0, 100)
        self.sharpness_slider.setValue(0)
        self.sharpness_slider.valueChanged.connect(self.update_processed_image)
        sharpness_layout.addWidget(QLabel("清晰度: 0"))
        sharpness_layout.addWidget(self.sharpness_slider)
        sharpness_group.setLayout(sharpness_layout)
        basic_column.addWidget(sharpness_group)
        
        # 添加弹性空间使控件垂直居中
        basic_column.addStretch()
        
        # 将第一列添加到主布局
        basic_widget = QWidget()
        basic_widget.setLayout(basic_column)
        layout.addWidget(basic_widget, 15)  # 15%宽度
        
        # 第二列：画面效果功能（15%宽度）
        effect_column = QVBoxLayout()
        effect_column.setSpacing(50)  # 设置控件间距
        
        # 画面柔和滑块
        blur_group = QGroupBox("画面柔和")
        blur_layout = QVBoxLayout()
        blur_layout.setSpacing(5)
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(0, 20)
        self.blur_slider.setValue(0)
        self.blur_slider.valueChanged.connect(self.update_processed_image)
        blur_layout.addWidget(QLabel("柔和程度: 0"))
        blur_layout.addWidget(self.blur_slider)
        blur_group.setLayout(blur_layout)
        effect_column.addWidget(blur_group)
        
        # 图片旋转滑块
        rotate_group = QGroupBox("图片旋转")
        rotate_layout = QVBoxLayout()
        rotate_layout.setSpacing(5)
        self.rotate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rotate_slider.setRange(-180, 180)
        self.rotate_slider.setValue(0)
        self.rotate_slider.valueChanged.connect(self.update_processed_image)
        rotate_layout.addWidget(QLabel("旋转角度: 0°"))
        rotate_layout.addWidget(self.rotate_slider)
        rotate_group.setLayout(rotate_layout)
        effect_column.addWidget(rotate_group)
        
        # 消除摩尔纹开关
        moire_group = QGroupBox("消除摩尔纹")
        moire_layout = QVBoxLayout()
        moire_layout.setSpacing(5)
        moire_switch_layout = QHBoxLayout()
        moire_switch_layout.setSpacing(5)
        moire_switch_layout.addWidget(QLabel("摩尔纹开关:"))
        self.moire_switch = QCheckBox()
        self.moire_switch.setChecked(False)
        self.moire_switch.stateChanged.connect(self.update_processed_image)
        self.moire_switch.setFixedSize(24, 24)  # 设置固定大小确保显示完整
        moire_switch_layout.addWidget(self.moire_switch)
        moire_switch_layout.addStretch()
        moire_layout.addLayout(moire_switch_layout)
        moire_group.setLayout(moire_layout)
        effect_column.addWidget(moire_group)

        # 添加弹性空间使控件垂直居中
        effect_column.addStretch()
        
        # 将第二列添加到主布局
        effect_widget = QWidget()
        effect_widget.setLayout(effect_column)
        layout.addWidget(effect_widget, 15)  # 15%宽度
        
        # 第三列：裁剪功能（25%宽度）
        crop_column = QVBoxLayout()
        crop_column.setSpacing(10)  # 设置控件间距
        
        # 裁剪控制
        crop_group = QGroupBox("裁剪功能")
        crop_layout = QVBoxLayout()
        crop_layout.setSpacing(53)
        
        # 裁剪开关
        crop_switch_layout = QHBoxLayout()
        crop_switch_layout.setSpacing(5)
        crop_switch_layout.addWidget(QLabel("裁剪开关:"))
        self.crop_switch = QCheckBox()
        self.crop_switch.setChecked(False)
        self.crop_switch.stateChanged.connect(self.update_processed_image)
        self.crop_switch.setFixedSize(24, 24)  # 设置固定大小确保显示完整
        crop_switch_layout.addWidget(self.crop_switch)
        crop_switch_layout.addStretch()
        crop_layout.addLayout(crop_switch_layout)
        
        # 裁剪参数
        crop_params_layout = QGridLayout()
        crop_params_layout.setSpacing(5)
        
        # 左上角坐标
        crop_params_layout.addWidget(QLabel("左上角X:"), 0, 0)
        self.crop_left_slider = QSlider(Qt.Orientation.Horizontal)
        self.crop_left_slider.setRange(0, 100)
        self.crop_left_slider.setValue(0)
        self.crop_left_slider.valueChanged.connect(self.update_processed_image)
        crop_params_layout.addWidget(self.crop_left_slider, 0, 1)
        self.crop_left_label = QLabel("0%")
        crop_params_layout.addWidget(self.crop_left_label, 0, 2)
        
        crop_params_layout.addWidget(QLabel("左上角Y:"), 1, 0)
        self.crop_top_slider = QSlider(Qt.Orientation.Horizontal)
        self.crop_top_slider.setRange(0, 100)
        self.crop_top_slider.setValue(0)
        self.crop_top_slider.valueChanged.connect(self.update_processed_image)
        crop_params_layout.addWidget(self.crop_top_slider, 1, 1)
        self.crop_top_label = QLabel("0%")
        crop_params_layout.addWidget(self.crop_top_label, 1, 2)
        
        # 右下角坐标
        crop_params_layout.addWidget(QLabel("右下角X:"), 2, 0)
        self.crop_right_slider = QSlider(Qt.Orientation.Horizontal)
        self.crop_right_slider.setRange(0, 100)
        self.crop_right_slider.setValue(100)
        self.crop_right_slider.valueChanged.connect(self.update_processed_image)
        crop_params_layout.addWidget(self.crop_right_slider, 2, 1)
        self.crop_right_label = QLabel("100%")
        crop_params_layout.addWidget(self.crop_right_label, 2, 2)
        
        crop_params_layout.addWidget(QLabel("右下角Y:"), 3, 0)
        self.crop_bottom_slider = QSlider(Qt.Orientation.Horizontal)
        self.crop_bottom_slider.setRange(0, 100)
        self.crop_bottom_slider.setValue(100)
        self.crop_bottom_slider.valueChanged.connect(self.update_processed_image)
        crop_params_layout.addWidget(self.crop_bottom_slider, 3, 1)
        self.crop_bottom_label = QLabel("100%")
        crop_params_layout.addWidget(self.crop_bottom_label, 3, 2)
        
        crop_layout.addLayout(crop_params_layout)
        crop_group.setLayout(crop_layout)
        crop_column.addWidget(crop_group)
        
        # 添加弹性空间使控件垂直居中
        crop_column.addStretch()
        
        # 将第三列添加到主布局
        crop_widget = QWidget()
        crop_widget.setLayout(crop_column)
        layout.addWidget(crop_widget, 25)  # 25%宽度
        
        # 第四列：四点变换功能（25%宽度）
        perspective_column = QVBoxLayout()
        perspective_column.setSpacing(10)  # 设置控件间距
        
        # 四点变换控制
        perspective_group = QGroupBox("四点变换")
        perspective_layout = QVBoxLayout()
        perspective_layout.setSpacing(8)
        
        # 四点变换开关
        switch_layout = QHBoxLayout()
        switch_layout.setSpacing(5)
        switch_layout.addWidget(QLabel("四点变换开关:"))
        self.perspective_switch = QCheckBox()
        self.perspective_switch.setChecked(False)
        self.perspective_switch.stateChanged.connect(self.update_processed_image)
        self.perspective_switch.setFixedSize(24, 24)  # 设置固定大小确保显示完整
        switch_layout.addWidget(self.perspective_switch)
        switch_layout.addStretch()
        perspective_layout.addLayout(switch_layout)
        
        # 四个角点的控制滑块
        corners_layout = QGridLayout()
        corners_layout.setSpacing(8)
        
        # 左上角
        top_left_group = QGroupBox("左上角")
        top_left_layout = QVBoxLayout()
        top_left_layout.setSpacing(5)
        self.top_left_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.top_left_x_slider.setRange(-100, 100)
        self.top_left_x_slider.setValue(0)
        self.top_left_x_slider.valueChanged.connect(self.update_processed_image)
        self.top_left_x_label = QLabel("X偏移: 0%")
        top_left_layout.addWidget(self.top_left_x_label)
        top_left_layout.addWidget(self.top_left_x_slider)
        
        self.top_left_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.top_left_y_slider.setRange(-100, 100)
        self.top_left_y_slider.setValue(0)
        self.top_left_y_slider.valueChanged.connect(self.update_processed_image)
        self.top_left_y_label = QLabel("Y偏移: 0%")
        top_left_layout.addWidget(self.top_left_y_label)
        top_left_layout.addWidget(self.top_left_y_slider)
        top_left_group.setLayout(top_left_layout)
        corners_layout.addWidget(top_left_group, 0, 0)
        
        # 右上角
        top_right_group = QGroupBox("右上角")
        top_right_layout = QVBoxLayout()
        top_right_layout.setSpacing(5)
        self.top_right_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.top_right_x_slider.setRange(-100, 100)
        self.top_right_x_slider.setValue(0)
        self.top_right_x_slider.valueChanged.connect(self.update_processed_image)
        self.top_right_x_label = QLabel("X偏移: 0%")
        top_right_layout.addWidget(self.top_right_x_label)
        top_right_layout.addWidget(self.top_right_x_slider)
        
        self.top_right_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.top_right_y_slider.setRange(-100, 100)
        self.top_right_y_slider.setValue(0)
        self.top_right_y_slider.valueChanged.connect(self.update_processed_image)
        self.top_right_y_label = QLabel("Y偏移: 0%")
        top_right_layout.addWidget(self.top_right_y_label)
        top_right_layout.addWidget(self.top_right_y_slider)
        top_right_group.setLayout(top_right_layout)
        corners_layout.addWidget(top_right_group, 0, 1)
        
        # 左下角
        bottom_left_group = QGroupBox("左下角")
        bottom_left_layout = QVBoxLayout()
        bottom_left_layout.setSpacing(5)
        self.bottom_left_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.bottom_left_x_slider.setRange(-100, 100)
        self.bottom_left_x_slider.setValue(0)
        self.bottom_left_x_slider.valueChanged.connect(self.update_processed_image)
        self.bottom_left_x_label = QLabel("X偏移: 0%")
        bottom_left_layout.addWidget(self.bottom_left_x_label)
        bottom_left_layout.addWidget(self.bottom_left_x_slider)
        
        self.bottom_left_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.bottom_left_y_slider.setRange(-100, 100)
        self.bottom_left_y_slider.setValue(0)
        self.bottom_left_y_slider.valueChanged.connect(self.update_processed_image)
        self.bottom_left_y_label = QLabel("Y偏移: 0%")
        bottom_left_layout.addWidget(self.bottom_left_y_label)
        bottom_left_layout.addWidget(self.bottom_left_y_slider)
        bottom_left_group.setLayout(bottom_left_layout)
        corners_layout.addWidget(bottom_left_group, 1, 0)
        
        # 右下角
        bottom_right_group = QGroupBox("右下角")
        bottom_right_layout = QVBoxLayout()
        bottom_right_layout.setSpacing(5)
        self.bottom_right_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.bottom_right_x_slider.setRange(-100, 100)
        self.bottom_right_x_slider.setValue(0)
        self.bottom_right_x_slider.valueChanged.connect(self.update_processed_image)
        self.bottom_right_x_label = QLabel("X偏移: 0%")
        bottom_right_layout.addWidget(self.bottom_right_x_label)
        bottom_right_layout.addWidget(self.bottom_right_x_slider)
        
        self.bottom_right_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.bottom_right_y_slider.setRange(-100, 100)
        self.bottom_right_y_slider.setValue(0)
        self.bottom_right_y_slider.valueChanged.connect(self.update_processed_image)
        self.bottom_right_y_label = QLabel("Y偏移: 0%")
        bottom_right_layout.addWidget(self.bottom_right_y_label)
        bottom_right_layout.addWidget(self.bottom_right_y_slider)
        bottom_right_group.setLayout(bottom_right_layout)
        corners_layout.addWidget(bottom_right_group, 1, 1)
        
        perspective_layout.addLayout(corners_layout)
        perspective_group.setLayout(perspective_layout)
        perspective_column.addWidget(perspective_group)
        
        # 添加弹性空间使控件垂直居中
        perspective_column.addStretch()
        
        # 将第四列添加到主布局
        perspective_widget = QWidget()
        perspective_widget.setLayout(perspective_column)
        layout.addWidget(perspective_widget, 35)  # 35%宽度
        
        # 第五列：操作按钮（20%宽度）
        button_column = QVBoxLayout()
        button_column.setSpacing(10)  # 设置控件间距
        
        # 重置按钮 - 简化布局实现完美垂直居中
        button_layout = QVBoxLayout()
        button_layout.addStretch()  # 在按钮上方添加弹性空间
        self.reset_button = QPushButton("重置参数")
        self.reset_button.clicked.connect(self.reset_parameters)
        self.reset_button.setFixedSize(120, 40)  # 设置按钮固定大小
        button_layout.addWidget(self.reset_button, 0, Qt.AlignmentFlag.AlignCenter)  # 水平居中
        button_layout.addStretch()  # 在按钮下方添加弹性空间
        
        # 直接将按钮布局添加到列布局
        button_column.addLayout(button_layout)
        
        # 将第五列添加到主布局
        button_column_widget = QWidget()
        button_column_widget.setLayout(button_column)
        layout.addWidget(button_column_widget, 10)  # 10%宽度
        
        # 设置参数调节区域的宽度与上面两个区域的总宽度一致
        frame.setMinimumWidth(600)  # 设置最小宽度
        frame.setLayout(layout)
        return frame
    
    def create_result_frame(self):
        frame = QGroupBox("图片结果显示")
        layout = QVBoxLayout()

        # 保存按钮
        self.save_button = QPushButton("保存图片")
        self.save_button.clicked.connect(self.save_image)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)

        self.result_label = ResizableImageLabel("处理结果")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setFrameStyle(QFrame.Shape.Box)
        self.result_label.setMinimumSize(300, 300)
        layout.addWidget(self.result_label)
        
        frame.setLayout(layout)
        return frame
    
    def load_image_from_path(self, file_path):
        """从文件路径加载图片（供拖拽功能使用）"""
        if file_path:
            # 保存原始图片文件路径
            self.original_image_path = file_path
            
            # 使用numpy从文件读取图片，解决中文路径问题
            #try:
            if 1:
                # 方法1: 使用numpy从文件读取
                with open(file_path, 'rb') as f:
                    img_array = np.frombuffer(f.read(), dtype=np.uint8)
                    self.original_image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                # 如果方法1失败，尝试方法2: 使用绝对路径
                if self.original_image is None:
                    # 将路径转换为绝对路径并确保使用正确的编码
                    abs_path = os.path.abspath(file_path)
                    self.original_image = cv2.imread(abs_path)
                
                # 如果仍然失败，尝试方法3: 使用Unicode路径
                if self.original_image is None:
                    # 使用Unicode编码处理路径
                    unicode_path = file_path.encode('utf-8').decode('utf-8')
                    self.original_image = cv2.imread(unicode_path)
                
                if self.original_image is not None:
                    # 显示原始图片
                    self.display_image(self.original_image, self.original_label)
                    self.original_image_old = self.original_image.copy()
                    # 初始化处理后的图片
                    #self.processed_image = self.original_image.copy()

                    # 将图片转换为灰度图
                    self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)

                    binary = cv2.adaptiveThreshold(self.original_image,255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,25,15)
                    se = cv2.getStructuringElement(cv2.MORPH_RECT,(1,1))
                    se = cv2.morphologyEx(se, cv2.MORPH_CLOSE, (2,2))
                    mask = cv2.dilate(binary,se)
                    mask1 = cv2.bitwise_not(mask)
                    binary =cv2.bitwise_and(self.original_image,mask)
                    self.original_image = cv2.add(binary,mask1)

                    self.processed_image = self.original_image.copy()

                    self.display_image(self.processed_image, self.result_label)
                    self.save_button.setEnabled(True)
                    # 重置参数
                    #self.reset_parameters()
                else:
                    self.show_error_message("无法加载图片，请检查文件路径和格式")
                    
            #except Exception as e:
                #self.show_error_message(f"加载图片时发生错误: {str(e)}")
    
    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        
        # 使用统一的图片加载方法
        self.load_image_from_path(file_path)
    
    def show_error_message(self, message):
        """显示错误消息"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "错误", message)
    
    def update_processed_image(self):
        if self.original_image is None:
            return
        
        # 获取滑块值
        contrast_value = self.contrast_slider.value() / 100.0
        brightness_value = self.brightness_slider.value()
        sharpness_value = self.sharpness_slider.value() / 100.0
        blur_value = self.blur_slider.value()
        rotate_value = self.rotate_slider.value()
        
        # 获取四点变换参数
        top_left_x = self.top_left_x_slider.value() / 100.0
        top_left_y = self.top_left_y_slider.value() / 100.0
        top_right_x = self.top_right_x_slider.value() / 100.0
        top_right_y = self.top_right_y_slider.value() / 100.0
        bottom_left_x = self.bottom_left_x_slider.value() / 100.0
        bottom_left_y = self.bottom_left_y_slider.value() / 100.0
        bottom_right_x = self.bottom_right_x_slider.value() / 100.0
        bottom_right_y = self.bottom_right_y_slider.value() / 100.0
        
        # 获取裁剪参数
        crop_left = self.crop_left_slider.value() / 100.0
        crop_top = self.crop_top_slider.value() / 100.0
        crop_right = self.crop_right_slider.value() / 100.0
        crop_bottom = self.crop_bottom_slider.value() / 100.0
        
        # 更新滑块标签
        self.contrast_slider.parent().findChild(QLabel).setText(f"对比度: {contrast_value*100:.0f}%")
        self.brightness_slider.parent().findChild(QLabel).setText(f"亮度: {brightness_value}")
        self.sharpness_slider.parent().findChild(QLabel).setText(f"清晰度: {sharpness_value*100:.0f}%")
        self.blur_slider.parent().findChild(QLabel).setText(f"柔和程度: {blur_value}")
        self.rotate_slider.parent().findChild(QLabel).setText(f"旋转角度: {rotate_value}°")
        
        # 更新四点变换标签
        self.top_left_x_label.setText(f"X偏移: {top_left_x*100:.2f}%")
        self.top_left_y_label.setText(f"Y偏移: {top_left_y*100:.2f}%")
        self.top_right_x_label.setText(f"X偏移: {top_right_x*100:.2f}%")
        self.top_right_y_label.setText(f"Y偏移: {top_right_y*100:.2f}%")
        self.bottom_left_x_label.setText(f"X偏移: {bottom_left_x*100:.2f}%")
        self.bottom_left_y_label.setText(f"Y偏移: {bottom_left_y*100:.2f}%")
        self.bottom_right_x_label.setText(f"X偏移: {bottom_right_x*100:.2f}%")
        self.bottom_right_y_label.setText(f"Y偏移: {bottom_right_y*100:.2f}%")
        
        # 更新裁剪标签
        self.crop_left_label.setText(f"X: {crop_left*100:.2f}%")
        self.crop_top_label.setText(f"Y: {crop_top*100:.2f}%")
        self.crop_right_label.setText(f"X: {crop_right*100:.2f}%")
        self.crop_bottom_label.setText(f"Y: {crop_bottom*100:.2f}%")

        # 消除摩尔纹
        if self.moire_switch.isChecked():
            self.processed_image = self.remove_moire(self.original_image_old)
            # 将图像转换为灰度图，因为adaptiveThreshold需要单通道输入
            if len(self.processed_image.shape) == 3:
                gray_image = cv2.cvtColor(self.processed_image, cv2.COLOR_BGR2GRAY)
            else:
                gray_image = self.processed_image
            
            binary = cv2.adaptiveThreshold(gray_image,255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,25,15)
            se = cv2.getStructuringElement(cv2.MORPH_RECT,(1,1))
            se = cv2.morphologyEx(se, cv2.MORPH_CLOSE, (2,2))
            mask = cv2.dilate(binary,se)
            mask1 = cv2.bitwise_not(mask)
            
            # 确保mask与原始图像的通道数匹配
            if len(self.original_image_old.shape) == 3 and len(mask.shape) == 2:
                # 将单通道mask转换为3通道
                mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                mask1_3ch = cv2.cvtColor(mask1, cv2.COLOR_GRAY2BGR)
                binary = cv2.bitwise_and(self.original_image_old, mask_3ch)
                self.processed_image = cv2.add(binary, mask1_3ch)
            else:
                binary = cv2.bitwise_and(self.original_image_old, mask)
                self.processed_image = cv2.add(binary, mask1)
        else:
            # 处理图片
            self.processed_image = self.original_image.copy()
        
        # 四点变换
        if self.perspective_switch.isChecked() and any([top_left_x, top_left_y, top_right_x, top_right_y, 
                bottom_left_x, bottom_left_y, bottom_right_x, bottom_right_y]):
            self.processed_image = self.apply_perspective_transform(self.processed_image, 
                top_left_x, top_left_y, top_right_x, top_right_y,
                bottom_left_x, bottom_left_y, bottom_right_x, bottom_right_y)
        
        # 图片旋转
        if rotate_value != 0:
            self.processed_image = self.rotate_image(self.processed_image, rotate_value)
        
        # 对比增强
        if contrast_value != 1.0:
            self.processed_image = self.adjust_contrast(self.processed_image, contrast_value)
        
        # 亮度调节
        if brightness_value != 0:
            self.processed_image = self.adjust_brightness(self.processed_image, brightness_value)
        
        # 清晰度调节
        if sharpness_value > 0:
            self.processed_image = self.adjust_sharpness(self.processed_image, sharpness_value)

        # 画面柔和
        if blur_value > 0:
            self.processed_image = self.apply_blur(self.processed_image, blur_value)
        
        # 裁剪功能
        if self.crop_switch.isChecked() and (crop_left > 0 or crop_top > 0 or crop_right < 1.0 or crop_bottom < 1.0):
            self.processed_image = self.apply_crop(self.processed_image, crop_left, crop_top, crop_right, crop_bottom)
        
        # 显示处理后的图片
        self.display_image(self.processed_image, self.result_label)
    
    def rotate_image(self, image, angle):
        """旋转图片"""
        if angle == 0:
            return image
        
        # 获取图片尺寸
        height, width = image.shape[:2]
        
        # 计算旋转中心
        center = (width // 2, height // 2)
        
        # 获取旋转矩阵
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 计算旋转后的图片尺寸
        cos_val = abs(rotation_matrix[0, 0])
        sin_val = abs(rotation_matrix[0, 1])
        new_width = int((height * sin_val) + (width * cos_val))
        new_height = int((height * cos_val) + (width * sin_val))
        
        # 调整旋转矩阵以考虑尺寸变化
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]
        
        # 执行旋转
        rotated_image = cv2.warpAffine(image, rotation_matrix, (new_width, new_height), 
                                      flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, 
                                      borderValue=(255, 255, 255))
        
        return rotated_image
    
    def apply_perspective_transform(self, image, 
                                   top_left_x, top_left_y, top_right_x, top_right_y,
                                   bottom_left_x, bottom_left_y, bottom_right_x, bottom_right_y):
        """应用四点透视变换"""
        height, width = image.shape[:2]
        
        # 原始四个角点
        src_points = np.float32([
            [0, 0],           # 左上角
            [width - 1, 0],   # 右上角
            [0, height - 1],  # 左下角
            [width - 1, height - 1]  # 右下角
        ])
        
        # 计算目标点（基于偏移百分比）
        # 偏移量基于图片尺寸的百分比
        offset_x_factor = width * 0.5  # 最大偏移为图片宽度的一半
        offset_y_factor = height * 0.5  # 最大偏移为图片高度的一半
        
        dst_points = np.float32([
            [0 + top_left_x * offset_x_factor, 0 + top_left_y * offset_y_factor],
            [width - 1 + top_right_x * offset_x_factor, 0 + top_right_y * offset_y_factor],
            [0 + bottom_left_x * offset_x_factor, height - 1 + bottom_left_y * offset_y_factor],
            [width - 1 + bottom_right_x * offset_x_factor, height - 1 + bottom_right_y * offset_y_factor]
        ])
        
        # 计算透视变换矩阵
        perspective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # 计算变换后的图片尺寸
        # 找到所有点的边界
        min_x = min(dst_points[:, 0])
        max_x = max(dst_points[:, 0])
        min_y = min(dst_points[:, 1])
        max_y = max(dst_points[:, 1])
        
        new_width = int(max_x - min_x)
        new_height = int(max_y - min_y)
        
        # 调整变换矩阵以考虑新的坐标系
        translation_matrix = np.float32([[1, 0, -min_x], [0, 1, -min_y], [0, 0, 1]])
        perspective_matrix = np.dot(translation_matrix, perspective_matrix)
        
        # 应用透视变换
        transformed_image = cv2.warpPerspective(image, perspective_matrix, (new_width, new_height),
                                                flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                                borderValue=(255, 255, 255))
        
        return transformed_image
    
    def adjust_contrast(self, image, contrast):
        """调整对比度"""
        return cv2.convertScaleAbs(image, alpha=contrast, beta=0)
    
    def adjust_brightness(self, image, brightness):
        """调整亮度"""
        # 亮度值范围：-100到100，转换为-255到255
        brightness_factor = brightness * 2.55
        return cv2.convertScaleAbs(image, alpha=1.0, beta=brightness_factor)
    
    def adjust_sharpness(self, image, sharpness):
        """调整清晰度"""
        # 创建锐化核
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]], dtype=np.float32)
        
        # 根据清晰度强度调整核
        kernel = kernel * sharpness
        kernel[1, 1] = 8 * sharpness + 1  # 中心值保持原图权重
        
        # 应用锐化
        sharpened = cv2.filter2D(image, -1, kernel)
        
        # 与原图混合
        return cv2.addWeighted(image, 1.0 - sharpness, sharpened, sharpness, 0)
    
    def remove_moire(self, image):
        """消除摩尔纹"""
        if image is None:
            return image
        
        # 检查图像通道数
        if len(image.shape) == 2:
            # 灰度图像 - 直接处理单通道
            # 多尺度高斯滤波
            def multi_scale_filter(image):
                # 不同尺度的高斯滤波
                g1 = cv2.GaussianBlur(image, (3, 3), 0.5)
                g2 = cv2.GaussianBlur(image, (5, 5), 1.0)
                g3 = cv2.GaussianBlur(image, (7, 7), 1.5)
                
                # 融合不同尺度的结果
                blended = cv2.addWeighted(g1, 0.4, g2, 0.4, 0)
                blended = cv2.addWeighted(blended, 0.6, g3, 0.4, 0)
                
                return blended
            
            # 对灰度图像进行多尺度滤波
            filtered = multi_scale_filter(image)
            
            # 双边滤波保留边缘
            bilateral = cv2.bilateralFilter(filtered, 9, 75, 75)
            
            return bilateral
        else:
            # 彩色图像 - 转换为Lab颜色空间处理
            # 转换为Lab颜色空间，更好地保留颜色信息
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 多尺度高斯滤波
            def multi_scale_filter(image):
                # 不同尺度的高斯滤波
                g1 = cv2.GaussianBlur(image, (3, 3), 0.5)
                g2 = cv2.GaussianBlur(image, (5, 5), 1.0)
                g3 = cv2.GaussianBlur(image, (7, 7), 1.5)
                
                # 融合不同尺度的结果
                blended = cv2.addWeighted(g1, 0.4, g2, 0.4, 0)
                blended = cv2.addWeighted(blended, 0.6, g3, 0.4, 0)
                
                return blended
            
            # 对亮度通道进行多尺度滤波
            l_filtered = multi_scale_filter(l)
            
            # 合并通道
            lab_filtered = cv2.merge([l_filtered, a, b])
            result_bgr = cv2.cvtColor(lab_filtered, cv2.COLOR_LAB2BGR)
            
            # 双边滤波保留边缘
            bilateral = cv2.bilateralFilter(result_bgr, 9, 75, 75)
            
            return bilateral
    
    def apply_blur(self, image, blur_strength):
        """应用高斯模糊"""
        kernel_size = blur_strength * 2 + 1  # 确保为奇数
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    
    def apply_crop(self, image, left_ratio, top_ratio, right_ratio, bottom_ratio):
        """应用裁剪功能"""
        height, width = image.shape[:2]
        
        # 计算裁剪区域的像素坐标
        left = int(width * left_ratio)
        top = int(height * top_ratio)
        right = int(width * right_ratio)
        bottom = int(height * bottom_ratio)
        
        # 确保裁剪区域有效
        if left >= right:
            left = 0
            right = width
        if top >= bottom:
            top = 0
            bottom = height
        
        # 执行裁剪
        cropped_image = image[top:bottom, left:right]
        
        return cropped_image
    
    def display_image(self, image, label):
        """在QLabel中显示图片"""
        if image is not None:
            # 转换颜色空间 BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 调整图片大小以适应标签
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            # 创建QImage - 使用copy()确保数据安全
            # 避免使用原始数据指针，防止数据被修改导致QPainter错误
            rgb_image_copy = rgb_image.copy()
            
            # 使用QImage.fromData()方法创建QImage，避免直接使用数据指针
            # 将numpy数组转换为bytes，然后创建QImage
            rgb_image_bytes = rgb_image_copy.tobytes()
            q_img = QImage(rgb_image_bytes, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # 缩放图片以适应标签 - 使用标签的实际可用尺寸
            pixmap = QPixmap.fromImage(q_img)
            
            # 获取标签的当前可用尺寸（考虑布局和边距）
            label_width = label.width() - 20  # 减去边距
            label_height = label.height() - 20  # 减去边距
            
            # 确保最小显示尺寸
            display_width = max(label_width, 200)
            display_height = max(label_height, 200)
            
            # 计算缩放比例，尽量填满显示区域
            width_ratio = display_width / w
            height_ratio = display_height / h
            
            # 选择较小的缩放比例，确保图片完全显示
            scale_ratio = min(width_ratio, height_ratio)
            
            # 计算最终显示尺寸
            final_width = int(w * scale_ratio)
            final_height = int(h * scale_ratio)
            
            scaled_pixmap = pixmap.scaled(final_width, final_height, 
                                        Qt.AspectRatioMode.KeepAspectRatio, 
                                        Qt.TransformationMode.SmoothTransformation)
            
            label.setPixmap(scaled_pixmap)
            # 确保标签显示图片后清除文字
            label.setText("")
            
            # 保存当前显示的图片，用于窗口大小变化时重新调整
            label.current_image = image
            label.current_pixmap = scaled_pixmap
    
    def reset_parameters(self):
        """重置所有参数滑块"""
        self.contrast_slider.setValue(100)
        self.brightness_slider.setValue(0)
        self.sharpness_slider.setValue(0)
        self.blur_slider.setValue(0)
        self.rotate_slider.setValue(0)
        
        # 重置四点变换滑块
        self.top_left_x_slider.setValue(0)
        self.top_left_y_slider.setValue(0)
        self.top_right_x_slider.setValue(0)
        self.top_right_y_slider.setValue(0)
        self.bottom_left_x_slider.setValue(0)
        self.bottom_left_y_slider.setValue(0)
        self.bottom_right_x_slider.setValue(0)
        self.bottom_right_y_slider.setValue(0)
        
        # 重置四点变换开关
        self.perspective_switch.setChecked(False)
        
        # 重置裁剪滑块
        self.crop_left_slider.setValue(0)
        self.crop_top_slider.setValue(0)
        self.crop_right_slider.setValue(100)
        self.crop_bottom_slider.setValue(100)
        
        # 重置裁剪开关
        self.crop_switch.setChecked(False)
        
        # 重置摩尔纹开关
        self.moire_switch.setChecked(False)
        
        if self.original_image is not None:
            self.processed_image = self.original_image.copy()
            self.display_image(self.processed_image, self.result_label)
    
    def save_image(self):
        """保存处理后的图片"""
        if self.processed_image is not None:
            # 在打开保存对话框前就生成时间戳和默认文件名
            import datetime
            now = datetime.datetime.now()
            timestamp = now.strftime("_%Y%m%d_%H%M%S")
            
            # 生成默认文件名（基于原始文件名）
            if self.original_image_path:
                # 获取原始文件名（不含路径）
                original_file_name = os.path.basename(self.original_image_path)
                # 分离文件名和扩展名
                name_without_ext, file_ext = os.path.splitext(original_file_name)
                # 如果原始文件没有扩展名，使用默认扩展名
                if not file_ext:
                    file_ext = '.png'
                # 生成基于原始文件名的默认文件名
                default_file_name = f"{name_without_ext}{timestamp}{file_ext}"
            else:
                # 如果没有原始文件路径，使用基于时间的默认文件名
                default_file_name = f"processed_image{timestamp}.png"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存图片", default_file_name, "PNG文件 (*.png);;JPEG文件 (*.jpg);;所有文件 (*)")
            
            if file_path:
                try:
                    # 分离文件名和扩展名
                    file_dir = os.path.dirname(file_path)
                    file_name = os.path.basename(file_path)
                    name_without_ext, file_ext = os.path.splitext(file_name)
                    
                    # 如果用户没有输入扩展名，使用默认扩展名
                    if not file_ext:
                        file_ext = '.png'
                        file_name = name_without_ext + file_ext
                    
                    # 构建新的文件名（确保包含时间戳）
                    # 检查文件名是否已经包含时间戳格式
                    import re
                    timestamp_pattern = r'_\d{8}_\d{6}$'
                    if not re.search(timestamp_pattern, name_without_ext):
                        # 如果文件名不包含时间戳，添加时间戳
                        new_file_name = name_without_ext + timestamp + file_ext
                    else:
                        # 如果文件名已经包含时间戳，直接使用
                        new_file_name = file_name
                    
                    new_file_path = os.path.join(file_dir, new_file_name)
                    
                    # 方法1: 使用cv2.imencode保存，解决中文路径问题
                    file_ext_lower = file_ext.lower()
                    
                    if file_ext_lower in ['.jpg', '.jpeg']:
                        # JPEG格式
                        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
                        success, buffer = cv2.imencode(file_ext_lower, self.processed_image, encode_param)
                    elif file_ext_lower == '.png':
                        # PNG格式
                        encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
                        success, buffer = cv2.imencode(file_ext_lower, self.processed_image, encode_param)
                    else:
                        # 其他格式，默认使用PNG
                        new_file_path = new_file_path.replace(file_ext, '.png')
                        encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
                        success, buffer = cv2.imencode('.png', self.processed_image, encode_param)
                    
                    if success:
                        # 写入文件
                        with open(new_file_path, 'wb') as f:
                            f.write(buffer)
                        self.show_success_message(f"图片已成功保存到: {new_file_path}")
                    else:
                        # 如果方法1失败，尝试方法2: 使用绝对路径
                        abs_path = os.path.abspath(new_file_path)
                        cv2.imwrite(abs_path, self.processed_image)
                        self.show_success_message(f"图片已成功保存到: {abs_path}")
                        
                except Exception as e:
                    self.show_error_message(f"保存图片时发生错误: {str(e)}")
    
    def show_success_message(self, message):
        """显示成功消息"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "成功", message)


def main():
    app = QApplication(sys.argv)
    processor = ImageProcessor()
    processor.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()