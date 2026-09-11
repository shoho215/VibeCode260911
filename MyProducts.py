import sqlite3
from contextlib import contextmanager
from pathlib import Path

from openpyxl import Workbook
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


DB_FILE = Path(__file__).with_name("products.db")


@contextmanager
def get_connection():
    """SQLite 데이터베이스 연결을 반환합니다."""
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()


def create_table():
    """Products 테이블이 없으면 생성합니다."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS Products (
                productID INTEGER PRIMARY KEY AUTOINCREMENT,
                productName TEXT NOT NULL,
                productPrice INTEGER NOT NULL CHECK (productPrice >= 0)
            )
            """
        )


def insert_product(product_name, product_price):
    """제품을 추가하고 생성된 productID를 반환합니다."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO Products (productName, productPrice)
            VALUES (?, ?)
            """,
            (product_name, product_price),
        )
        return cursor.lastrowid


def update_product(product_id, product_name, product_price):
    """productID에 해당하는 제품을 수정하고 성공 여부를 반환합니다."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE Products
            SET productName = ?, productPrice = ?
            WHERE productID = ?
            """,
            (product_name, product_price, product_id),
        )
        return cursor.rowcount > 0


def delete_product(product_id):
    """productID에 해당하는 제품을 삭제하고 성공 여부를 반환합니다."""
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM Products WHERE productID = ?",
            (product_id,),
        )
        return cursor.rowcount > 0


def search_products(keyword=""):
    """제품명에 keyword가 포함된 제품을 productID 순서로 조회합니다."""
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT productID, productName, productPrice
            FROM Products
            WHERE productName LIKE ?
            ORDER BY productID
            """,
            (f"%{keyword}%",),
        ).fetchall()


def print_products(products):
    """조회된 제품 목록을 화면에 출력합니다."""
    if not products:
        print("조회된 제품이 없습니다.")
        return

    print("\nID\t제품명\t가격")
    print("-" * 35)
    for product in products:
        print(
            f"{product['productID']}\t"
            f"{product['productName']}\t"
            f"{product['productPrice']:,}원"
        )


def read_price():
    """0 이상의 정수 가격을 입력받습니다."""
    while True:
        try:
            price = int(input("제품 가격: "))
            if price < 0:
                raise ValueError
            return price
        except ValueError:
            print("가격은 0 이상의 정수로 입력하세요.")


class ProductWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Products 관리")
        self.resize(700, 500)
        self.selected_product_id = None

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("제품명을 입력하세요")
        self.price_input = QSpinBox()
        self.price_input.setRange(0, 2_147_483_647)
        self.price_input.setSuffix(" 원")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색할 제품명")

        form_layout = QFormLayout()
        form_layout.addRow("제품명", self.name_input)
        form_layout.addRow("제품 가격", self.price_input)

        add_button = QPushButton("입력")
        add_button.clicked.connect(self.add_product)
        update_button = QPushButton("수정")
        update_button.clicked.connect(self.edit_product)
        delete_button = QPushButton("삭제")
        delete_button.clicked.connect(self.remove_product)
        clear_button = QPushButton("입력 초기화")
        clear_button.clicked.connect(self.clear_inputs)

        input_buttons = QHBoxLayout()
        input_buttons.addWidget(add_button)
        input_buttons.addWidget(update_button)
        input_buttons.addWidget(delete_button)
        input_buttons.addWidget(clear_button)

        search_button = QPushButton("검색")
        search_button.clicked.connect(self.search)
        show_all_button = QPushButton("전체 조회")
        show_all_button.clicked.connect(self.load_products)
        excel_button = QPushButton("Excel로 저장")
        excel_button.clicked.connect(self.export_to_excel)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("제품 검색"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        search_layout.addWidget(show_all_button)
        search_layout.addWidget(excel_button)

        self.product_table = QTableWidget(0, 3)
        self.product_table.setHorizontalHeaderLabels(
            ["상품 ID", "상품명", "가격"]
        )
        self.product_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.product_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.product_table.cellClicked.connect(self.select_product)
        self.product_table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addLayout(input_buttons)
        layout.addLayout(search_layout)
        layout.addWidget(self.product_table)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.load_products()

    def load_products(self):
        self.show_products(search_products())

    def search(self):
        self.show_products(search_products(self.search_input.text().strip()))

    def show_products(self, products):
        if not products:
            self.product_table.setRowCount(1)
            empty_item = QTableWidgetItem("조회된 제품이 없습니다.")
            empty_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.product_table.setItem(0, 0, empty_item)
            self.product_table.setSpan(0, 0, 1, 3)
            return

        self.product_table.setRowCount(len(products))
        for row_index, product in enumerate(products):
            values = (
                product["productID"],
                product["productName"],
                f"{product['productPrice']:,}원",
            )
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column_index in (0, 2):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.product_table.setItem(row_index, column_index, item)
        self.product_table.resizeColumnsToContents()

    def select_product(self, row, _column):
        self.selected_product_id = int(
            self.product_table.item(row, 0).text()
        )
        self.name_input.setText(self.product_table.item(row, 1).text())
        price_text = self.product_table.item(row, 2).text().replace(",", "")
        self.price_input.setValue(int(price_text.replace("원", "").strip()))

    def add_product(self):
        product_name = self.name_input.text().strip()
        if not product_name:
            QMessageBox.warning(self, "입력 오류", "제품명을 입력하세요.")
            return
        product_id = insert_product(product_name, self.price_input.value())
        self.load_products()
        self.clear_inputs()
        self.statusBar().showMessage(f"제품이 입력되었습니다. ID: {product_id}")

    def edit_product(self):
        if self.selected_product_id is None:
            QMessageBox.warning(self, "수정 오류", "수정할 제품을 목록에서 선택하세요.")
            return
        product_name = self.name_input.text().strip()
        if not product_name:
            QMessageBox.warning(self, "입력 오류", "제품명을 입력하세요.")
            return
        update_product(
            self.selected_product_id,
            product_name,
            self.price_input.value(),
        )
        self.load_products()
        self.clear_inputs()
        self.statusBar().showMessage("제품이 수정되었습니다.")

    def remove_product(self):
        if self.selected_product_id is None:
            QMessageBox.warning(self, "삭제 오류", "삭제할 제품을 목록에서 선택하세요.")
            return
        answer = QMessageBox.question(
            self,
            "삭제 확인",
            "선택한 제품을 삭제하시겠습니까?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            delete_product(self.selected_product_id)
            self.load_products()
            self.clear_inputs()
            self.statusBar().showMessage("제품이 삭제되었습니다.")

    def clear_inputs(self):
        self.selected_product_id = None
        self.name_input.clear()
        self.price_input.setValue(0)
        self.product_table.clearSelection()

    def export_to_excel(self):
        products = search_products()
        if not products:
            QMessageBox.information(self, "저장 안내", "저장할 제품 데이터가 없습니다.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel 파일 저장",
            "products.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not file_path:
            return

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Products"
        worksheet.append(["productID", "productName", "productPrice"])
        for product in products:
            worksheet.append(
                [
                    product["productID"],
                    product["productName"],
                    product["productPrice"],
                ]
            )
        worksheet.column_dimensions["A"].width = 12
        worksheet.column_dimensions["B"].width = 25
        worksheet.column_dimensions["C"].width = 15
        workbook.save(file_path)
        QMessageBox.information(self, "저장 완료", f"Excel 파일을 저장했습니다.\n{file_path}")


if __name__ == "__main__":
    create_table()
    app = QApplication([])
    window = ProductWindow()
    window.show()
    app.exec()
