#!/usr/bin/env python3
"""
HAADF-STEM Image Deconvolution GUI for run_deconv.py
基于run_deconv.py的Qt界面

Features:
- 完整的参数控制界面
- 三种解卷积算法选择
- 实时处理进度显示
- 结果预览和保存
- 现代化的界面设计
"""

import sys
import os
import numpy as np

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QLineEdit, QSpinBox,
        QDoubleSpinBox, QGroupBox, QFileDialog, QMessageBox,
        QProgressBar, QTabWidget, QComboBox, QCheckBox,
        QScrollArea, QTextEdit, QRadioButton, QButtonGroup, QInputDialog
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QAction
except ImportError:
    print("Error: PyQt6 not installed. Install with: pip install PyQt6")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use('QtAgg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
except ImportError:
    print("Error: matplotlib not installed.")
    sys.exit(1)

# Import processing functions from run_deconv.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from stem_deconv.utils import read_mrc, write_mrc
    from stem_deconv.physics import calculate_ctf, calculate_probe, calculate_wavelength
    from stem_deconv.core import richardson_lucy_additive, richardson_lucy_multiplicative, fista_deconvolution
    from stem_deconv.postprocess import radial_wiener_filter, p_spline_wiener_filter, radial_difference_filter
except ImportError as e:
    print(f"Warning: Could not import stem_deconv modules: {e}")
    print("Please ensure stem_deconv package is available in the current directory.")
    sys.exit(1)


class DeconvolutionWorker(QThread):
    """处理线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, params):
        super().__init__()
        self.params = params
        self.results = {}
        
    def run(self):
        try:
            self.progress.emit("Loading image...")
            
            # Load Image
            if not os.path.exists(self.params['image_path']):
                raise FileNotFoundError(f"Image not found: {self.params['image_path']}")
            
            image_data, pixel_size = read_mrc(self.params['image_path'])
            # Use pixel_size from file if available, otherwise use GUI value
            if pixel_size <= 0:
                pixel_size = self.params['pixel_size_nm']
            self.progress.emit(f"Image loaded: {image_data.shape}, Pixel size: {pixel_size} nm")
            
            # Generate Probe
            self.progress.emit("Generating probe...")
            ctf = calculate_ctf(
                image_data.shape, pixel_size, 
                self.params['voltage_kv'], 
                self.params['cs3_mm'], self.params['cs5_mm'], 
                self.params['defocus_nm'], 
                self.params['obj_aperture_rad']
            )
            probe = calculate_probe(ctf, image_data.shape[1]/2, image_data.shape[0]/2)
            wavelength_nm = calculate_wavelength(self.params['voltage_kv'])
            
            # Store probe info
            self.results['probe'] = probe
            self.results['ctf'] = ctf
            
            # Run selected algorithm (single selection)
            algorithm_id = self.params['algorithm']
            if algorithm_id == 0:  # Additive
                self.progress.emit("Running Richardson-Lucy Additive...")
                result = richardson_lucy_additive(
                    image_data, probe, 
                    iterations=self.params['iterations'],
                    lambda_reg=self.params['lambda_reg'],
                    reg_type=self.params['reg_type'],
                    boundary_handling=self.params['boundary_handling']
                )
                self.results['result'] = result
            elif algorithm_id == 1:  # Multiplicative
                self.progress.emit("Running Richardson-Lucy Multiplicative...")
                bg_level = np.percentile(image_data, 1.0)
                result = richardson_lucy_multiplicative(
                    image_data, probe,
                    iterations=self.params['iterations'],
                    lambda_reg=self.params['lambda_reg'],
                    reg_type=self.params['reg_type'],
                    pixel_size=pixel_size,
                    wavelength=wavelength_nm,
                    acceleration=self.params['acceleration'],
                    boundary_handling=self.params['boundary_handling'],
                    damping_threshold=self.params['damping_threshold'],
                    background_level=bg_level,
                    entropy_stopping=self.params['entropy_stopping'],
                    sharpness_stopping=self.params['sharpness_stopping'],
                    residual_stopping=self.params['residual_stopping']
                )
                self.results['result'] = result
            elif algorithm_id == 2:  # FISTA
                self.progress.emit("Running FISTA Deconvolution...")
                result = fista_deconvolution(
                    image_data, probe,
                    iterations=self.params['iterations'],
                    lambda_reg=self.params['fista_lambda_reg'],
                    boundary_handling=self.params['boundary_handling']
                )
                self.results['result'] = result
            
            # Apply post-processing to result
            if 'result' in self.results:
                if self.params['use_p_spline']:
                    self.progress.emit("Applying P-spline filter...")
                    self.results['result'] = p_spline_wiener_filter(
                        np.abs(self.results['result']), pixel_size,
                        lambda_val=self.params['p_spline_lambda'],
                        information_limit=self.params['information_limit']
                    )
                if self.params['apply_wiener']:
                    self.progress.emit("Applying radial Wiener filter...")
                    self.results['result'] = radial_wiener_filter(
                        np.abs(self.results['result']), pixel_size,
                        information_limit=self.params['information_limit']
                    )
                if self.params['use_radial_diff']:
                    self.progress.emit("Applying radial difference filter...")
                    self.results['result'] = radial_difference_filter(
                        np.abs(self.results['result']), pixel_size,
                        information_limit=self.params['information_limit']
                    )
            
            # Store original data
            self.results['original'] = image_data
            self.results['pixel_size'] = pixel_size
            
            self.progress.emit("Processing completed!")
            self.finished.emit(self.results)
            
        except Exception as e:
            self.error.emit(str(e))


class ImageDisplayWidget(QWidget):
    """图像显示组件"""
    def __init__(self, title=""):
        super().__init__()
        self.title = title
        self.init_ui(title)
        
    def init_ui(self, title):
        layout = QVBoxLayout()
        
        # Matplotlib figure - square aspect ratio
        self.figure = Figure(figsize=(6, 6), dpi=80)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Style the toolbar
        self.toolbar.setStyleSheet("""
            QToolBar {
                background: transparent;
                border: none;
                spacing: 2px;
            }
            QToolButton {
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px;
                margin: 1px;
            }
            QToolButton:hover {
                background: rgba(67, 97, 238, 0.1);
                border-color: #4361ee;
            }
            QToolButton:pressed {
                background: rgba(67, 97, 238, 0.2);
            }
        """)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
        
    def apply_theme(self, theme_name):
        """应用主题到图像显示组件"""
        themes = {
            "Professional Blue": {
                "title_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9)",
                "title_color": "white",
                "figure_bg": "#2c3e50",
                "canvas_bg": "#1a252f"
            },
            "Dark Mode": {
                "title_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9f7aea, stop:1 #805ad5)",
                "title_color": "white",
                "figure_bg": "#2d3748",
                "canvas_bg": "#1a202c"
            },
            "Light Clean": {
                "title_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2196f3, stop:1 #1976d2)",
                "title_color": "white",
                "figure_bg": "#37474f",
                "canvas_bg": "#263238"
            },
            "Nature Green": {
                "title_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66bb6a, stop:1 #4caf50)",
                "title_color": "white",
                "figure_bg": "#1b5e20",
                "canvas_bg": "#0d2818"
            },
            "Sunset Orange": {
                "title_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff9800, stop:1 #f57c00)",
                "title_color": "white",
                "figure_bg": "#e65100",
                "canvas_bg": "#bf360c"
            }
        }
        
        if theme_name in themes:
            theme = themes[theme_name]
            
            # Update matplotlib figure background
            self.figure.patch.set_facecolor(theme['figure_bg'])
            self.canvas.setStyleSheet(f"""
                FigureCanvas {{
                    background-color: {theme['canvas_bg']};
                    border: 2px solid #dee2e6;
                    border-radius: 6px;
                }}
            """)
            
            # Update toolbar theme
            if theme_name == "Dark Mode":
                self.toolbar.setStyleSheet("""
                    QToolBar {
                        background: #2d3748;
                        border: none;
                        spacing: 2px;
                    }
                    QToolButton {
                        background: #4a5568;
                        border: 1px solid #718096;
                        border-radius: 4px;
                        padding: 4px;
                        margin: 1px;
                        color: #e2e8f0;
                    }
                    QToolButton:hover {
                        background: #9f7aea;
                        border-color: #9f7aea;
                    }
                    QToolButton:pressed {
                        background: #805ad5;
                    }
                """)
            else:
                self.toolbar.setStyleSheet("""
                    QToolBar {
                        background: transparent;
                        border: none;
                        spacing: 2px;
                    }
                    QToolButton {
                        background: rgba(255, 255, 255, 0.8);
                        border: 1px solid #dee2e6;
                        border-radius: 4px;
                        padding: 4px;
                        margin: 1px;
                    }
                    QToolButton:hover {
                        background: rgba(67, 97, 238, 0.1);
                        border-color: #4361ee;
                    }
                    QToolButton:pressed {
                        background: rgba(67, 97, 238, 0.2);
                    }
                """)
            
            self.canvas.draw()
        
    def display_image(self, data, title=None, colormap='gray'):
        """显示图像"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if len(data.shape) == 2:
            im = ax.imshow(data, cmap=colormap, interpolation='nearest')
            
            # Style colorbar based on current theme
            cbar = self.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            if hasattr(self.parent(), 'current_theme'):
                theme = self.parent().current_theme
                self.apply_matplotlib_theme(ax, cbar, theme)
        else:
            ax.imshow(data, interpolation='nearest')
            
        ax.set_title(title or self.title, fontweight='bold', fontsize=10)
        ax.axis('off')
        
        # Ensure square aspect ratio
        ax.set_aspect('equal')
        
        self.figure.tight_layout()
        self.canvas.draw()
        
    def apply_matplotlib_theme(self, ax, cbar, theme_name):
        """应用matplotlib主题样式"""
        theme_colors = {
            "Professional Blue": {
                "text": "#ecf0f1",
                "spine": "#4361ee",
                "tick": "#ecf0f1"
            },
            "Dark Mode": {
                "text": "#e2e8f0",
                "spine": "#9f7aea",
                "tick": "#e2e8f0"
            },
            "Light Clean": {
                "text": "#eceff1",
                "spine": "#2196f3",
                "tick": "#eceff1"
            },
            "Nature Green": {
                "text": "#e8f5e8",
                "spine": "#66bb6a",
                "tick": "#e8f5e8"
            },
            "Sunset Orange": {
                "text": "#fff3e0",
                "spine": "#ff9800",
                "tick": "#fff3e0"
            }
        }
        
        if theme_name in theme_colors:
            colors = theme_colors[theme_name]
            cbar.ax.yaxis.set_tick_params(colors=colors["tick"])
            cbar.set_label('Intensity', color=colors["text"])
            ax.spines['bottom'].set_color(colors["spine"])
            ax.spines['top'].set_color(colors["spine"])
            ax.spines['right'].set_color(colors["spine"])
            ax.spines['left'].set_color(colors["spine"])
            ax.tick_params(axis='x', colors=colors["tick"])
            ax.tick_params(axis='y', colors=colors["tick"])
            ax.xaxis.label.set_color(colors["text"])
            ax.yaxis.label.set_color(colors["text"])
            ax.title.set_color(colors["text"])
        
    def clear(self):
        """清除显示"""
        self.figure.clear()
        self.canvas.draw()


class DeconvolutionGUI(QMainWindow):
    """主界面"""
    def __init__(self):
        super().__init__()
        self.worker = None
        self.results = {}
        self.current_theme = "Professional Blue"
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("HAADF-STEM Image Deconvolution GUI")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Left panel - Controls
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel - Image display
        right_panel = self.create_display_panel()
        main_layout.addWidget(right_panel, 2)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Add theme selector to menu bar
        self.create_theme_menu()
        
    def create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Scroll area
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        
        # File selection
        file_group = QGroupBox("📁 File Selection")
        file_layout = QGridLayout()
        
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText("Select MRC image file...")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_image)
        
        file_layout.addWidget(QLabel("Image:"), 0, 0)
        file_layout.addWidget(self.image_path_edit, 0, 1)
        file_layout.addWidget(browse_btn, 0, 2)
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Output directory...")
        self.output_path_edit.setText("restored")
        output_browse_btn = QPushButton("Browse...")
        output_browse_btn.clicked.connect(self.browse_output)
        
        file_layout.addWidget(QLabel("Output:"), 1, 0)
        file_layout.addWidget(self.output_path_edit, 1, 1)
        file_layout.addWidget(output_browse_btn, 1, 2)
        
        file_group.setLayout(file_layout)
        scroll_layout.addWidget(file_group)
        
        # Microscope parameters
        micro_group = QGroupBox("🔬 Microscope Parameters")
        micro_layout = QGridLayout()
        
        # Voltage
        micro_layout.addWidget(QLabel("Voltage (kV):"), 0, 0)
        self.voltage_spin = QDoubleSpinBox()
        self.voltage_spin.setRange(50, 1000)
        self.voltage_spin.setValue(300.0)
        self.voltage_spin.setSuffix(" kV")
        micro_layout.addWidget(self.voltage_spin, 0, 1)
        
        # Cs3
        micro_layout.addWidget(QLabel("Cs3 (mm):"), 1, 0)
        self.cs3_spin = QDoubleSpinBox()
        self.cs3_spin.setRange(-10, 10)
        self.cs3_spin.setValue(0.5)
        self.cs3_spin.setSingleStep(0.1)
        self.cs3_spin.setSuffix(" mm")
        micro_layout.addWidget(self.cs3_spin, 1, 1)
        
        # Cs5
        micro_layout.addWidget(QLabel("Cs5 (mm):"), 2, 0)
        self.cs5_spin = QDoubleSpinBox()
        self.cs5_spin.setRange(-10, 10)
        self.cs5_spin.setValue(0.0)
        self.cs5_spin.setSingleStep(0.1)
        self.cs5_spin.setSuffix(" mm")
        micro_layout.addWidget(self.cs5_spin, 2, 1)
        
        # Defocus
        micro_layout.addWidget(QLabel("Defocus (nm):"), 3, 0)
        self.defocus_spin = QDoubleSpinBox()
        self.defocus_spin.setRange(-1000, 1000)
        self.defocus_spin.setValue(-44.0)
        self.defocus_spin.setSuffix(" nm")
        micro_layout.addWidget(self.defocus_spin, 3, 1)
        
        # Objective aperture
        micro_layout.addWidget(QLabel("Obj. Aperture:"), 4, 0)
        self.obj_aperture_spin = QDoubleSpinBox()
        self.obj_aperture_spin.setRange(1, 50)
        self.obj_aperture_spin.setValue(16.0)
        self.obj_aperture_spin.setSuffix(" mrad")
        micro_layout.addWidget(self.obj_aperture_spin, 4, 1)
        
        # Pixel size (read-only, loaded from file)
        micro_layout.addWidget(QLabel("Pixel Size (nm):"), 5, 0)
        self.pixel_size_spin = QDoubleSpinBox()
        self.pixel_size_spin.setRange(0.001, 10.0)
        self.pixel_size_spin.setValue(0.1)
        self.pixel_size_spin.setDecimals(6)
        self.pixel_size_spin.setSingleStep(0.001)
        self.pixel_size_spin.setSuffix(" nm")
        self.pixel_size_spin.setReadOnly(True)
        self.pixel_size_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.pixel_size_spin.setStyleSheet("QDoubleSpinBox { background: #2c3e50; }")
        micro_layout.addWidget(self.pixel_size_spin, 5, 1)
        
        # Add info label and manual set button
        pixel_info_layout = QHBoxLayout()
        pixel_info_label = QLabel("(Auto-loaded from MRC file)")
        pixel_info_label.setStyleSheet("color: #9f7aea; font-size: 9pt; font-style: italic;")
        pixel_info_layout.addWidget(pixel_info_label)
        
        manual_pixel_btn = QPushButton("Set Manual")
        manual_pixel_btn.setMaximumWidth(80)
        manual_pixel_btn.clicked.connect(self.set_manual_pixel_size)
        manual_pixel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9f7aea, stop:1 #805ad5);
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 8pt;
                padding: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b794f4, stop:1 #9f7aea);
            }
        """)
        pixel_info_layout.addWidget(manual_pixel_btn)
        pixel_info_layout.addStretch()
        
        micro_layout.addLayout(pixel_info_layout, 6, 0, 1, 2)
        
        micro_group.setLayout(micro_layout)
        scroll_layout.addWidget(micro_group)
        
        # Advanced Aberration Parameters
        aberr_group = QGroupBox("⚙️ Advanced Aberration Parameters")
        aberr_layout = QGridLayout()
        
        # A2 aberration
        aberr_layout.addWidget(QLabel("A2 Amplitude (nm):"), 0, 0)
        self.a2_amp_spin = QDoubleSpinBox()
        self.a2_amp_spin.setRange(0, 1000)
        self.a2_amp_spin.setValue(0)
        self.a2_amp_spin.setSuffix(" nm")
        aberr_layout.addWidget(self.a2_amp_spin, 0, 1)
        
        aberr_layout.addWidget(QLabel("A2 Angle (rad):"), 0, 2)
        self.a2_angle_spin = QDoubleSpinBox()
        self.a2_angle_spin.setRange(0, 6.283)
        self.a2_angle_spin.setValue(0)
        self.a2_angle_spin.setDecimals(4)
        self.a2_angle_spin.setSingleStep(0.01)
        self.a2_angle_spin.setSuffix(" rad")
        aberr_layout.addWidget(self.a2_angle_spin, 0, 3)
        
        # A3 aberration
        aberr_layout.addWidget(QLabel("A3 Amplitude (nm):"), 1, 0)
        self.a3_amp_spin = QDoubleSpinBox()
        self.a3_amp_spin.setRange(0, 1000)
        self.a3_amp_spin.setValue(0)
        self.a3_amp_spin.setSuffix(" nm")
        aberr_layout.addWidget(self.a3_amp_spin, 1, 1)
        
        aberr_layout.addWidget(QLabel("A3 Angle (rad):"), 1, 2)
        self.a3_angle_spin = QDoubleSpinBox()
        self.a3_angle_spin.setRange(0, 6.283)
        self.a3_angle_spin.setValue(0)
        self.a3_angle_spin.setDecimals(4)
        self.a3_angle_spin.setSingleStep(0.01)
        self.a3_angle_spin.setSuffix(" rad")
        aberr_layout.addWidget(self.a3_angle_spin, 1, 3)
        
        # B2 aberration
        aberr_layout.addWidget(QLabel("B2 Amplitude (nm):"), 2, 0)
        self.b2_amp_spin = QDoubleSpinBox()
        self.b2_amp_spin.setRange(0, 1000)
        self.b2_amp_spin.setValue(0)
        self.b2_amp_spin.setSuffix(" nm")
        aberr_layout.addWidget(self.b2_amp_spin, 2, 1)
        
        aberr_layout.addWidget(QLabel("B2 Angle (rad):"), 2, 2)
        self.b2_angle_spin = QDoubleSpinBox()
        self.b2_angle_spin.setRange(0, 6.283)
        self.b2_angle_spin.setValue(0)
        self.b2_angle_spin.setDecimals(4)
        self.b2_angle_spin.setSingleStep(0.01)
        self.b2_angle_spin.setSuffix(" rad")
        aberr_layout.addWidget(self.b2_angle_spin, 2, 3)
        
        # Focal spread and convergence angle
        aberr_layout.addWidget(QLabel("Focal Spread (nm):"), 3, 0)
        self.focal_spread_spin = QDoubleSpinBox()
        self.focal_spread_spin.setRange(0, 100)
        self.focal_spread_spin.setValue(0)
        self.focal_spread_spin.setSuffix(" nm")
        aberr_layout.addWidget(self.focal_spread_spin, 3, 1)
        
        aberr_layout.addWidget(QLabel("Convergence (rad):"), 3, 2)
        self.convergence_spin = QDoubleSpinBox()
        self.convergence_spin.setRange(0, 0.1)
        self.convergence_spin.setValue(0)
        self.convergence_spin.setDecimals(4)
        self.convergence_spin.setSingleStep(0.001)
        self.convergence_spin.setSuffix(" rad")
        aberr_layout.addWidget(self.convergence_spin, 3, 3)
        
        aberr_group.setLayout(aberr_layout)
        scroll_layout.addWidget(aberr_group)
        
        # Algorithm selection - Radio buttons for single selection
        algo_group = QGroupBox("🧮 Algorithm Selection")
        algo_layout = QVBoxLayout()
        
        self.algorithm_group = QButtonGroup()
        
        self.additive_radio = QRadioButton("Richardson-Lucy Additive")
        self.algorithm_group.addButton(self.additive_radio, 0)
        algo_layout.addWidget(self.additive_radio)
        
        self.multiplicative_radio = QRadioButton("Richardson-Lucy Multiplicative")
        self.multiplicative_radio.setChecked(True)
        self.algorithm_group.addButton(self.multiplicative_radio, 1)
        algo_layout.addWidget(self.multiplicative_radio)
        
        self.fista_radio = QRadioButton("FISTA Deconvolution")
        self.algorithm_group.addButton(self.fista_radio, 2)
        algo_layout.addWidget(self.fista_radio)
        
        algo_group.setLayout(algo_layout)
        scroll_layout.addWidget(algo_group)
        
        # Deconvolution parameters
        deconv_group = QGroupBox("⚡ Deconvolution Parameters")
        deconv_layout = QGridLayout()
        
        deconv_layout.addWidget(QLabel("Iterations:"), 0, 0)
        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(1, 100)
        self.iterations_spin.setValue(15)
        deconv_layout.addWidget(self.iterations_spin, 0, 1)
        
        deconv_layout.addWidget(QLabel("Lambda (RL):"), 1, 0)
        self.lambda_spin = QDoubleSpinBox()
        self.lambda_spin.setRange(0.0001, 1.0)
        self.lambda_spin.setValue(0.002)
        self.lambda_spin.setDecimals(4)
        self.lambda_spin.setSingleStep(0.0001)
        deconv_layout.addWidget(self.lambda_spin, 1, 1)
        
        deconv_layout.addWidget(QLabel("Lambda (FISTA):"), 2, 0)
        self.fista_lambda_spin = QDoubleSpinBox()
        self.fista_lambda_spin.setRange(0.0001, 1.0)
        self.fista_lambda_spin.setValue(0.005)
        self.fista_lambda_spin.setDecimals(4)
        self.fista_lambda_spin.setSingleStep(0.0001)
        deconv_layout.addWidget(self.fista_lambda_spin, 2, 1)
        
        # Regularization type
        deconv_layout.addWidget(QLabel("Reg. Type:"), 3, 0)
        self.reg_type_combo = QComboBox()
        self.reg_type_combo.addItems(["TV", "L2"])
        deconv_layout.addWidget(self.reg_type_combo, 3, 1)
        
        deconv_group.setLayout(deconv_layout)
        scroll_layout.addWidget(deconv_group)
        
        # Advanced options
        advanced_group = QGroupBox("🔧 Advanced Options")
        advanced_layout = QVBoxLayout()

        self.boundary_handling_check = QCheckBox("Boundary Handling")
        self.boundary_handling_check.setChecked(True)
        self.boundary_handling_check.setStyleSheet("QCheckBox { color: #ffffff; font-size: 11pt; font-weight: bold; padding: 3px; } QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #4361ee; border-radius: 4px; background: #2c3e50; } QCheckBox::indicator:checked { background: #4361ee; border-color: #4361ee; }")
        advanced_layout.addWidget(self.boundary_handling_check)

        self.acceleration_check = QCheckBox("Acceleration (Multiplicative)")
        self.acceleration_check.setChecked(True)
        self.acceleration_check.setStyleSheet("QCheckBox { color: #ffffff; font-size: 11pt; font-weight: bold; padding: 3px; } QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #4361ee; border-radius: 4px; background: #2c3e50; } QCheckBox::indicator:checked { background: #4361ee; border-color: #4361ee; }")
        advanced_layout.addWidget(self.acceleration_check)

        # Stopping criteria
        self.entropy_stopping_check = QCheckBox("Entropy Plateau Stopping")
        self.entropy_stopping_check.setChecked(False)
        self.entropy_stopping_check.setStyleSheet("QCheckBox { color: #ffffff; font-size: 11pt; font-weight: bold; padding: 3px; } QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #4361ee; border-radius: 4px; background: #2c3e50; } QCheckBox::indicator:checked { background: #4361ee; border-color: #4361ee; }")
        advanced_layout.addWidget(self.entropy_stopping_check)

        self.sharpness_stopping_check = QCheckBox("Sharpness Minimum Stopping")
        self.sharpness_stopping_check.setChecked(False)
        self.sharpness_stopping_check.setStyleSheet("QCheckBox { color: #ffffff; font-size: 11pt; font-weight: bold; padding: 3px; } QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #4361ee; border-radius: 4px; background: #2c3e50; } QCheckBox::indicator:checked { background: #4361ee; border-color: #4361ee; }")
        advanced_layout.addWidget(self.sharpness_stopping_check)

        self.residual_stopping_check = QCheckBox("Residual-based Stopping")
        self.residual_stopping_check.setChecked(True)
        self.residual_stopping_check.setStyleSheet("QCheckBox { color: #ffffff; font-size: 11pt; font-weight: bold; padding: 3px; } QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #4361ee; border-radius: 4px; background: #2c3e50; } QCheckBox::indicator:checked { background: #4361ee; border-color: #4361ee; }")
        advanced_layout.addWidget(self.residual_stopping_check)

        advanced_group.setLayout(advanced_layout)
        scroll_layout.addWidget(advanced_group)
        
        # Post-processing
        post_group = QGroupBox("🎨 Post-processing")
        post_layout = QVBoxLayout()

        self.apply_wiener_check = QCheckBox("Apply Wiener Filter")
        self.apply_wiener_check.setChecked(True)
        self.apply_wiener_check.setStyleSheet("QCheckBox { color: #ffffff; font-size: 11pt; font-weight: bold; padding: 3px; } QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #4361ee; border-radius: 4px; background: #2c3e50; } QCheckBox::indicator:checked { background: #4361ee; border-color: #4361ee; }")
        post_layout.addWidget(self.apply_wiener_check)

        self.use_p_spline_check = QCheckBox("Apply P-spline Filter")
        self.use_p_spline_check.setChecked(False)
        self.use_p_spline_check.setStyleSheet("QCheckBox { color: #ffffff; font-size: 11pt; font-weight: bold; padding: 3px; } QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #4361ee; border-radius: 4px; background: #2c3e50; } QCheckBox::indicator:checked { background: #4361ee; border-color: #4361ee; }")
        post_layout.addWidget(self.use_p_spline_check)

        self.use_radial_diff_check = QCheckBox("Apply Radial Difference Filter")
        self.use_radial_diff_check.setChecked(False)
        self.use_radial_diff_check.setStyleSheet("QCheckBox { color: #ffffff; font-size: 11pt; font-weight: bold; padding: 3px; } QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #4361ee; border-radius: 4px; background: #2c3e50; } QCheckBox::indicator:checked { background: #4361ee; border-color: #4361ee; }")
        post_layout.addWidget(self.use_radial_diff_check)

        post_param_layout = QGridLayout()
        
        post_param_layout.addWidget(QLabel("P-spline Lambda:"), 0, 0)
        self.p_spline_lambda_spin = QDoubleSpinBox()
        self.p_spline_lambda_spin.setRange(1, 10000)
        self.p_spline_lambda_spin.setValue(1000.0)
        post_param_layout.addWidget(self.p_spline_lambda_spin, 0, 1)
        
        post_param_layout.addWidget(QLabel("Info Limit:"), 1, 0)
        self.info_limit_spin = QDoubleSpinBox()
        self.info_limit_spin.setRange(0.1, 100)
        self.info_limit_spin.setValue(1.0)
        self.info_limit_spin.setSpecialValueText("Auto")
        post_param_layout.addWidget(self.info_limit_spin, 1, 1)
        
        post_layout.addLayout(post_param_layout)

        # Filter target & apply button
        filter_action_layout = QHBoxLayout()
        filter_action_layout.addWidget(QLabel("Target:"))
        self.filter_target_combo = QComboBox()
        self.filter_target_combo.addItems(["Deconvolution Result", "Original Image"])
        self.filter_target_combo.setStyleSheet("QComboBox { color: #ffffff; background: rgba(44, 62, 80, 0.7); border: 1px solid #4361ee; border-radius: 4px; padding: 4px; } QComboBox::drop-down { border: none; } QComboBox QAbstractItemView { color: #ffffff; background: #2c3e50; selection-background-color: #4361ee; }")
        filter_action_layout.addWidget(self.filter_target_combo)
        self.apply_filters_btn = QPushButton("Apply Filters")
        self.apply_filters_btn.clicked.connect(self.apply_post_filters_manually)
        self.apply_filters_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4361ee, stop:1 #3a56d4);
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4cc9f0, stop:1 #4361ee);
            }
            QPushButton:disabled {
                background: #555555;
            }
        """)
        filter_action_layout.addWidget(self.apply_filters_btn)
        post_layout.addLayout(filter_action_layout)

        post_group.setLayout(post_layout)
        scroll_layout.addWidget(post_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        # Add preview probe button
        self.preview_probe_btn = QPushButton("Preview Probe")
        self.preview_probe_btn.clicked.connect(self.preview_probe)
        self.preview_probe_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9f7aea, stop:1 #805ad5);
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b794f4, stop:1 #9f7aea);
            }
            QPushButton:disabled {
                background: #CCCCCC;
            }
        """)
        
        self.process_btn = QPushButton("Start Processing")
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        
        self.save_btn = QPushButton("Save Results")
        self.save_btn.clicked.connect(self.save_results)
        self.save_btn.setEnabled(False)
        
        button_layout.addWidget(self.preview_probe_btn)
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.save_btn)
        scroll_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        scroll_layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        scroll_layout.addWidget(self.status_text)
        
        scroll_layout.addStretch()
        layout.addWidget(scroll)
        
        return panel
        
    def create_theme_menu(self):
        """创建主题菜单"""
        menubar = self.menuBar()
        theme_menu = menubar.addMenu('🎨 Theme')
        
        themes = [
            ("Professional Blue", "professional_blue"),
            ("Dark Mode", "dark_mode"),
            ("Light Clean", "light_clean"),
            ("Nature Green", "nature_green"),
            ("Sunset Orange", "sunset_orange")
        ]
        
        for theme_name, theme_id in themes:
            action = QAction(theme_name, self)
            action.triggered.connect(lambda checked, tid=theme_id, tname=theme_name: self.apply_theme(tid, tname))
            theme_menu.addAction(action)
            
    def apply_theme(self, theme_id, theme_name):
        """应用主题"""
        self.current_theme = theme_name
        themes = {
            "professional_blue": self.get_professional_blue_theme(),
            "dark_mode": self.get_dark_mode_theme(),
            "light_clean": self.get_light_clean_theme(),
            "nature_green": self.get_nature_green_theme(),
            "sunset_orange": self.get_sunset_orange_theme()
        }

        # Define theme gradients for display panel labels
        theme_label_gradients = {
            "Professional Blue": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9)",
            "Dark Mode": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9f7aea, stop:1 #805ad5)",
            "Light Clean": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2196f3, stop:1 #1976d2)",
            "Nature Green": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66bb6a, stop:1 #4caf50)",
            "Sunset Orange": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff9800, stop:1 #f57c00)"
        }

        # Define theme colors for checkboxes
        theme_checkbox_colors = {
            "Professional Blue": "#4361ee",
            "Dark Mode": "#9f7aea",
            "Light Clean": "#2196f3",
            "Nature Green": "#66bb6a",
            "Sunset Orange": "#ff9800"
        }

        if theme_id in themes:
            self.setStyleSheet(themes[theme_id])
            self.statusBar().showMessage(f"Theme: {theme_name}")

            # Apply theme to all image display widgets
            for widget in self.findChildren(ImageDisplayWidget):
                widget.apply_theme(theme_name)

            # Update display panel labels with theme-appropriate colors
            label_gradient = theme_label_gradients[theme_name]
            label_style = f"QLabel {{ color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: {label_gradient}; border-radius: 3px; }}"
            for label in self.findChildren(QLabel):
                # Check if this is a display panel label
                if hasattr(label, 'text') and any(keyword in label.text() for keyword in ['Space:', 'Mode:', 'Colormap:']):
                    label.setStyleSheet(label_style)

            # Update checkboxes with theme-appropriate colors
            checkbox_color = theme_checkbox_colors[theme_name]
            checkbox_style = f"QCheckBox {{ color: #ffffff; font-size: 11pt; font-weight: bold; padding: 3px; }} QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid {checkbox_color}; border-radius: 4px; background: #2c3e50; }} QCheckBox::indicator:checked {{ background: {checkbox_color}; border-color: {checkbox_color}; }}"
            for checkbox in [self.boundary_handling_check, self.acceleration_check, self.entropy_stopping_check, self.sharpness_stopping_check, self.residual_stopping_check, self.apply_wiener_check, self.use_p_spline_check, self.use_radial_diff_check]:
                checkbox.setStyleSheet(checkbox_style)
            
    def get_professional_blue_theme(self):
        """专业蓝色主题（暗色调）"""
        return """
        /* Main window */
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2c3e50, stop:1 #1a252f);
        }
        
        /* Group boxes */
        QGroupBox {
            font-weight: bold;
            font-size: 11pt;
            border: 2px solid #34495e;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 15px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #34495e, stop:1 #2c3e50);
            color: #ecf0f1;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 5px 12px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4361ee, stop:1 #3f37c9);
            color: white;
            border-radius: 15px;
            font-weight: bold;
        }
        
        /* Buttons */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4361ee, stop:1 #3f37c9);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 10pt;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4895ef, stop:1 #4361ee);
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #3f37c9, stop:1 #3a0ca3);
        }
        
        QPushButton:disabled {
            background: #7f8c8d;
            color: #bdc3c7;
        }
        
        /* Browse button */
        QPushButton[text="Browse..."] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #06ffa5, stop:0.5 #00b4d8, stop:1 #0077b6);
            max-width: 80px;
        }
        
        /* Input fields */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            border: 2px solid #34495e;
            border-radius: 6px;
            padding: 8px 12px;
            background: #2c3e50;
            font-size: 11pt;
            color: #ecf0f1;
            font-weight: 500;
        }

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #4361ee;
            outline: none;
            background: #1a252f;
        }

        /* ComboBox dropdown */
        QComboBox QAbstractItemView {
            border: 2px solid #34495e;
            background: #2c3e50;
            color: #ecf0f1;
            selection-background-color: #4361ee;
            selection-color: white;
            font-size: 11pt;
            padding: 5px;
            outline: none;
        }

        QComboBox QAbstractItemView::item {
            padding: 6px 12px;
            border-radius: 3px;
        }

        QComboBox QAbstractItemView::item:hover {
            background: #4361ee;
            color: white;
        }

        QComboBox QAbstractItemView::item:selected {
            background: #4361ee;
            color: white;
        }

        QComboBox::drop-down {
            border: none;
            width: 20px;
        }

        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #ecf0f1;
            width: 0;
            height: 0;
        }

        QComboBox::down-arrow:hover {
            border-top-color: #4361ee;
        }
        
        /* Labels */
        QLabel {
            color: #ecf0f1;
            font-size: 10pt;
            font-weight: 600;
        }
        
        /* Checkboxes */
        QCheckBox {
            color: #ecf0f1;
            font-size: 10pt;
            font-weight: 600;
        }
        
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #34495e;
            border-radius: 4px;
            background: #2c3e50;
        }
        
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #4361ee, stop:1 #3f37c9);
            border-color: #3f37c9;
        }
        
        /* Progress bar */
        QProgressBar {
            border: 2px solid #34495e;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
            color: white;
            background: #2c3e50;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #06ffa5, stop:0.5 #00b4d8, stop:1 #0077b6);
            border-radius: 4px;
        }
        
        /* Text edit */
        QTextEdit {
            border: 2px solid #34495e;
            border-radius: 6px;
            background: #1a252f;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 10pt;
            color: #ecf0f1;
        }
        
        /* Scroll area */
        QScrollArea {
            border: none;
            background: transparent;
        }
        
        QScrollBar:vertical {
            border: none;
            background: #2c3e50;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #34495e, stop:1 #7f8c8d);
            border-radius: 6px;
            min-height: 20px;
        }
        """
        
    def get_dark_mode_theme(self):
        """深色主题"""
        return """
        /* Main window */
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2d3748, stop:1 #1a202c);
        }
        
        /* Group boxes */
        QGroupBox {
            font-weight: bold;
            font-size: 11pt;
            border: 2px solid #4a5568;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 15px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4a5568, stop:1 #2d3748);
            color: #e2e8f0;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 5px 12px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #9f7aea, stop:1 #805ad5);
            color: white;
            border-radius: 15px;
            font-weight: bold;
        }
        
        /* Buttons */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #9f7aea, stop:1 #805ad5);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 10pt;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #b794f4, stop:1 #9f7aea);
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #805ad5, stop:1 #6b46c1);
        }
        
        QPushButton:disabled {
            background: #4a5568;
            color: #718096;
        }
        
        /* Browse button */
        QPushButton[text="Browse..."] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4fd1c5, stop:0.5 #38b2ac, stop:1 #319795);
            max-width: 80px;
        }
        
        /* Input fields */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            border: 2px solid #4a5568;
            border-radius: 6px;
            padding: 8px 12px;
            background: #2d3748;
            font-size: 11pt;
            color: #e2e8f0;
            font-weight: 500;
        }

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #9f7aea;
            outline: none;
            background: #1a202c;
        }

        /* ComboBox dropdown */
        QComboBox QAbstractItemView {
            border: 2px solid #4a5568;
            background: #2d3748;
            color: #e2e8f0;
            selection-background-color: #9f7aea;
            selection-color: white;
            font-size: 11pt;
            padding: 5px;
            outline: none;
        }

        QComboBox QAbstractItemView::item {
            padding: 6px 12px;
            border-radius: 3px;
        }

        QComboBox QAbstractItemView::item:hover {
            background: #9f7aea;
            color: white;
        }

        QComboBox QAbstractItemView::item:selected {
            background: #9f7aea;
            color: white;
        }

        QComboBox::drop-down {
            border: none;
            width: 20px;
        }

        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #e2e8f0;
            width: 0;
            height: 0;
        }

        QComboBox::down-arrow:hover {
            border-top-color: #9f7aea;
        }
        
        /* Labels */
        QLabel {
            color: #e2e8f0;
            font-size: 10pt;
            font-weight: 600;
        }
        
        /* Checkboxes */
        QCheckBox {
            color: #e2e8f0;
            font-size: 10pt;
            font-weight: 600;
        }
        
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #4a5568;
            border-radius: 4px;
            background: #2d3748;
        }
        
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #9f7aea, stop:1 #805ad5);
            border-color: #805ad5;
        }
        
        /* Progress bar */
        QProgressBar {
            border: 2px solid #4a5568;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
            color: white;
            background: #2d3748;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4fd1c5, stop:0.5 #38b2ac, stop:1 #319795);
            border-radius: 4px;
        }
        
        /* Text edit */
        QTextEdit {
            border: 2px solid #4a5568;
            border-radius: 6px;
            background: #1a202c;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 10pt;
            color: #e2e8f0;
        }
        
        /* Scroll area */
        QScrollArea {
            border: none;
            background: transparent;
        }
        
        QScrollBar:vertical {
            border: none;
            background: #2d3748;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4a5568, stop:1 #718096);
            border-radius: 6px;
            min-height: 20px;
        }
        """
        
    def get_light_clean_theme(self):
        """简洁浅色主题（暗色调）"""
        return """
        /* Main window */
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #37474f, stop:1 #263238);
        }
        
        /* Group boxes */
        QGroupBox {
            font-weight: bold;
            font-size: 11pt;
            border: 2px solid #455a64;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 15px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #455a64, stop:1 #37474f);
            color: #eceff1;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 5px 12px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2196f3, stop:1 #1976d2);
            color: white;
            border-radius: 4px;
            font-weight: bold;
        }
        
        /* Buttons */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2196f3, stop:1 #1976d2);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 10pt;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #42a5f5, stop:1 #2196f3);
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1976d2, stop:1 #1565c0);
        }
        
        QPushButton:disabled {
            background: #607d8b;
            color: #b0bec5;
        }
        
        /* Browse button */
        QPushButton[text="Browse..."] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #66bb6a, stop:1 #4caf50);
            max-width: 80px;
        }
        
        /* Input fields */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            border: 2px solid #455a64;
            border-radius: 4px;
            padding: 8px 12px;
            background: #37474f;
            font-size: 12pt;
            color: #eceff1;
            font-weight: normal;
        }

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #2196f3;
            outline: none;
            background: #263238;
        }

        /* ComboBox dropdown */
        QComboBox QAbstractItemView {
            border: 2px solid #455a64;
            background: #37474f;
            color: #eceff1;
            selection-background-color: #2196f3;
            selection-color: white;
            font-size: 12pt;
            padding: 5px;
            outline: none;
        }

        QComboBox QAbstractItemView::item {
            padding: 6px 12px;
            border-radius: 3px;
        }

        QComboBox QAbstractItemView::item:hover {
            background: #2196f3;
            color: white;
        }

        QComboBox QAbstractItemView::item:selected {
            background: #2196f3;
            color: white;
        }

        QComboBox::drop-down {
            border: none;
            width: 20px;
        }

        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #eceff1;
            width: 0;
            height: 0;
        }

        QComboBox::down-arrow:hover {
            border-top-color: #2196f3;
        }
        
        /* Labels */
        QLabel {
            color: #eceff1;
            font-size: 11pt;
            font-weight: normal;
        }
        
        /* Checkboxes */
        QCheckBox {
            color: #eceff1;
            font-size: 11pt;
            font-weight: normal;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #455a64;
            border-radius: 3px;
            background: #37474f;
        }
        
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #2196f3, stop:1 #1976d2);
            border-color: #1976d2;
        }
        
        /* Progress bar */
        QProgressBar {
            border: 2px solid #455a64;
            border-radius: 4px;
            text-align: center;
            font-weight: bold;
            color: white;
            background: #37474f;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #66bb6a, stop:1 #4caf50);
            border-radius: 3px;
        }
        
        /* Text edit */
        QTextEdit {
            border: 2px solid #455a64;
            border-radius: 4px;
            background: #263238;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 10pt;
            color: #eceff1;
        }
        
        /* Scroll area */
        QScrollArea {
            border: none;
            background: transparent;
        }
        
        QScrollBar:vertical {
            border: none;
            background: #37474f;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #455a64, stop:1 #607d8b);
            border-radius: 6px;
            min-height: 20px;
        }
        """
        
    def get_nature_green_theme(self):
        """自然绿色主题（暗色调）"""
        return """
        /* Main window */
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1b5e20, stop:1 #0d2818);
        }
        
        /* Group boxes */
        QGroupBox {
            font-weight: bold;
            font-size: 11pt;
            border: 2px solid #2e7d32;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 15px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2e7d32, stop:1 #1b5e20);
            color: #e8f5e8;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 5px 12px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #66bb6a, stop:1 #4caf50);
            color: white;
            border-radius: 15px;
            font-weight: bold;
        }
        
        /* Buttons */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #66bb6a, stop:1 #4caf50);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 10pt;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #81c784, stop:1 #66bb6a);
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4caf50, stop:1 #388e3c);
        }
        
        QPushButton:disabled {
            background: #388e3c;
            color: #81c784;
        }
        
        /* Browse button */
        QPushButton[text="Browse..."] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #26a69a, stop:0.5 #00897b, stop:1 #00695c);
            max-width: 80px;
        }
        
        /* Input fields */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            border: 2px solid #2e7d32;
            border-radius: 6px;
            padding: 8px 12px;
            background: #1b5e20;
            font-size: 11pt;
            color: #e8f5e8;
            font-weight: 500;
        }

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #66bb6a;
            outline: none;
            background: #0d2818;
        }

        /* ComboBox dropdown */
        QComboBox QAbstractItemView {
            border: 2px solid #2e7d32;
            background: #1b5e20;
            color: #e8f5e8;
            selection-background-color: #66bb6a;
            selection-color: white;
            font-size: 11pt;
            padding: 5px;
            outline: none;
        }

        QComboBox QAbstractItemView::item {
            padding: 6px 12px;
            border-radius: 3px;
        }

        QComboBox QAbstractItemView::item:hover {
            background: #66bb6a;
            color: white;
        }

        QComboBox QAbstractItemView::item:selected {
            background: #66bb6a;
            color: white;
        }

        QComboBox::drop-down {
            border: none;
            width: 20px;
        }

        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #e8f5e8;
            width: 0;
            height: 0;
        }

        QComboBox::down-arrow:hover {
            border-top-color: #66bb6a;
        }
        
        /* Labels */
        QLabel {
            color: #e8f5e8;
            font-size: 10pt;
            font-weight: 600;
        }
        
        /* Checkboxes */
        QCheckBox {
            color: #e8f5e8;
            font-size: 10pt;
            font-weight: 600;
        }
        
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #2e7d32;
            border-radius: 4px;
            background: #1b5e20;
        }
        
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #66bb6a, stop:1 #4caf50);
            border-color: #4caf50;
        }
        
        /* Progress bar */
        QProgressBar {
            border: 2px solid #2e7d32;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
            color: white;
            background: #1b5e20;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #26a69a, stop:0.5 #00897b, stop:1 #00695c);
            border-radius: 4px;
        }
        
        /* Text edit */
        QTextEdit {
            border: 2px solid #2e7d32;
            border-radius: 6px;
            background: #0d2818;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 10pt;
            color: #e8f5e8;
        }
        
        /* Scroll area */
        QScrollArea {
            border: none;
            background: transparent;
        }
        
        QScrollBar:vertical {
            border: none;
            background: #1b5e20;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2e7d32, stop:1 #388e3c);
            border-radius: 6px;
            min-height: 20px;
        }
        """
        
    def get_sunset_orange_theme(self):
        """日落橙色主题（暗色调）"""
        return """
        /* Main window */
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #e65100, stop:1 #bf360c);
        }
        
        /* Group boxes */
        QGroupBox {
            font-weight: bold;
            font-size: 11pt;
            border: 2px solid #f57c00;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 15px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f57c00, stop:1 #e65100);
            color: #fff3e0;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 5px 12px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #ff9800, stop:1 #f57c00);
            color: white;
            border-radius: 15px;
            font-weight: bold;
        }
        
        /* Buttons */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ff9800, stop:1 #f57c00);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 10pt;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ffa726, stop:1 #ff9800);
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f57c00, stop:1 #e65100);
        }
        
        QPushButton:disabled {
            background: #d84315;
            color: #ffcc02;
        }
        
        /* Browse button */
        QPushButton[text="Browse..."] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ef5350, stop:0.5 #f44336, stop:1 #d32f2f);
            max-width: 80px;
        }
        
        /* Input fields */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            border: 2px solid #f57c00;
            border-radius: 6px;
            padding: 8px 12px;
            background: #e65100;
            font-size: 11pt;
            color: #fff3e0;
            font-weight: 500;
        }

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #ff9800;
            outline: none;
            background: #bf360c;
        }

        /* ComboBox dropdown */
        QComboBox QAbstractItemView {
            border: 2px solid #f57c00;
            background: #e65100;
            color: #fff3e0;
            selection-background-color: #ff9800;
            selection-color: white;
            font-size: 11pt;
            padding: 5px;
            outline: none;
        }

        QComboBox QAbstractItemView::item {
            padding: 6px 12px;
            border-radius: 3px;
        }

        QComboBox QAbstractItemView::item:hover {
            background: #ff9800;
            color: white;
        }

        QComboBox QAbstractItemView::item:selected {
            background: #ff9800;
            color: white;
        }

        QComboBox::drop-down {
            border: none;
            width: 20px;
        }

        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #fff3e0;
            width: 0;
            height: 0;
        }

        QComboBox::down-arrow:hover {
            border-top-color: #ff9800;
        }
        
        /* Labels */
        QLabel {
            color: #fff3e0;
            font-size: 10pt;
            font-weight: 600;
        }
        
        /* Checkboxes */
        QCheckBox {
            color: #fff3e0;
            font-size: 10pt;
            font-weight: 600;
        }
        
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #f57c00;
            border-radius: 4px;
            background: #e65100;
        }
        
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ff9800, stop:1 #f57c00);
            border-color: #f57c00;
        }
        
        /* Progress bar */
        QProgressBar {
            border: 2px solid #f57c00;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
            color: white;
            background: #e65100;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #ef5350, stop:0.5 #f44336, stop:1 #d32f2f);
            border-radius: 4px;
        }
        
        /* Text edit */
        QTextEdit {
            border: 2px solid #f57c00;
            border-radius: 6px;
            background: #bf360c;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 10pt;
            color: #fff3e0;
        }
        
        /* Scroll area */
        QScrollArea {
            border: none;
            background: transparent;
        }
        
        QScrollBar:vertical {
            border: none;
            background: #e65100;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f57c00, stop:1 #d84315);
            border-radius: 6px;
            min-height: 20px;
        }
        """
        
    def create_display_panel(self):
        """创建显示面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Create tabbed display for three main areas
        self.display_tabs = QTabWidget()
        
        # Probe display tab
        probe_tab = QWidget()
        probe_layout = QVBoxLayout()
        probe_tab.setLayout(probe_layout)
        
        # Probe controls
        probe_controls = QHBoxLayout()
        space_label = QLabel("Space:")
        space_label.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9); border-radius: 3px; }")
        probe_controls.addWidget(space_label)
        self.probe_space_combo = QComboBox()
        self.probe_space_combo.addItems(["Real Space", "Frequency Space"])
        self.probe_space_combo.currentTextChanged.connect(lambda: self.update_probe_display())
        probe_controls.addWidget(self.probe_space_combo)

        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9); border-radius: 3px; }")
        probe_controls.addWidget(mode_label)
        self.probe_mode_combo = QComboBox()
        self.probe_mode_combo.addItems(["Linear", "Power", "Log"])
        self.probe_mode_combo.currentTextChanged.connect(lambda: self.update_probe_display())
        probe_controls.addWidget(self.probe_mode_combo)

        colormap_label = QLabel("Colormap:")
        colormap_label.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9); border-radius: 3px; }")
        probe_controls.addWidget(colormap_label)
        self.probe_colormap_combo = QComboBox()
        self.probe_colormap_combo.addItems(["gray", "viridis", "plasma", "inferno", "magma", "jet", "hot", "cool"])
        self.probe_colormap_combo.currentTextChanged.connect(lambda: self.update_probe_display())
        probe_controls.addWidget(self.probe_colormap_combo)
        probe_controls.addStretch()
        
        probe_layout.addLayout(probe_controls)
        
        self.probe_display = ImageDisplayWidget("Probe")
        probe_layout.addWidget(self.probe_display)
        
        # Original data display tab
        original_tab = QWidget()
        original_layout = QVBoxLayout()
        original_tab.setLayout(original_layout)
        
        # Original controls
        original_controls = QHBoxLayout()
        space_label = QLabel("Space:")
        space_label.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9); border-radius: 3px; }")
        original_controls.addWidget(space_label)
        self.original_space_combo = QComboBox()
        self.original_space_combo.addItems(["Real Space", "Frequency Space"])
        self.original_space_combo.currentTextChanged.connect(lambda: self.update_original_display())
        original_controls.addWidget(self.original_space_combo)

        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9); border-radius: 3px; }")
        original_controls.addWidget(mode_label)
        self.original_mode_combo = QComboBox()
        self.original_mode_combo.addItems(["Linear", "Power", "Log"])
        self.original_mode_combo.currentTextChanged.connect(lambda: self.update_original_display())
        original_controls.addWidget(self.original_mode_combo)

        colormap_label = QLabel("Colormap:")
        colormap_label.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9); border-radius: 3px; }")
        original_controls.addWidget(colormap_label)
        self.original_colormap_combo = QComboBox()
        self.original_colormap_combo.addItems(["gray", "viridis", "plasma", "inferno", "magma", "jet", "hot", "cool"])
        self.original_colormap_combo.currentTextChanged.connect(lambda: self.update_original_display())
        original_controls.addWidget(self.original_colormap_combo)
        original_controls.addStretch()
        
        original_layout.addLayout(original_controls)
        
        self.original_display = ImageDisplayWidget("Original Data")
        original_layout.addWidget(self.original_display)
        
        # Result display tab
        result_tab = QWidget()
        result_layout = QVBoxLayout()
        result_tab.setLayout(result_layout)
        
        # Result controls
        result_controls = QHBoxLayout()
        space_label = QLabel("Space:")
        space_label.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9); border-radius: 3px; }")
        result_controls.addWidget(space_label)
        self.result_space_combo = QComboBox()
        self.result_space_combo.addItems(["Real Space", "Frequency Space"])
        self.result_space_combo.currentTextChanged.connect(lambda: self.update_result_display())
        result_controls.addWidget(self.result_space_combo)

        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9); border-radius: 3px; }")
        result_controls.addWidget(mode_label)
        self.result_mode_combo = QComboBox()
        self.result_mode_combo.addItems(["Linear", "Power", "Log"])
        self.result_mode_combo.currentTextChanged.connect(lambda: self.update_result_display())
        result_controls.addWidget(self.result_mode_combo)

        colormap_label = QLabel("Colormap:")
        colormap_label.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; font-size: 11pt; padding: 2px 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #3f37c9); border-radius: 3px; }")
        result_controls.addWidget(colormap_label)
        self.result_colormap_combo = QComboBox()
        self.result_colormap_combo.addItems(["gray", "viridis", "plasma", "inferno", "magma", "jet", "hot", "cool"])
        self.result_colormap_combo.currentTextChanged.connect(lambda: self.update_result_display())
        result_controls.addWidget(self.result_colormap_combo)
        result_controls.addStretch()
        
        result_layout.addLayout(result_controls)
        
        self.result_display = ImageDisplayWidget("Deconvolution Result")
        result_layout.addWidget(self.result_display)
        
        # Add tabs to tab widget
        self.display_tabs.addTab(probe_tab, "🔬 Probe")
        self.display_tabs.addTab(original_tab, "📊 Original Data")
        self.display_tabs.addTab(result_tab, "🎯 Result")
        
        layout.addWidget(self.display_tabs)
        
        return panel
        
    def browse_image(self):
        """浏览图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select MRC Image File", "", 
            "MRC Files (*.mrc *.mrcs);;All Files (*)"
        )
        if file_path:
            self.image_path_edit.setText(file_path)
            
            # Try to read and display image data immediately
            try:
                if os.path.exists(file_path):
                    image_data, pixel_size = read_mrc(file_path)
                    
                    # Store original data for display
                    self.results = {'original': image_data, 'pixel_size': pixel_size}
                    
                    # Update pixel size
                    if pixel_size > 0:
                        self.pixel_size_spin.setValue(pixel_size)
                        self.statusBar().showMessage(f"Loaded pixel size: {pixel_size:.6f} nm from file")
                    else:
                        self.statusBar().showMessage("Pixel size not found in file, using default value")
                    
                    # Display original image immediately
                    self.update_original_display()
                    
                else:
                    self.statusBar().showMessage("File not found, using default pixel size")
            except Exception as e:
                self.statusBar().showMessage(f"Could not read pixel size from file: {str(e)}")
                
    def set_manual_pixel_size(self):
        """手动设置pixel size"""
        current_value = self.pixel_size_spin.value()
        value, ok = QInputDialog.getDouble(
            self, "Set Pixel Size", 
            "Enter pixel size (nm):",
            current_value, 0.001, 10.0, 6
        )
        
        if ok:
            self.pixel_size_spin.setValue(value)
            self.statusBar().showMessage(f"Pixel size manually set to: {value:.6f} nm")
            
    def browse_output(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        if dir_path:
            self.output_path_edit.setText(dir_path)
            
    def preview_probe(self):
        """预览探针"""
        # Check if image is loaded
        if not self.image_path_edit.text():
            QMessageBox.warning(self, "Warning", "Please select an image file first.")
            return
            
        if not os.path.exists(self.image_path_edit.text()):
            QMessageBox.warning(self, "Warning", "Image file not found.")
            return
            
        try:
            # Load image data
            image_data, pixel_size = read_mrc(self.image_path_edit.text())
            if pixel_size <= 0:
                pixel_size = self.pixel_size_spin.value()
            
            # Generate probe using current microscope parameters
            ctf = calculate_ctf(
                image_data.shape, pixel_size, 
                self.voltage_spin.value(), 
                self.cs3_spin.value(), self.cs5_spin.value(), 
                self.defocus_spin.value(), 
                self.obj_aperture_spin.value() / 1000.0  # mrad to rad
            )
            probe = calculate_probe(ctf, image_data.shape[1]/2, image_data.shape[0]/2)
            
            # Store probe for display
            self.results['probe'] = probe
            
            # Update probe display
            self.update_probe_display()
            
            self.statusBar().showMessage("Probe preview generated successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate probe preview: {str(e)}")
            
    def get_parameters(self):
        """获取所有参数"""
        return {
            'image_path': self.image_path_edit.text(),
            'output_path': self.output_path_edit.text(),
            'pixel_size_nm': self.pixel_size_spin.value(),
            'voltage_kv': self.voltage_spin.value(),
            'cs3_mm': self.cs3_spin.value(),
            'cs5_mm': self.cs5_spin.value(),
            'defocus_nm': self.defocus_spin.value(),
            'obj_aperture_rad': self.obj_aperture_spin.value() / 1000.0,  # mrad to rad
            'a2_amp_nm': self.a2_amp_spin.value(),
            'a2_angle_rad': self.a2_angle_spin.value(),
            'a3_amp_nm': self.a3_amp_spin.value(),
            'a3_angle_rad': self.a3_angle_spin.value(),
            'b2_amp_nm': self.b2_amp_spin.value(),
            'b2_angle_rad': self.b2_angle_spin.value(),
            'focal_spread_nm': self.focal_spread_spin.value(),
            'convergence_angle_rad': self.convergence_spin.value(),
            'algorithm': self.algorithm_group.checkedId(),  # 0: additive, 1: multiplicative, 2: fista
            'iterations': self.iterations_spin.value(),
            'lambda_reg': self.lambda_spin.value(),
            'fista_lambda_reg': self.fista_lambda_spin.value(),
            'reg_type': self.reg_type_combo.currentText(),
            'boundary_handling': self.boundary_handling_check.isChecked(),
            'acceleration': self.acceleration_check.isChecked(),
            'entropy_stopping': self.entropy_stopping_check.isChecked(),
            'sharpness_stopping': self.sharpness_stopping_check.isChecked(),
            'residual_stopping': self.residual_stopping_check.isChecked(),
            'apply_wiener': self.apply_wiener_check.isChecked(),
            'use_p_spline': self.use_p_spline_check.isChecked(),
            'use_radial_diff': self.use_radial_diff_check.isChecked(),
            'p_spline_lambda': self.p_spline_lambda_spin.value(),
            'information_limit': self.info_limit_spin.value() if self.info_limit_spin.value() > 0.1 else None,
            'damping_threshold': None  # Could add this to UI if needed
        }
        
    def start_processing(self):
        """开始处理"""
        # Validate inputs
        if not self.image_path_edit.text():
            QMessageBox.warning(self, "Warning", "Please select an image file.")
            return
            
        if not os.path.exists(self.image_path_edit.text()):
            QMessageBox.warning(self, "Warning", "Image file not found.")
            return
            
        # Disable controls
        self.process_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_text.clear()
        
        # Get parameters
        params = self.get_parameters()
        
        # Start worker thread
        self.worker = DeconvolutionWorker(params)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.processing_finished)
        self.worker.error.connect(self.processing_error)
        self.worker.start()
        
    def update_progress(self, message):
        """更新进度"""
        self.status_text.append(message)
        self.progress_bar.setValue(self.progress_bar.value() + 10)
        
    def processing_finished(self, results):
        """处理完成"""
        self.results = results
        self.progress_bar.setValue(100)
        self.status_text.append("All processing completed successfully!")
        
        # Display results
        self.display_results()
        
        # Enable save button
        self.save_btn.setEnabled(True)
        self.process_btn.setEnabled(True)
        
    def processing_error(self, error_message):
        """处理错误"""
        self.status_text.append(f"Error: {error_message}")
        QMessageBox.critical(self, "Processing Error", error_message)
        self.process_btn.setEnabled(True)

    def apply_post_filters_manually(self):
        """手动对选定目标应用后处理滤波"""
        if not self.results:
            QMessageBox.warning(self, "No Data", "Please load an image or run deconvolution first.")
            return

        target = self.filter_target_combo.currentText()
        if target == "Deconvolution Result":
            if 'result' not in self.results:
                QMessageBox.warning(self, "No Result", "No deconvolution result available. Run deconvolution first or select 'Original Image' as target.")
                return
            image = np.abs(self.results['result'])
        else:
            if 'original' not in self.results:
                QMessageBox.warning(self, "No Data", "No original image loaded.")
                return
            image = self.results['original'].copy()

        pixel_size = self.results.get('pixel_size', 0.1)
        info_limit = self.info_limit_spin.value() if self.info_limit_spin.value() > 0.1 else None

        # Apply filters in order: P-spline → Wiener → Radial Diff
        any_applied = False
        if self.use_p_spline_check.isChecked():
            self.status_text.append("Applying P-spline filter...")
            image = p_spline_wiener_filter(image, pixel_size,
                lambda_val=self.p_spline_lambda_spin.value(),
                information_limit=info_limit)
            any_applied = True
        if self.apply_wiener_check.isChecked():
            self.status_text.append("Applying radial Wiener filter...")
            image = radial_wiener_filter(image, pixel_size,
                information_limit=info_limit)
            any_applied = True
        if self.use_radial_diff_check.isChecked():
            self.status_text.append("Applying radial difference filter...")
            image = radial_difference_filter(image, pixel_size,
                information_limit=info_limit)
            any_applied = True

        if not any_applied:
            QMessageBox.information(self, "No Filter", "No post-processing filter selected. Please check at least one filter.")
            return

        # Always show filtered output in the Result panel
        self.results['result'] = image
        self.display_results()
        self.display_tabs.setCurrentIndex(2)  # Switch to Result tab
        self.status_text.append("Filter(s) applied successfully.")

    def display_results(self):
        """显示结果"""
        if not self.results:
            return
            
        # Update all displays
        self.update_probe_display()
        self.update_original_display()
        self.update_result_display()
        
    def update_probe_display(self):
        """更新探针显示"""
        if 'probe' not in self.results:
            return
            
        probe_data = self.results['probe']
        space = self.probe_space_combo.currentText()
        mode = self.probe_mode_combo.currentText()
        colormap = self.probe_colormap_combo.currentText()
        
        # Apply space transformation
        if space == "Frequency Space":
            probe_data = np.fft.fftshift(np.fft.fft2(probe_data))
        
        # Apply mode transformation
        if mode == "Power":
            probe_data = np.abs(probe_data) ** 2
        elif mode == "Log":
            probe_data = np.log1p(np.abs(probe_data))
        else:  # Linear
            probe_data = np.abs(probe_data)
            
        self.probe_display.display_image(probe_data, "Probe", colormap)
        
    def update_original_display(self):
        """更新原始数据显示"""
        if 'original' not in self.results:
            return
            
        original_data = self.results['original']
        space = self.original_space_combo.currentText()
        mode = self.original_mode_combo.currentText()
        colormap = self.original_colormap_combo.currentText()
        
        # Apply space transformation
        if space == "Frequency Space":
            original_data = np.fft.fftshift(np.fft.fft2(original_data))
        
        # Apply mode transformation
        if mode == "Power":
            original_data = np.abs(original_data) ** 2
        elif mode == "Log":
            original_data = np.log1p(np.abs(original_data))
        else:  # Linear
            original_data = np.abs(original_data)
            
        self.original_display.display_image(original_data, "Original Data", colormap)
        
    def update_result_display(self):
        """更新结果显示"""
        if 'result' not in self.results:
            return
            
        result_data = self.results['result']
        space = self.result_space_combo.currentText()
        mode = self.result_mode_combo.currentText()
        colormap = self.result_colormap_combo.currentText()
        
        # Apply space transformation
        if space == "Frequency Space":
            result_data = np.fft.fftshift(np.fft.fft2(result_data))
        
        # Apply mode transformation
        if mode == "Power":
            result_data = np.abs(result_data) ** 2
        elif mode == "Log":
            result_data = np.log1p(np.abs(result_data))
        else:  # Linear
            result_data = np.abs(result_data)
            
        self.result_display.display_image(result_data, "Deconvolution Result", colormap)
            
        # Display probe
        if 'probe' in self.results:
            self.probe_display.display_image(
                np.abs(self.results['probe']), "Probe"
            )
            
        # Display additive result
        if 'additive' in self.results:
            self.additive_display.display_image(
                np.abs(self.results['additive']), "RL Additive"
            )
            
        # Display multiplicative result
        if 'multiplicative' in self.results:
            self.multiplicative_display.display_image(
                np.abs(self.results['multiplicative']), "RL Multiplicative"
            )
            
        # Display FISTA result
        if 'fista' in self.results:
            self.fista_display.display_image(
                np.abs(self.results['fista']), "FISTA"
            )
            
        # Create comparison
        if len(self.results) > 2:  # More than just original and probe
            self.create_comparison()
            
    def create_comparison(self):
        """创建对比图"""
        results_to_compare = []
        titles = []
        
        if 'original' in self.results:
            results_to_compare.append(self.results['original'])
            titles.append('Original')
            
        if 'additive' in self.results:
            results_to_compare.append(np.abs(self.results['additive']))
            titles.append('RL Additive')
            
        if 'multiplicative' in self.results:
            results_to_compare.append(np.abs(self.results['multiplicative']))
            titles.append('RL Multiplicative')
            
        if 'fista' in self.results:
            results_to_compare.append(np.abs(self.results['fista']))
            titles.append('FISTA')
            
        if len(results_to_compare) > 1:
            # Create subplot comparison
            n = len(results_to_compare)
            cols = 2
            rows = (n + 1) // 2
            
            self.comparison_display.figure.clear()
            
            # Apply theme styling to comparison
            theme_colors = {
                "Professional Blue": {
                    "text": "#ecf0f1",
                    "spine": "#4361ee",
                    "tick": "#ecf0f1"
                },
                "Dark Mode": {
                    "text": "#e2e8f0",
                    "spine": "#9f7aea",
                    "tick": "#e2e8f0"
                },
                "Light Clean": {
                    "text": "#eceff1",
                    "spine": "#2196f3",
                    "tick": "#eceff1"
                },
                "Nature Green": {
                    "text": "#e8f5e8",
                    "spine": "#66bb6a",
                    "tick": "#e8f5e8"
                },
                "Sunset Orange": {
                    "text": "#fff3e0",
                    "spine": "#ff9800",
                    "tick": "#fff3e0"
                }
            }
            
            colors = theme_colors.get(self.current_theme, theme_colors["Professional Blue"])
            
            for i, (data, title) in enumerate(zip(results_to_compare, titles)):
                ax = self.comparison_display.figure.add_subplot(rows, cols, i+1)
                im = ax.imshow(data, cmap='gray', interpolation='nearest')
                ax.set_title(title, fontweight='bold', fontsize=9, color=colors["text"])
                ax.axis('off')
                
                # Apply theme styling
                ax.spines['bottom'].set_color(colors["spine"])
                ax.spines['top'].set_color(colors["spine"])
                ax.spines['right'].set_color(colors["spine"])
                ax.spines['left'].set_color(colors["spine"])
                ax.tick_params(axis='x', colors=colors["tick"])
                ax.tick_params(axis='y', colors=colors["tick"])
                ax.xaxis.label.set_color(colors["text"])
                ax.yaxis.label.set_color(colors["text"])
                
            self.comparison_display.figure.tight_layout()
            self.comparison_display.canvas.draw()
            
    def save_results(self):
        """保存结果"""
        if not self.results:
            QMessageBox.warning(self, "Warning", "No results to save.")
            return
            
        output_path = self.output_path_edit.text()
        os.makedirs(output_path, exist_ok=True)
        pixel_size = self.results.get('pixel_size', 0.1)
        
        # Get algorithm name for filename
        algorithm_names = ["additive", "multiplicative", "fista"]
        algorithm_id = self.algorithm_group.checkedId()
        algorithm_name = algorithm_names[algorithm_id] if 0 <= algorithm_id < len(algorithm_names) else "result"
        
        try:
            # Save original data
            if 'original' in self.results:
                original_path = os.path.join(output_path, "original.mrc")
                write_mrc(original_path, self.results['original'], pixel_size)
                self.status_text.append(f"Saved: {original_path}")
                
            # Save probe
            if 'probe' in self.results:
                probe_path = os.path.join(output_path, "probe.mrc")
                write_mrc(probe_path, self.results['probe'], pixel_size)
                self.status_text.append(f"Saved: {probe_path}")
                
            # Save result
            if 'result' in self.results:
                result_path = os.path.join(output_path, f"result_{algorithm_name}.mrc")
                write_mrc(result_path, np.abs(self.results['result']), pixel_size)
                self.status_text.append(f"Saved: {result_path}")
                
            QMessageBox.information(self, "Success", "Results saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save results: {str(e)}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Create window and apply default theme
    window = DeconvolutionGUI()
    window.apply_theme("dark_mode", "Dark Mode")
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()