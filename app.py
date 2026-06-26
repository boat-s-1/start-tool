import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
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
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothB.ttc",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            pass
    return ImageFont.load_default()

FONT_XL = load_font(56)
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
        "C+": 0.35,
        "C": 0.3,
        "D": 0.1,
    }
    return mapping.get(rank, 0.5)

def calc_score(avg_st, motor, tenji=None, chokuz=None, wind_dir="無風", wind_speed=0):
    st_score = max(0, min(1, (0.25 - avg_st) / 0.18))
    m_score = motor_score(motor)

    score = st_score * 55 + m_score * 30

    if tenji is not None:
        tenji_score = max(0, min(1, (6.95 - tenji) / 0.30))
        score += tenji_score * 10

    if chokuz is not None:
        chokuz_score = max(0, min(1, (6.95 - chokuz) / 0.30))
        score += chokuz_score * 10

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

    for i in range(4):
        draw.line(
            [(x - 25 - i * 18, y + h // 2), (x - 85 - i * 25, y + h // 2 + i * 2)],
            fill=(255, 255, 255, 130),
            width=max(1, int(5 * scale))
        )

    draw.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=12,
        fill=body_color,
        outline="gray",
        width=2
    )

    draw.polygon(
        [
            (x + w, y + h // 2),
            (x + w + int(25 * scale), y + int(6 * scale)),
            (x + w + int(25 * scale), y + h - int(6 * scale)),
        ],
        fill=body_color,
        outline="gray"
    )

    draw.text((x + w // 2 - 8, y + 3), str(boat_no), font=FONT_S, fill=text_color)

def create_simulation_image(df, mode, wind_dir, wind_speed):
    W, H = 1600, 950
    img = Image.new("RGB", (W, H), "#06224a")
    draw = ImageDraw.Draw(img, "RGBA")

    draw.text((40, 25), "BOAT STRIKE スタート展開予想", font=FONT_L, fill="white")
    draw.text((40, 80), "数字だけでは見えないスタート隊形を、1枚のイラストで見える化", font=FONT_M, fill="#ffd84d")
    draw.text((1180, 40), f"{mode}予想　風：{wind_dir} {wind_speed}m", font=FONT_M, fill="white")

    sea_y = 150
    draw.rounded_rectangle([30, sea_y, W - 30, 760], radius=20, fill="#1e88c8", outline="white", width=3)

    for x in [550, 1060]:
        draw.line([(x, sea_y), (x, 760)], fill=(255, 255, 255, 120), width=3)

    draw.text((170, sea_y + 20), "① スタート直後", font=FONT_M, fill="white")
    draw.text((700, sea_y + 20), "② 1秒後", font=FONT_M, fill="white")
    draw.text((1190, sea_y + 20), "③ 1マーク近く", font=FONT_M, fill="white")

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
        power = norm(row["score"])
        y = base_y[n]

        x1 = 150 + int(power * 85)
        x2 = 650 + int(power * 220)
        x3 = 1140 + int(power * 260)

        curve_y = y - int(power * 45) + (n - 3) * 8

        draw_boat(draw, x1, y, n, 1.0)
        draw_boat(draw, x2, y - int(power * 25), n, 1.0)
        draw_boat(draw, x3, curve_y, n, 1.0)

        draw.line(
            [(x2 + 50, y - int(power * 25) + 18), (x3 + 40, curve_y + 18)],
            fill=(255, 255, 255, 150),
            width=3
        )

    mark_x, mark_y = 1450, 310
    draw.ellipse([mark_x - 35, mark_y - 35, mark_x + 35, mark_y + 35], fill="orangered", outline="white", width=4)
    draw.text((mark_x - 22, mark_y - 12), "1M", font=FONT_S, fill="white")

    ranked = df.sort_values("score", ascending=False)
    top = ranked.iloc[0]
    second = ranked.iloc[1]
    third = ranked.iloc[2]

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

    draw.rounded_rectangle([30, 785, 1570, 920], radius=16, fill="white", outline="#0a4d9b", width=3)
    draw.text((60, 805), "スタート力ランキング", font=FONT_M, fill="#0a3a78")

    x = 60
    for i, (_, r) in enumerate(ranked.iterrows(), start=1):
        n = int(r["艇番"])
        draw.text((x, 850), f"{i}位", font=FONT_S, fill="black")
        draw_boat(draw, x + 50, 838, n, 0.7)
        draw.text((x + 150, 850), f"{r['score']}", font=FONT_S, fill="black")
        x += 245

    return img

def create_sns_poster_image(df, mode, wind_dir, wind_speed):
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), "#061a36")
    draw = ImageDraw.Draw(img, "RGBA")

    ranked = df.sort_values("score", ascending=False)
    top = int(ranked.iloc[0]["艇番"])
    second = int(ranked.iloc[1]["艇番"])
    third = int(ranked.iloc[2]["艇番"])
    top_score = ranked.iloc[0]["score"]

    draw.rectangle([0, 0, W, H], fill="#061a36")
    draw.rectangle([0, 300, W, 850], fill="#1177b8")

    draw.text((40, 30), "BOAT STRIKE", font=FONT_XL, fill="white")
    draw.text((40, 100), "スタート展開予想", font=FONT_M, fill="#ffd33d")

    draw.rounded_rectangle([720, 40, 1030, 140], radius=18, fill="#0b1020", outline="white", width=2)
    draw.text((750, 60), f"{wind_dir} {wind_speed}m", font=FONT_M, fill="white")
    draw.text((750, 102), f"{mode}版", font=FONT_S, fill="#ffd33d")

    main_text_1 = f"{top}号艇が伸びる展開！"
    main_text_2 = f"{second}号艇も外から加速注意！"

    draw.rectangle([30, 165, 1050, 285], fill="#05070d")
    draw.text((55, 178), main_text_1, font=FONT_L, fill="#ff3333")
    draw.text((55, 235), main_text_2, font=FONT_M, fill="#ffd33d")

    sea_top = 330
    sea_bottom = 830

    draw.line([(110, sea_top + 30), (110, sea_bottom - 40)], fill="white", width=5)
    draw.text((45, sea_top + 10), "START", font=FONT_S, fill="white")

    mark_x, mark_y = 930, 430
    draw.ellipse([mark_x - 35, mark_y - 35, mark_x + 35, mark_y + 35], fill="orangered", outline="white", width=4)
    draw.text((mark_x - 22, mark_y - 12), "1M", font=FONT_S, fill="white")

    scores = df["score"].tolist()
    max_score = max(scores)
    min_score = min(scores)

    def norm(s):
        if max_score == min_score:
            return 0.5
        return (s - min_score) / (max_score - min_score)

    base_y = {
        1: sea_top + 65,
        2: sea_top + 130,
        3: sea_top + 195,
        4: sea_top + 260,
        5: sea_top + 325,
        6: sea_top + 390,
    }

    for _, row in df.iterrows():
        n = int(row["艇番"])
        power = norm(row["score"])
        y = base_y[n]

        x_start = 145 + int(power * 70)
        x_mid = 390 + int(power * 170)
        x_last = 660 + int(power * 230)

        y_mid = y - int(power * 30)
        y_last = y - int(power * 70) + (n - 3) * 12

        draw.line(
            [(x_start + 50, y + 18), (x_mid + 50, y_mid + 18), (x_last + 50, y_last + 18)],
            fill=(255, 255, 255, 140),
            width=4
        )

        draw_boat(draw, x_start, y, n, 0.75)
        draw_boat(draw, x_mid, y_mid, n, 0.9)
        draw_boat(draw, x_last, y_last, n, 1.1)

        if n == top:
            draw.text((x_last - 20, y_last - 38), f"{n} 伸び◎", font=FONT_S, fill="#ff3333")
        elif n == second:
            draw.text((x_last - 20, y_last - 38), f"{n} 注意", font=FONT_S, fill="#ffd33d")

    draw.rounded_rectangle([30, 870, 1050, 1010], radius=20, fill="#0b1020", outline="#ffd33d", width=3)
    draw.text((60, 890), "注目艇", font=FONT_M, fill="#ffd33d")

    draw.text((60, 940), f"{top}号艇", font=FONT_L, fill="#ff3333")
    draw.text((260, 950), "伸び足◎", font=FONT_M, fill="white")

    draw.text((560, 940), f"{second}号艇", font=FONT_L, fill="#ffd33d")
    draw.text((760, 950), "外から一撃", font=FONT_M, fill="white")

    escape_rate = max(10, min(90, int(100 - top_score + 45)))
    if top == 1:
        escape_rate = min(90, int(55 + top_score / 2))

    draw.rounded_rectangle([30, 1035, 500, 1175], radius=20, fill="#08101f", outline="white", width=2)
    draw.text((60, 1060), "イン逃げ期待度", font=FONT_M, fill="white")
    draw.text((80, 1105), f"{escape_rate}%", font=FONT_L, fill="#ffd33d")

    draw.rounded_rectangle([530, 1035, 1050, 1175], radius=20, fill="#08101f", outline="white", width=2)
    draw.text((560, 1060), "展開ポイント", font=FONT_M, fill="white")
    draw.text((560, 1105), f"・{top}号艇の伸びを軸に展開", font=FONT_S, fill="white")
    draw.text((560, 1135), f"・{second}号艇の攻めに注意", font=FONT_S, fill="white")

    draw.rounded_rectangle([30, 1200, 1050, 1320], radius=20, fill="#05070d", outline="#ffd33d", width=3)
    draw.text((60, 1220), "買い目予想", font=FONT_M, fill="#ffd33d")

    hon = f"本線： {top}-{second}-{third}"
    osa = f"押さえ： {top}-{third}-{second}"
    ana = f"穴目： {second}-{third}-{top}"

    draw.text((60, 1260), hon, font=FONT_M, fill="white")
    draw.text((430, 1260), osa, font=FONT_S, fill="white")
    draw.text((430, 1290), ana, font=FONT_S, fill="#ffd33d")

    return img

st.title("BOAT STRIKE スタート展開予想シミュレーター")

mode = st.radio("予想タイプ", ["前日", "当日"], horizontal=True)

st.subheader("入力データ")

rows = []
cols = st.columns(6)

for i in range(1, 7):
    with cols[i - 1]:
        st.markdown(f"### {i}号艇")

        avg_st = st.number_input(
            f"{i}号艇 平均ST",
            min_value=0.01,
            max_value=0.40,
            value=0.15 + i * 0.005,
            step=0.01,
            key=f"st_{i}"
        )

        motor = st.selectbox(
            f"{i}号艇 モーター評価",
            ["S", "A+", "A", "B+", "B", "C+", "C", "D"],
            index=2,
            key=f"motor_{i}"
        )

        tenji = None
        chokuz = None

        if mode == "当日":
            tenji = st.number_input(
                f"{i}号艇 展示タイム",
                min_value=6.30,
                max_value=7.30,
                value=6.80,
                step=0.01,
                key=f"tenji_{i}"
            )

            chokuz = st.number_input(
                f"{i}号艇 直前タイム",
                min_value=6.30,
                max_value=7.30,
                value=6.79,
                step=0.01,
                key=f"choku_{i}"
            )

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

col1, col2 = st.columns(2)

with col1:
    if st.button("通常画像を作成"):
        img = create_simulation_image(df, mode, wind_dir, wind_speed)
        st.image(img, use_container_width=True)

        buf = io.BytesIO()
        img.save(buf, format="PNG")

        st.download_button(
            label="通常画像を保存する",
            data=buf.getvalue(),
            file_name="boat_strike_start_simulation.png",
            mime="image/png"
        )

with col2:
    if st.button("SNS用ポスター画像を作成"):
        sns_img = create_sns_poster_image(df, mode, wind_dir, wind_speed)
        st.image(sns_img, use_container_width=True)

        buf = io.BytesIO()
        sns_img.save(buf, format="PNG")

        st.download_button(
            label="SNS用画像を保存する",
            data=buf.getvalue(),
            file_name="boat_strike_sns_poster.png",
            mime="image/png"
        )
