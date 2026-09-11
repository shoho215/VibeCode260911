"""네이버 뉴스 검색 결과에서 기사 제목과 본문을 수집하는 예제."""

from __future__ import annotations

import csv
import time
from dataclasses import asdict, dataclass
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


DEFAULT_URL = (
    "https://search.naver.com/search.naver?sm=tab_hty.top&where=nexearch&"
    "ssc=tab.nx.all&query=AI&oquery=AI%5C&tqi=jbh9Cdqo1SCssDDWnaGssssstIN-045342&"
    "ackey=r0afict9"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


@dataclass
class Article:
    title: str
    url: str
    press: str
    content: str


def make_search_url(url: str, query: str | None) -> str:
    """네이버 뉴스 탭 URL로 정규화하고 검색어를 적용한다."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params["where"] = ["news"]
    if query:
        params["query"] = [query]
    return parsed._replace(query=urlencode(params, doseq=True)).geturl()


def fetch_soup(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return BeautifulSoup(response.text, "html.parser")


def collect_search_results(soup: BeautifulSoup, limit: int) -> list[tuple[str, str, str]]:
    """네이버 뉴스 검색 결과에서 실제 기사 제목 링크를 추출한다."""
    results: list[tuple[str, str, str]] = []
    seen_urls: set[str] = set()

    title_tags = soup.select(
        "a.news_tit, a.sds-comps-text-type-headline1, "
        "a[class*='headline'], a[class*='title']"
    )
    for title_tag in title_tags:
        item = title_tag.find_parent(["div", "li", "article"]) or title_tag.parent
        if not title_tag:
            continue

        article_url = urljoin("https://search.naver.com", title_tag.get("href", ""))
        if not is_article_url(article_url) or article_url in seen_urls:
            continue

        title = title_tag.get_text(" ", strip=True)
        press_tag = item.select_one(
            "a.info.press, .info_group .press, .press, "
            ".sds-comps-text-type-body2"
        )
        press = press_tag.get_text(" ", strip=True) if press_tag else ""
        results.append((title, article_url, press))
        seen_urls.add(article_url)
        if len(results) >= limit:
            break

    # 네이버 마크업이 바뀌어 제목 클래스가 없어도 기사 링크를 수집한다.
    if len(results) < limit:
        for link in soup.select("a[href]"):
            article_url = urljoin("https://search.naver.com", link.get("href", ""))
            title = link.get_text(" ", strip=True)
            if len(title) < 8 or not is_article_url(article_url) or article_url in seen_urls:
                continue
            results.append((title, article_url, ""))
            seen_urls.add(article_url)
            if len(results) >= limit:
                break

    return results


def is_article_url(url: str) -> bool:
    """검색 결과 링크 중 검색/로그인/광고 링크를 제외한다."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    blocked_hosts = ("search.naver.com", "m.search.naver.com", "nid.naver.com")
    if parsed.netloc.lower() in blocked_hosts:
        return False
    blocked_words = ("ad.naver.com", "shopping.naver.com", "tv.naver.com")
    return not any(host in parsed.netloc.lower() for host in blocked_words)


def extract_article_content(soup: BeautifulSoup) -> str:
    """주요 언론사에서 자주 사용하는 본문 선택자를 순서대로 시도한다."""
    selectors = (
        "#dic_area",                  # 연합뉴스, 일부 네이버 뉴스
        "#newsct_article",            # 네이버 뉴스 본문
        ".article_view",              # 일반 언론사
        ".article-body",
        ".article_body",
        "[itemprop='articleBody']",
        ".news_end",
    )
    for selector in selectors:
        content_tag = soup.select_one(selector)
        if content_tag:
            for tag in content_tag.select(
                "script, style, aside, figure, .ad, "
                ".article_footer, .copyright"
            ):
                tag.decompose()
            content = content_tag.get_text(" ", strip=True)
            if content:
                return content

    description = soup.select_one("meta[property='og:description'], meta[name='description']")
    if description and description.get("content"):
        return description["content"].strip()
    return "본문 선택자를 찾지 못했습니다. 해당 언론사의 선택자를 추가하세요."


def crawl_articles(search_url: str, query: str | None, limit: int, delay: float) -> list[Article]:
    session = requests.Session()
    search_soup = fetch_soup(session, make_search_url(search_url, query))
    search_results = collect_search_results(search_soup, limit)
    articles: list[Article] = []

    for index, (title, url, press) in enumerate(search_results):
        try:
            article_soup = fetch_soup(session, url)
            content = extract_article_content(article_soup)
        except requests.RequestException as error:
            content = f"기사 요청 실패: {error}"

        articles.append(Article(title, url, press, content))
        if index < len(search_results) - 1:
            time.sleep(delay)

    return articles


def save_csv(articles: list[Article], filename: str) -> None:
    with open(filename, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=Article.__annotations__.keys())
        writer.writeheader()
        writer.writerows(asdict(article) for article in articles)


def save_excel(articles: list[Article], filename: str) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "뉴스 기사"

    headers = ["제목", "기사 링크", "언론사", "본문"]
    worksheet.append(headers)
    for cell in worksheet[1]:
        cell.font = Font(bold=True)

    for article in articles:
        worksheet.append([article.title, article.url, article.press, article.content])

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    worksheet.column_dimensions["A"].width = 40
    worksheet.column_dimensions["B"].width = 60
    worksheet.column_dimensions["C"].width = 18
    worksheet.column_dimensions["D"].width = 100

    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = cell.alignment.copy(wrap_text=True, vertical="top")

    workbook.save(filename)


class CrawlWorker(QThread):
    completed = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, query: str, limit: int) -> None:
        super().__init__()
        self.query = query
        self.limit = limit

    def run(self) -> None:
        try:
            articles = crawl_articles(DEFAULT_URL, self.query, self.limit, 0.5)
            self.completed.emit(articles)
        except requests.RequestException as error:
            self.failed.emit(f"네이버 요청에 실패했습니다.\n{error}")
        except Exception as error:
            self.failed.emit(f"크롤링 중 오류가 발생했습니다.\n{error}")


class NewsCrawlerWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.articles: list[Article] = []
        self.worker: CrawlWorker | None = None
        self.setWindowTitle("네이버 뉴스 크롤러")
        self.resize(1100, 650)

        self.query_edit = QLineEdit("AI")
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 100)
        self.limit_spin.setValue(10)
        self.search_button = QPushButton("기사 조회")
        self.save_button = QPushButton("엑셀 저장")
        self.save_button.setEnabled(False)
        self.status_label = QLabel("검색어를 입력하고 기사 조회를 누르세요.")

        form = QFormLayout()
        form.addRow("검색어", self.query_edit)
        form.addRow("기사 수", self.limit_spin)

        buttons = QHBoxLayout()
        buttons.addWidget(self.search_button)
        buttons.addWidget(self.save_button)
        buttons.addStretch()

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["제목", "언론사", "링크", "본문"])
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 300)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)

        self.search_button.clicked.connect(self.start_crawl)
        self.save_button.clicked.connect(self.save_results)

    def start_crawl(self) -> None:
        query = self.query_edit.text().strip()
        if not query:
            QMessageBox.warning(self, "입력 확인", "검색어를 입력하세요.")
            return

        self.search_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.table.setRowCount(0)
        self.status_label.setText("기사를 조회하는 중입니다...")
        self.worker = CrawlWorker(query, self.limit_spin.value())
        self.worker.completed.connect(self.show_results)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.worker.start()

    def show_results(self, articles: list[Article]) -> None:
        self.articles = articles
        self.table.setRowCount(len(articles))
        for row, article in enumerate(articles):
            values = [article.title, article.press, article.url, article.content]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.search_button.setEnabled(True)
        self.save_button.setEnabled(bool(articles))
        self.status_label.setText(f"{len(articles)}개의 기사를 조회했습니다.")

    def show_error(self, message: str) -> None:
        self.search_button.setEnabled(True)
        self.status_label.setText("조회에 실패했습니다.")
        QMessageBox.critical(self, "크롤링 오류", message)

    def save_results(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "엑셀 파일 저장",
            "naverresult.xlsx",
            "Excel 파일 (*.xlsx)",
        )
        if filename:
            save_excel(self.articles, filename)
            self.status_label.setText(f"엑셀 파일을 저장했습니다: {filename}")


def main() -> None:
    app = QApplication([])
    window = NewsCrawlerWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()