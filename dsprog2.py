import flet as ft
import requests
import sqlite3
from datetime import datetime
from typing import List, Dict, Any

INIT_DATABASE_SQL = """
CREATE TABLE IF NOT EXISTS areas (
    area_code TEXT PRIMARY KEY,
    area_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS weather_forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_code TEXT NOT NULL,
    forecast_date TEXT NOT NULL,
    weather_condition TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (area_code) REFERENCES areas (area_code),
    UNIQUE(area_code, forecast_date)
);
"""

class WeatherDatabase:
    """天気情報を管理するSQLiteデータベースクラス"""

    def __init__(self, db_path: str = "weather.db"):
        self.db_path = db_path
        self.initialize_database()

    def initialize_database(self):
        """データベース初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.executescript(INIT_DATABASE_SQL)
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")

    def save_area(self, area_code: str, area_name: str):
        """エリア情報を保存"""
        now = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO areas (area_code, area_name, created_at) VALUES (?, ?, ?)",
                    (area_code, area_name, now),
                )
        except sqlite3.Error as e:
            print(f"Failed to save area: {e}")

    def save_weather(self, area_code: str, date: str, condition: str):
        """天気情報を保存"""
        now = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO weather_forecasts 
                    (area_code, forecast_date, weather_condition, created_at) VALUES (?, ?, ?, ?)""",
                    (area_code, date, condition, now),
                )
        except sqlite3.Error as e:
            print(f"Failed to save weather: {e}")

    def get_weather_dates(self, area_code: str) -> List[str]:
        """指定エリアの天気情報の日付を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT forecast_date FROM weather_forecasts WHERE area_code = ?",
                    (area_code,),
                )
                rows = cursor.fetchall()
                return [r[0] for r in rows]
        except sqlite3.Error as e:
            print(f"Failed to fetch weather dates: {e}")
            return []

    def get_weather_by_date(self, area_code: str, date: str) -> Dict[str, Any]:
        """指定エリアと日付の天気情報を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT forecast_date, weather_condition FROM weather_forecasts WHERE area_code = ? AND forecast_date = ?",
                    (area_code, date),
                )
                row = cursor.fetchone()
                return {"date": row[0], "condition": row[1]} if row else {}
        except sqlite3.Error as e:
            print(f"Failed to fetch weather: {e}")
            return {}

# 天気データ取得関数
def fetch_weather(area_code: str) -> List[Dict]:
    """APIから天気情報を取得し、日付と天気を対応付けてリストとして返す"""
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        forecasts = []
        # データ構造を解析して日付と天気を取得
        for area in data:
            for time_series in area.get("timeSeries", []):
                times = time_series.get("timeDefines", [])
                weathers = time_series.get("areas", [{}])[0].get("weathers", [])

                # timeDefines（日付）とweathers（天気）を1対1でマッピング
                for idx in range(min(len(times), len(weathers))):
                    date = times[idx]
                    condition = weathers[idx]
                    forecasts.append({"date": date, "condition": condition})
        return forecasts
    except requests.RequestException as e:
        print(f"Weather API request failed: {e}")
        return []

# 天気データ取得後、日付リストを表示
def on_area_selected(e):
    selected_code = area_dropdown.value
    if not selected_code:
        return

    # 天気データ取得
    weather_data = fetch_weather(selected_code)
    date_dropdown.options.clear()

    # 天気データを保存して日付ドロップダウンを更新
    for entry in weather_data:
        db.save_weather(selected_code, entry["date"], entry["condition"])
        date_dropdown.options.append(ft.dropdown.Option(entry["date"]))

    page.update()

# 選択された日付の天気情報を表示
def on_date_selected(e):
    selected_code = area_dropdown.value
    selected_date = date_dropdown.value
    if not selected_code or not selected_date:
        return

    weather_grid.controls.clear()
    # データベースから天気情報を取得
    weather = db.get_weather_by_date(selected_code, selected_date)
    if weather:
        weather_grid.controls.append(create_weather_card(weather["date"], weather["condition"]))
    page.update()


def create_weather_card(date: str, condition: str) -> ft.Card:
    """天気カードを生成"""
    return ft.Card(
        content=ft.Container(
            padding=10,
            content=ft.Column(
                [
                    ft.Text(f"Date: {date}", size=18),
                    ft.Text(f"Condition: {condition}", size=16),
                ]
            ),
        )
    )

def main(page: ft.Page):
    db = WeatherDatabase()

    # UIコンポーネント
    area_dropdown = ft.Dropdown(label="Select Area", width=200)
    date_dropdown = ft.Dropdown(label="Select Date", width=200)
    weather_grid = ft.GridView(expand=True, max_extent=400)

    # 地域リストの取得
    def load_areas():
        try:
            response = requests.get("https://www.jma.go.jp/bosai/common/const/area.json")
            data = response.json().get("offices", {})
            for code, info in data.items():
                if len(code) == 6:
                    area_dropdown.options.append(ft.dropdown.Option(key=code, text=info["name"]))
                    db.save_area(code, info["name"])
            page.update()
        except Exception as e:
            print(f"Failed to load areas: {e}")

    # 天気データ取得後、日付リスト表示
    def on_area_selected(e):
        selected_code = area_dropdown.value
        if not selected_code:
            return

        weather_data = fetch_weather(selected_code)
        date_dropdown.options.clear()

        for entry in weather_data:
            db.save_weather(selected_code, entry["date"], entry["condition"])
            date_dropdown.options.append(ft.dropdown.Option(entry["date"]))

        page.update()

    # 選択された日付の天気情報を表示
    def on_date_selected(e):
        selected_code = area_dropdown.value
        selected_date = date_dropdown.value
        if not selected_code or not selected_date:
            return

        weather_grid.controls.clear()
        weather = db.get_weather_by_date(selected_code, selected_date)
        if weather:
            weather_grid.controls.append(create_weather_card(weather["date"], weather["condition"]))
        page.update()

    # イベントリスナー設定
    area_dropdown.on_change = on_area_selected
    date_dropdown.on_change = on_date_selected

    # UIをページに追加
    page.add(ft.Column([area_dropdown, date_dropdown, weather_grid]))

    load_areas()

if __name__ == "__main__":
    ft.app(target=main)
