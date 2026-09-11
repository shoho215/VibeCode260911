"""네이버 금융 KOSPI200 편입종목상위 정보를 수집하는 GUI 프로그램."""

from __future__ import annotations

import csv
import sys
from dataclasses import asdict, dataclass
from urllib.parse import urljoin

from openpyxl import Workbook
from openpyxl.styles import Font
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
import requests
from bs4 import BeautifulSoup


URL = "https://finance.naver.com/sise/sise_index.naver?code=KPI200"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}
TABLE_HEADERS = (
    "종목별",
    "현재가",
    "전일비",
    "등락률",
    "거래량",
    "거래대금(백만)",
    "시가총액(억)",
)


@dataclass
class Stock:
    name: str
    price: str
    change: str
    change_rate: str
    volume: str
    trading_value: str
    market_cap: str


def fetch_soup(url: str = URL) -> BeautifulSoup:
    """네이버 금융 페이지를 요청하고 BeautifulSoup 객체를 반환한다."""
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, "html.parser")

    iframe = soup.select_one("iframe[title*='편입종목상위']")
    if iframe and iframe.get("src"):
        table_response = requests.get(
            urljoin(url, iframe["src"]), headers=HEADERS, timeout=15
        )
        table_response.raise_for_status()
        table_response.encoding = table_response.apparent_encoding or table_response.encoding
        return BeautifulSoup(table_response.text, "html.parser")
    return soup


def find_constituent_table(soup: BeautifulSoup):
    """헤더 조합으로 편입종목상위 표를 찾는다."""
    expected_headers = set(TABLE_HEADERS)
    for table in soup.select("table"):
        header_cells = table.select_one("tr")
        if not header_cells:
            continue
        headers = {
            "".join(cell.stripped_strings)
            for cell in header_cells.select("th, td")
        }
        if expected_headers.issubset(headers):
            return table
    raise ValueError("편입종목상위 표를 찾지 못했습니다.")


def crawl_stocks(soup: BeautifulSoup) -> list[Stock]:
    """편입종목상위 표의 종목 정보를 추출한다."""
    table = find_constituent_table(soup)
    stocks: list[Stock] = []

    for row in table.select("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
        if len(cells) != len(TABLE_HEADERS) or cells[0] == TABLE_HEADERS[0]:
            continue
        if not cells[0]:
            continue
        stocks.append(Stock(*cells))

    if not stocks:
        raise ValueError("편입종목상위 표에서 종목 데이터를 찾지 못했습니다.")
    return stocks


def save_csv(stocks: list[Stock], filename: str) -> None:
    """수집 결과를 UTF-8 BOM CSV 파일로 저장한다."""
    with open(filename, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=Stock.__annotations__.keys())
        writer.writeheader()
        writer.writerows(asdict(stock) for stock in stocks)


def save_excel(stocks: list[Stock], filename: str) -> None:
    """크롤링한 종목 목록을 Excel 파일로 저장한다."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "KOSPI200"
    worksheet.append(list(TABLE_HEADERS))

    for cell in worksheet[1]:
        cell.font = Font(bold=True)

    for stock in stocks:
        worksheet.append(list(asdict(stock).values()))

    widths = (18, 14, 14, 12, 16, 18, 18)
    for index, width in enumerate(widths, start=1):
        worksheet.column_dimensions[chr(64 + index)].width = width
    worksheet.freeze_panes = "A2"
    workbook.save(filename)


class KospiWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.stocks: list[Stock] = []
        self.setWindowTitle("KOSPI200 종목 조회")
        self.resize(1_100, 600)

        self.status_label = QLabel("크롤링 버튼을 눌러 종목을 조회하세요.")

        self.crawl_button = QPushButton("KOSPI200 크롤링")
        self.crawl_button.clicked.connect(self.load_stocks)
        self.excel_button = QPushButton("Excel로 저장")
        self.excel_button.setEnabled(False)
        self.excel_button.clicked.connect(self.export_excel)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.crawl_button)
        button_layout.addWidget(self.excel_button)
        button_layout.addStretch()

        self.stock_table = QTableWidget(0, len(TABLE_HEADERS))
        self.stock_table.setHorizontalHeaderLabels(list(TABLE_HEADERS))
        self.stock_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.stock_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.stock_table.setAlternatingRowColors(True)
        self.stock_table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.stock_table)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_stocks(self):
        self.crawl_button.setEnabled(False)
        self.excel_button.setEnabled(False)
        self.status_label.setText("KOSPI200 종목을 크롤링하는 중입니다...")
        QApplication.processEvents()

        try:
            self.stocks = crawl_stocks(fetch_soup())
            self.show_stocks(self.stocks)
            self.excel_button.setEnabled(True)
            self.status_label.setText(
                f"총 {len(self.stocks)}개 종목을 조회했습니다."
            )
        except (requests.RequestException, ValueError) as error:
            self.stocks = []
            self.stock_table.setRowCount(0)
            self.status_label.setText("크롤링에 실패했습니다.")
            QMessageBox.critical(self, "크롤링 오류", str(error))
        finally:
            self.crawl_button.setEnabled(True)

    def show_stocks(self, stocks: list[Stock]):
        self.stock_table.setRowCount(len(stocks))
        for row_index, stock in enumerate(stocks):
            for column_index, value in enumerate(asdict(stock).values()):
                item = QTableWidgetItem(str(value))
                if column_index > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.stock_table.setItem(row_index, column_index, item)
        self.stock_table.resizeColumnsToContents()

    def export_excel(self):
        if not self.stocks:
            QMessageBox.information(self, "저장 안내", "저장할 종목 데이터가 없습니다.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Excel 파일 저장",
            "kospi200_stocks.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not filename:
            return

        try:
            save_excel(self.stocks, filename)
        except OSError as error:
            QMessageBox.critical(self, "저장 오류", str(error))
            return
        QMessageBox.information(self, "저장 완료", f"Excel 파일을 저장했습니다.\n{filename}")


def main() -> None:
    app = QApplication(sys.argv)
    window = KospiWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()