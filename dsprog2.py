import flet as ft
import requests

#APIエンドポイント
AREA_LIST_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{}.json"

#地方の構造を定義
REGION_STRUCTURE = {
    "北海道地方": {
        "宗谷地方": ["北海道宗谷地方"],
        "上川・留萌地方": ["北海道上川留萌地方"],
        "網走・北見・紋別地方": ["北海道網走北見紋別地方"],
        "十勝地方": ["北海道十勝地方"],
        "釧路・根室地方": ["北海道釧路根室地方"],
        "胆振・日高地方": ["北海道胆振日高地方"],
        "石狩・空知・後志地方": ["北海道石狩空知後志地方"],
        "渡島・檜山地方": ["北海道渡島檜山地方"],
    },
    "東北地方": ["青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県"],
    "関東地方": ["茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県"],
    "中部地方": ["新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県"],
    "近畿地方": ["三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県"],
    "中国地方": ["鳥取県", "島根県", "岡山県", "広島県", "山口県"],
    "四国地方": ["徳島県", "香川県", "愛媛県", "高知県"],
    "九州地方": [
        "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", 
        "奄美地方"
    ],
    "沖縄地方": [
        "沖縄県", "大東島地方", "宮古島地方", "八重山地方"
    ]
}

#地域リストを取得する関数
#地域名をキー、地域コードを値とする辞書を作成
def get_area_list():
    data_json = requests.get(AREA_LIST_URL).json()
    offices = data_json.get("offices", {})
    return {info["name"]: code for code, info in offices.items()}

#天気予報を取得して整形する関数
#地域コードをURLに埋め込む
#情報を抽出
#日付をキー、天気情報を値とする辞書作成
def get_forecast(area_code):
    url = FORECAST_URL.format(area_code)
    data_json = requests.get(url).json()
    daily_forecasts = {}
    try:
        for time_series in data_json[0]["timeSeries"]:
            times = time_series["timeDefines"]
            for area in time_series["areas"]:
                area_name = area.get("area", {}).get("name", "不明な地域")
                weathers = area.get("weathers", ["天気情報なし"] * len(times))
                temps = area.get("temps", ["情報なし"] * len(times))
                winds = area.get("winds", ["風情報なし"] * len(times))
                waves = area.get("waves", ["波情報なし"] * len(times))
                rain_probs = area.get("pops", ["降水確率なし"] * len(times))

                for i, time in enumerate(times):
                    date = time[:10]
                    daily_forecasts[date] = {
                        "area": area_name,
                        "weather": weathers[i] if i < len(weathers) else "天気情報なし",
                        "temp": temps[i] if i < len(temps) else "情報なし",
                        "wind": winds[i] if i < len(winds) else "風情報なし",
                        "wave": waves[i] if i < len(waves) else "波情報なし",
                        "rain_prob": rain_probs[i] if i < len(rain_probs) else "降水確率なし",
                    }
    except Exception as e:
        daily_forecasts = {"error": f"エラーが発生しました: {e}"}
    return daily_forecasts

#タイトルなどの設定
def main(page: ft.Page):
    page.title = "天気予報アプリ"
    page.padding = 20

    #地域リストを取得
    area_mapping = get_area_list()

    #ウィジェット定義
    region_dropdown = ft.Dropdown(
        label="地方を選択してください",
        options=[ft.dropdown.Option(region) for region in REGION_STRUCTURE.keys()],
        width=300,
    )

    prefecture_dropdown = ft.Dropdown(
        label="地域を選択してください",
        width=300,
    )

    forecast_button = ft.ElevatedButton("天気予報を取得", width=200)
    calendar_column = ft.Column(spacing=10)
    forecast_result = ft.Text("日付をクリックして詳細を表示してください", selectable=True, width=400)

    #地方選択の変更処理
    def on_region_change(e):
        selected_region = region_dropdown.value
        if not selected_region:
            return

        #地方に基づいて都道府県または地域を更新
        regions = REGION_STRUCTURE.get(selected_region, [])
        prefecture_dropdown.options = [
            ft.dropdown.Option(area) for area in regions
        ]
        prefecture_dropdown.value = None
        page.update()

    #天気予報取得処理
    def on_forecast_click(e):
        selected_region = region_dropdown.value
        selected_area = prefecture_dropdown.value

        if not selected_region or not selected_area:
            forecast_result.value = "エラー: 地方と地域を選択してください。"
            page.update()
            return

        try:
            area_code = area_mapping[selected_area]
            forecast_data = get_forecast(area_code)
            calendar_column.controls.clear()
            for date, details in forecast_data.items():
                calendar_column.controls.append(
                    ft.ElevatedButton(
                        text=date,
                        on_click=lambda e, d=details: on_date_click(d),
                        width=150,
                    )
                )
            forecast_result.value = "日付をクリックして詳細を表示してください。"
        except Exception as ex:
            forecast_result.value = f"エラーが発生しました: {ex}"
        finally:
            page.update()

    #日付をクリックして詳細を表示
    def on_date_click(details):
        forecast_result.value = (
            f"地域: {details['area']}\n"
            f"天気: {details['weather']}\n"
            f"気温: {details['temp']}℃\n"
            f"風: {details['wind']}\n"
            f"波: {details['wave']}\n"
            f"降水確率: {details['rain_prob']}%\n"
        )
        page.update()

    region_dropdown.on_change = on_region_change
    forecast_button.on_click = on_forecast_click

    #ページレイアウト
    page.add(
        ft.Column(
            [
                ft.Text("天気予報アプリ", size=24, weight="bold"),
                region_dropdown,
                prefecture_dropdown,
                forecast_button,
                calendar_column,
                forecast_result,
            ],
            spacing=20,
        )
    )

#アプリ起動
if __name__ == "__main__":
    ft.app(target=main)
