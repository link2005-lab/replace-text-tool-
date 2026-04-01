import sys
import os
import json
import pyperclip
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QPushButton, QLabel, QLineEdit,
                             QMessageBox, QRadioButton, QButtonGroup, QSplitter)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QIcon

# 获取资源路径（兼容源码运行和打包后的 exe）
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# 配置文件路径（与 EXE 同目录）
def get_config_path():
    """获取配置文件路径（兼容源码运行和打包后的 exe）"""
    return os.path.join(get_base_path(), 'config.json')

CONFIG_PATH = get_config_path()
ICON_PATH = os.path.join(get_base_path(), 'app_icon.ico')


class TextReplaceDeleteTool(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_config()  # 启动时读取配置

    def init_ui(self):
        # 窗口基础设置
        self.setWindowTitle('文本替换删除工具 1.0beta')
        self.setGeometry(100, 100, 490, 480)
        self.setMinimumSize(490, 480)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # ── 1. 粘贴区 ──────────────────────────────────────────
        paste_label = QLabel('粘贴替换的文字（双击清空）：')
        self.paste_text_edit = QTextEdit()
        self.paste_text_edit.mouseDoubleClickEvent = self.clear_paste_text

        paste_btn_layout = QHBoxLayout()
        self.paste_btn = QPushButton('粘贴')
        self.paste_btn.clicked.connect(self.paste_text)
        paste_btn_layout.addStretch(1)
        paste_btn_layout.addWidget(self.paste_btn)

        main_layout.addWidget(paste_label)
        main_layout.addWidget(self.paste_text_edit)
        main_layout.addLayout(paste_btn_layout)
        main_layout.addSpacing(6)

        # ── 2. 左右分栏（批量删除 | 单独替换）─────────────────
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(8)

        # 单选组（两个 RadioButton 互斥）
        self.mode_group = QButtonGroup(self)

        # ── 左栏：批量删除 ──
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)

        left_header = QHBoxLayout()
        self.delete_radio = QRadioButton('批量删除的文字')
        self.delete_radio.setChecked(True)   # 默认选中
        self.mode_group.addButton(self.delete_radio, 0)
        left_header.addWidget(self.delete_radio)
        left_header.addStretch(1)

        self.delete_text_edit = QTextEdit()
        self.delete_text_edit.setPlaceholderText('一行一个要删除的内容\n双击可清空')
        self.delete_text_edit.mouseDoubleClickEvent = self.clear_delete_text

        left_layout.addLayout(left_header)
        left_layout.addWidget(self.delete_text_edit)

        # ── 右栏：单独替换 ──
        right_layout = QVBoxLayout()
        right_layout.setSpacing(4)

        right_header = QHBoxLayout()
        self.replace_radio = QRadioButton('单独替换')
        self.replace_radio.setChecked(False)
        self.mode_group.addButton(self.replace_radio, 1)
        right_header.addWidget(self.replace_radio)
        right_header.addStretch(1)

        self.replace_text_edit = QTextEdit()
        self.replace_text_edit.setPlaceholderText(
            '格式：旧内容>>新内容\n'
            '例：123>>000  （把123替换成000）\n'
            '例：abc>>      （把abc替换成一个空格）\n'
            '双击可清空'
        )
        self.replace_text_edit.mouseDoubleClickEvent = self.clear_replace_text

        right_layout.addLayout(right_header)
        right_layout.addWidget(self.replace_text_edit)

        columns_layout.addLayout(left_layout, 1)
        columns_layout.addLayout(right_layout, 1)
        main_layout.addLayout(columns_layout)

        # ── 3. 删除位数 + 按钮行 ────────────────────────────────
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        self.front_num_label = QLabel('删除前面几位：')
        self.front_num_edit = QLineEdit('1')
        self.front_num_edit.setFixedWidth(45)
        self.front_num_edit.setAlignment(Qt.AlignCenter)

        self.back_num_label = QLabel('删除后面几位：')
        self.back_num_edit = QLineEdit('0')
        self.back_num_edit.setFixedWidth(45)
        self.back_num_edit.setAlignment(Qt.AlignCenter)

        self.save_cfg_btn = QPushButton('💾 保存配置')
        self.save_cfg_btn.clicked.connect(self.save_config_manually)
        self.exec_btn = QPushButton('执行')
        self.exec_btn.setFixedWidth(60)
        self.exec_btn.clicked.connect(self.process_text)

        bottom_bar.addWidget(self.front_num_label)
        bottom_bar.addWidget(self.front_num_edit)
        bottom_bar.addSpacing(12)
        bottom_bar.addWidget(self.back_num_label)
        bottom_bar.addWidget(self.back_num_edit)
        bottom_bar.addStretch(1)
        bottom_bar.addWidget(self.save_cfg_btn)
        bottom_bar.addSpacing(6)
        bottom_bar.addWidget(self.exec_btn)
        main_layout.addLayout(bottom_bar)

        # ── 4. 输出区 ───────────────────────────────────────────
        output_label = QLabel('输出的文字（已复制到剪贴板）：')
        self.output_text_edit = QTextEdit()
        self.output_text_edit.setReadOnly(True)

        main_layout.addWidget(output_label)
        main_layout.addWidget(self.output_text_edit)

        self.setLayout(main_layout)

    # ─────────────── 配置读写 ───────────────────────────────────
    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            self.delete_text_edit.setPlainText(cfg.get('delete_text', ''))
            self.replace_text_edit.setPlainText(cfg.get('replace_text', ''))
            self.front_num_edit.setText(str(cfg.get('front_num', '1')))
            self.back_num_edit.setText(str(cfg.get('back_num', '0')))
            # mode: 0 = 批量删除, 1 = 单独替换
            mode = cfg.get('mode', 0)
            if mode == 1:
                self.replace_radio.setChecked(True)
            else:
                self.delete_radio.setChecked(True)
        except Exception as e:
            QMessageBox.warning(self, '提示', f'读取配置失败：{str(e)}')

    def save_config(self):
        try:
            cfg = {
                'delete_text':  self.delete_text_edit.toPlainText(),
                'replace_text': self.replace_text_edit.toPlainText(),
                'front_num':    self.front_num_edit.text().strip(),
                'back_num':     self.back_num_edit.text().strip(),
                'mode':         self.mode_group.checkedId(),  # 0 或 1
            }
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, '提示', f'保存配置失败：{str(e)}')

    @pyqtSlot()
    def save_config_manually(self):
        self.save_config()
        QMessageBox.information(self, '成功', f'配置已保存到：\n{CONFIG_PATH}')

    def closeEvent(self, event):
        self.save_config()
        event.accept()

    # ─────────────── 清空事件 ───────────────────────────────────
    @pyqtSlot()
    def paste_text(self):
        try:
            self.paste_text_edit.setPlainText(pyperclip.paste())
        except Exception as e:
            QMessageBox.warning(self, '提示', f'粘贴失败：{str(e)}')

    def clear_paste_text(self, event):
        self.paste_text_edit.clear()
        event.accept()

    def clear_delete_text(self, event):
        self.delete_text_edit.clear()
        event.accept()

    def clear_replace_text(self, event):
        self.replace_text_edit.clear()
        event.accept()

    # ─────────────── 核心处理 ───────────────────────────────────
    @pyqtSlot()
    def process_text(self):
        try:
            source_text = self.paste_text_edit.toPlainText().strip()
            if not source_text:
                QMessageBox.warning(self, '提示', '请先粘贴需要处理的文字！')
                return

            front_num = int(self.front_num_edit.text().strip())
            back_num  = int(self.back_num_edit.text().strip())

            # ── 批量删除列表（选中左栏才生效）──
            delete_list = []
            if self.delete_radio.isChecked():
                raw = self.delete_text_edit.toPlainText()
                delete_list = [line for line in raw.split('\n') if line]
                # 注意：这里不 strip()，保留原始内容（空格也算有效关键词）

            # ── 单独替换规则（选中右栏才生效）──
            replace_pairs = []
            if self.replace_radio.isChecked():
                raw = self.replace_text_edit.toPlainText()
                for line in raw.split('\n'):
                    if '>>' in line:
                        # 只在第一个 >> 处分割，保留右侧所有内容（包含空格）
                        idx = line.index('>>')
                        old = line[:idx]
                        new = line[idx + 2:]  # >> 占 2 个字符，右侧全部保留
                        if old:  # 旧内容不能为空
                            replace_pairs.append((old, new))

            # ── 逐行处理 ──
            processed_lines = []
            for line in source_text.split('\n'):
                if not line.strip():
                    processed_lines.append('')
                    continue

                cur = line

                # 步骤1：批量删除
                for item in delete_list:
                    cur = cur.replace(item, '')

                # 步骤2：单独替换
                for old, new in replace_pairs:
                    cur = cur.replace(old, new)

                # 步骤3：删除前面几位
                if front_num > 0 and len(cur) >= front_num:
                    cur = cur[front_num:]

                # 步骤4：删除后面几位
                if back_num > 0 and len(cur) >= back_num:
                    cur = cur[:-back_num]

                processed_lines.append(cur)

            result_text = '\n'.join(processed_lines)
            self.output_text_edit.setPlainText(result_text)
            pyperclip.copy(result_text)
            self.save_config()
            QMessageBox.information(self, '成功', '处理完成，结果已复制到剪贴板！')

        except ValueError:
            QMessageBox.critical(self, '错误', '删除前后位数请输入有效数字！')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'处理失败：{str(e)}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    tool = TextReplaceDeleteTool()
    tool.show()
    sys.exit(app.exec())
