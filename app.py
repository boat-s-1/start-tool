import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import math
import io

st.set_page_config(page_title="BOAT STRIKE スタート展開予想", layout="wide")

BOAT_COLORS = {
    1: ("white", "black"),
    2: ("black", "white"),
    3: ("red", "white"),
    4: ("royalblue", "white"),
    5: ("gold", "black"),
    6: ("green", "white"),
}

def load_font(size=28):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothB.ttc",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            pass
    return ImageFont.load_default()

FONT_L = load_font(42)
FONT_M = load_font(26)
FONT_S = load_font(18)

def motor_score(rank):
    mapping = {
        "S": 1.0,
        "A+": 0.9,
        "A": 0.8,
        "B+": 0.65,
        "B": 0.5,
        "C": 0.3,
        "C+": 0.35,
        "D": 0.1,
    }
    return mapping.get(rank, 0.5)

def calc_score(avg_st, motor, tenji=None, chokuz=None, wind_dir="無風", wind_speed=0):
    # STは早いほど高評価
    st_score = max(0, min(1, (0.25 - avg_st) / 0.18))

    m_score = motor_score(motor)

    score = st_score * 55 + m_score * 30

    if tenji is not None:
        # 展示タイムは低いほど良い。6.70前後を高評価にする簡易式
        tenji_score = max(0, min(1, (6.95 - tenji) / 0.30))
        score += tenji_score * 10

    if chokuz is not None:
        chokuz_score = max(0, min(1, (6.95 - chokuz) / 0.30))
        score += chokuz_score * 10

    # 風補正
    if wind_dir == "追い風":
        score += wind_speed * 1.2
    elif wind_dir == "向かい風":
        score -= wind_speed * 0.8
    elif wind_dir == "横風":
        score -= wind_speed * 0.4

    return round(score, 1)

def draw_boat(draw, x, y, boat_no, scale=1.0):
    body_color, text_color = BOAT_COLORS[boat_no]
    w = int(90 * scale)
    h = int(34 * scale)

    # 航跡
    for i in range(4):
        draw.line(
            [(x - 25 - i * 18, y + h // 2), (x - 85 - i * 25, y + h // 2 + i * 2)],
            fill=(255, 255, 255, 170),
            width=max(1, int(5 * scale))
        )

    # 舟本体
    draw.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=body_color, outline="gray", width=2)
    draw.polygon([(x + w, y + h // 2), (x + w + 25, y + 6), (x + w + 25, y + h - 6)], fill=body_color, outline="gray")

    # 番号
    draw.text((x + w//2 - 8, y + 3), str(boat_no), font=FONT_S, fill=text_color)

def create_simulation_image(df, mode, wind_dir, wind_speed):
    W, H = 1600, 950
    img = Image.new("RGB", (W, H), "#06224a")
    draw = ImageDraw.Draw(img, "RGBA")

    # ヘッダー
    draw.text((40, 25), "BOAT STRIKE スタート展開予想", font=FONT_L, fill="white")
    draw.text((40, 80), "数字だけでは見えないスタート隊形を、1枚のイラストで見える化", font=FONT_M, fill="#ffd84d")
    draw.text((1180, 40), f"{mode}予想　風：{wind_dir} {wind_speed}m", font=FONT_M, fill="white")

    # 水面
    sea_y = 150
    draw.rounded_rectangle([30, sea_y, W-30, 760], radius=20, fill="#1e88c8", outline="white", width=3)

    # 区切り
    for x in [550, 1060]:
        draw.line([(x, sea_y), (x, 760)], fill=(255,255,255,120), width=3)

    draw.text((170, sea_y + 20), "① スタート直後", font=FONT_M, fill="white")
    draw.text((700, sea_y + 20), "② 1秒後", font=FONT_M, fill="white")
    draw.text((1190, sea_y + 20), "③ 1マーク近く", font=FONT_M, fill="white")

    # スタートライン
    draw.line([(100, 230), (100, 690)], fill="white", width=5)
    draw.text((50, 200), "START", font=FONT_S, fill="white")

    scores = df["score"].tolist()
    max_score = max(scores)
    min_score = min(scores)

    def norm(s):
        if max_score == min_score:
            return 0.5
        return (s - min_score) / (max_score - min_score)

    base_y = {1: 240, 2: 310, 3: 380, 4: 450, 5: 520, 6: 590}

    for _, row in df.iterrows():
        n = int(row["艇番"])
        s = row["score"]
        power = norm(s)

        y = base_y[n]

        # ①スタート直後
        x1 = 150 + int(power * 85)

        # ②1秒後
        x2 = 650 + int(power * 220)

        # ③1マーク近く
        x3 = 1140 + int(power * 260)

        # 外艇は少し外側、内艇は内側に寄せる
        curve_y = y - int(power * 45) + (n - 3) * 8

        draw_boat(draw, x1, y, n, 1.0)
        draw_boat(draw, x2, y - int(power * 25), n, 1.0)
        draw_boat(draw, x3, curve_y, n, 1.0)

        # 軌跡
        draw.line(
            [(x2 + 50, y - int(power * 25) + 18), (x3 + 40, curve_y + 18)],
            fill=(255,255,255,150),
            width=3
        )

    # 1マーク
    mark_x, mark_y = 1450, 310
    draw.ellipse([mark_x-35, mark_y-35, mark_x+35, mark_y+35], fill="orangered", outline="white", width=4)
    draw.text((mark_x-22, mark_y-12), "1M", font=FONT_S, fill="white")

    # コメントボックス
    top = df.sort_values("score", ascending=False).iloc[0]
    second = df.sort_values("score", ascending=False).iloc[1]
    third = df.sort_values("score", ascending=False).iloc[2]

    comment = [
        f"本命：{int(top['艇番'])}号艇",
        f"{int(top['艇番'])}号艇がスタート力上位。",
        f"{int(second['艇番'])}号艇・{int(third['艇番'])}号艇も展開注意。",
        "1マークまでの隊形イメージです。"
    ]

    draw.rounded_rectangle([1040, 560, 1510, 730], radius=16, fill="white", outline="#003b80", width=3)
    y = 580
    for line in comment:
        draw.text((1070, y), line, font=FONT_M, fill="#111")
        y += 36

    # 下部ランキング
    draw.rounded_rectangle([30, 785, 1570, 920], radius=16, fill="white", outline="#0a4d9b", width=3)
    draw.text((60, 805), "スタート力ランキング", font=FONT_M, fill="#0a3a78")

    ranked = df.sort_values("score", ascending=False)
    x = 60
    for i, (_, r) in enumerate(ranked.iterrows(), start=1):
        n = int(r["艇番"])
        draw.text((x, 850), f"{i}位", font=FONT_S, fill="black")
        draw_boat(draw, x + 50, 838, n, 0.7)
        draw.text((x + 150, 850), f"{r['score']}", font=FONT_S, fill="black")
        x += 245

    return img

st.title("BOAT STRIKE スタート展開予想シミュレーター")

mode = st.radio("予想タイプ", ["前日", "当日"], horizontal=True)

st.subheader("入力データ")

rows = []
cols = st.columns(6)

for i in range(1, 7):
    with cols[i-1]:
        st.markdown(f"### {i}号艇")
        avg_st = st.number_input(f"{i}号艇 平均ST", min_value=0.01, max_value=0.40, value=0.15 + i*0.005, step=0.01, key=f"st_{i}")
        motor = st.selectbox(f"{i}号艇 モーター評価", ["S", "A+", "A", "B+", "B", "C+", "C", "D"], index=2, key=f"motor_{i}")

        tenji = None
        chokuz = None

        if mode == "当日":
            tenji = st.number_input(f"{i}号艇 展示タイム", min_value=6.30, max_value=7.30, value=6.80, step=0.01, key=f"tenji_{i}")
            chokuz = st.number_input(f"{i}号艇 直前タイム", min_value=6.30, max_value=7.30, value=6.79, step=0.01, key=f"choku_{i}")

        rows.append({
            "艇番": i,
            "平均ST": avg_st,
            "モーター": motor,
            "展示タイム": tenji,
            "直前タイム": chokuz,
        })

wind_dir = "無風"
wind_speed = 0

if mode == "当日":
    st.subheader("風情報")
    wind_dir = st.selectbox("風向き", ["無風", "追い風", "向かい風", "横風"])
    wind_speed = st.slider("風速", 0, 10, 2)

df = pd.DataFrame(rows)

df["score"] = df.apply(
    lambda r: calc_score(
        r["平均ST"],
        r["モーター"],
        r["展示タイム"],
        r["直前タイム"],
        wind_dir,
        wind_speed
    ),
    axis=1
)

st.subheader("計算結果")
st.dataframe(df, use_container_width=True)

if st.button("スタート展開イラストを作成"):
    img = create_simulation_image(df, mode, wind_dir, wind_speed)
    st.image(img, use_container_width=True)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    st.download_button(
        label="画像を保存する",
        data=buf.getvalue(),
        file_name="boat_strike_start_simulation.png",
        mime="image/png"
    )
