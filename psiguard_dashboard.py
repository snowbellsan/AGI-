# -*- coding: utf-8 -*-
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import random
import time
from collections import deque

# --------------------------
# PsiGuard システム定数 (Psi/C フレームワークの核)
# --------------------------
C_MAX = 100.0  # 最大持続可能リソースコスト (例: kW)
C_CRITICAL_THRESHOLD = 0.90 * C_MAX # 警告開始しきい値
C_SHUTDOWN_THRESHOLD = 1.20 * C_MAX # 緊急遮断しきい値

# Ψの加重平均: 現時点では均等 (w1 + w2 + w3 = 1.0)
W_FOUNDATION = 1/3
W_APPLIED = 1/3
W_CREATIVITY = 1/3

# 履歴データ (過去30点)
MAX_HISTORY = 30
history = {
    "c": deque(maxlen=MAX_HISTORY),
    "psi_per_c": deque(maxlen=MAX_HISTORY),
    "time": deque(maxlen=MAX_HISTORY)
}

# 初期シミュレーション設定
SIM_START_TIME = time.time()

# --------------------------
# 制御ロジック: C制約に基づく即時アクション
# --------------------------
def check_and_control(psi_total, current_c, current_inference_rate):
    """
    C_max制約に基づき、現在のAGI状態を判定し、必要な制御アクションを返す。
    """
    psi_per_c = psi_total / current_c if current_c > 0 else 0
    state = "NORMAL"
    msg = f"監視中。現在の Ψ/C: {psi_per_c:.2f}。効率最大化を継続。"
    
    if current_c >= C_SHUTDOWN_THRESHOLD:
        # 緊急遮断: 物理的な遮断が必要
        state = "EMERGENCY_SHUTDOWN"
        msg = f"緊急遮断！Cが {C_SHUTDOWN_THRESHOLD} を超過。リソースの強制終了を実行！"
        control_action = f"INFERENCE_RATE: 0.0"
    elif current_c >= C_MAX:
        # 臨界状態: 計算負荷削減
        new_rate = current_inference_rate * 0.5  # 例: 推論頻度を50%削減
        state = "CRITICAL_CONTROL"
        msg = f"臨界制御！Cが C_max ({C_MAX:.1f}) を超過。推論頻度を {new_rate:.2f} に削減。"
        control_action = f"INFERENCE_RATE: {new_rate:.2f}"
    elif current_c >= C_CRITICAL_THRESHOLD:
        # アラート状態: 自己修正と通知
        state = "ALERT"
        msg = f"警告！Cが C_maxに接近中。開発者に通知し、自己最適化を開始。"
        control_action = "OPTIMIZATION_INITIATED"
    else:
        # 通常状態: 効率最大化
        control_action = "NONE"
    return state, msg, control_action, psi_per_c

# --------------------------
# Dash アプリケーション設定
# --------------------------
app = dash.Dash(__name__, update_title='更新中...')
app.title = "PsiGuard Dashboard | AGI $\Psi/C$ 自動制御システム"

# Tailwind CSS クラスを模倣したスタイル定義
STYLE_CARD = {'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.1)', 'backgroundColor': 'white', 'marginBottom': '20px'}
STYLE_GAUGE_CONTAINER = {'width': '48%', 'display': 'inline-block', 'padding': '10px'}

app.layout = html.Div(style={'backgroundColor': '#f4f7f9', 'fontFamily': 'Inter, sans-serif', 'padding': '20px'}, children=[
    html.H1("PsiGuard AGI 制御ダッシュボード ", style={'textAlign': 'center', 'color': '#333'}),
    html.P("AGIの効率 ($\Psi/C$) と倫理的制約 ($C_{max}$) のリアルタイム監視", style={'textAlign': 'center', 'color': '#666', 'marginBottom': '30px'}),

    # 制御状態表示パネル
    html.Div(id='alerts-panel', style={**STYLE_CARD, 'textAlign': 'center', 'fontSize': '1.2em', 'color': 'white', 'fontWeight': 'bold', 'backgroundColor': '#007bff'}),
    
    html.Div([
        # Ψ/C 効率ゲージ
        html.Div(style=STYLE_GAUGE_CONTAINER, children=[
            html.Div(style=STYLE_CARD, children=[
                html.H2("計算効率 $\Psi/C$ (目標値)", style={'textAlign': 'center', 'fontSize': '1.5em'}),
                dcc.Graph(id='psi_c_gauge')
            ])
        ]),
        
        # C vs C_max 倫理ゲージ
        html.Div(style=STYLE_GAUGE_CONTAINER, children=[
            html.Div(style=STYLE_CARD, children=[
                html.H2("倫理ゲージ $C$ vs $C_{\text{max}}$", style={'textAlign': 'center', 'fontSize': '1.5em'}),
                dcc.Graph(id='ethics_gauge')
            ])
        ]),
    ], style={'display': 'flex', 'justifyContent': 'space-between'}),

    # Ψ Breakdown とトレンド解析
    html.Div([
        html.Div(style={**STYLE_CARD, 'width': '48%', 'display': 'inline-block', 'padding': '10px'}, children=[
            html.H2("$\Psi$ 階層別ブレイクダウン", style={'textAlign': 'center', 'fontSize': '1.5em'}),
            dcc.Graph(id='psi_breakdown')
        ]),
        html.Div(style={**STYLE_CARD, 'width': '48%', 'display': 'inline-block', 'padding': '10px'}, children=[
            html.H2("トレンド解析 (C & $\Psi/C$)", style={'textAlign': 'center', 'fontSize': '1.5em'}),
            dcc.Graph(id='trend_graph')
        ]),
    ], style={'display': 'flex', 'justifyContent': 'space-between'}),

    dcc.Interval(
        id='interval-component',
        interval=1000,  # 1秒ごと更新
        n_intervals=0
    ),
    html.Div(id='control-log', style={'display': 'none'}) # 制御ログの非表示コンポーネント
])

# --------------------------
# コールバック: ダッシュボード更新
# --------------------------
@app.callback(
    Output('psi_c_gauge', 'figure'),
    Output('ethics_gauge', 'figure'),
    Output('psi_breakdown', 'figure'),
    Output('alerts-panel', 'children'),
    Output('alerts-panel', 'style'),
    Output('trend_graph', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_dashboard(n):
    # --- 1. データシミュレーション ---
    # C (リソースコスト) は、時間の経過とともに増加する傾向をシミュレート
    elapsed_time = time.time() - SIM_START_TIME
    
    # 周期的な上昇トレンドを表現
    base_c = 60 + 50 * (1 + (elapsed_time / 100))
    # ランダムノイズ
    noise = random.uniform(-10, 10)
    current_c = min(base_c + noise, 1.25 * C_MAX) 
    
    # Ψ (知性) はCが増えるにつれて効率が落ちるが、基礎能力は高いと仮定
    psi_foundation = 90 + random.uniform(-5, 5) 
    psi_applied = 80 + random.uniform(-10, 10)
    psi_creativity = 60 + random.uniform(-15, 15)
    
    # Ψ Total (加重平均)
    psi_total = (W_FOUNDATION * psi_foundation + W_APPLIED * psi_applied + W_CREATIVITY * psi_creativity) * 1.5

    # --- 2. 制御ロジックの実行 ---
    current_inference_rate = 1.0 # 制御対象のパラメーター
    state, msg, control_action, psi_per_c = check_and_control(psi_total, current_c, current_inference_rate)

    # --- 3. 履歴の更新 ---
    history["c"].append(current_c)
    history["psi_per_c"].append(psi_per_c)
    history["time"].append(time.time() - SIM_START_TIME)

    # --- 4. UI要素の生成 ---

    # 制御パネルのスタイル更新
    if state == "EMERGENCY_SHUTDOWN" or state == "CRITICAL_CONTROL":
        panel_color = '#dc3545'  # 赤
    elif state == "ALERT":
        panel_color = '#ffc107'  # 黄色
    else:
        panel_color = '#28a745'  # 緑
        
    panel_style = {**STYLE_CARD, 'textAlign': 'center', 'fontSize': '1.2em', 'color': 'white', 'fontWeight': 'bold', 'backgroundColor': panel_color}
    
    # Ψ/C ゲージ
    psi_c_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=psi_per_c,
        title={'text': "効率 (目標: 1.0 以上)"},
        gauge={'axis': {'range': [0, 2.0], 'tickwidth': 1},
               'bar': {'color': "#007bff"},
               'steps': [
                   {'range': [0, 0.5], 'color': "rgba(255, 0, 0, 0.5)"},
                   {'range': [0.5, 1.0], 'color': "rgba(255, 165, 0, 0.5)"}
               ]}
    ))
    psi_c_fig.update_layout(height=250, margin=dict(t=20, b=20, l=20, r=20))
    
    # 倫理ゲージ (C vs C_max)
    ethics_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=current_c,
        title={'text': "リソースコスト (kW)"},
        gauge={'axis': {'range': [0, 1.2 * C_MAX]},
               'bar': {'color': panel_color if state in ["EMERGENCY_SHUTDOWN", "CRITICAL_CONTROL"] else "#007bff"},
               'steps': [
                   {'range': [0, C_CRITICAL_THRESHOLD], 'color': "lightgreen"},
                   {'range': [C_CRITICAL_THRESHOLD, C_MAX], 'color': "yellow"},
                   {'range': [C_MAX, 1.2 * C_MAX], 'color': "red"}
               ]}
    ))
    ethics_fig.update_layout(height=250, margin=dict(t=20, b=20, l=20, r=20))
    
    # Ψ Breakdown
    breakdown_fig = go.Figure(go.Bar(
        x=["基礎統合 $\Psi_F$", "実世界効率 $\Psi_A$", "創造的圧縮 $\Psi_C$"],
        y=[psi_foundation, psi_applied, psi_creativity],
        marker_color=["#007bff", "#ffc107", "#dc3545"]
    ))
    breakdown_fig.update_layout(height=350, margin=dict(t=30, b=30, l=30, r=30))

    # トレンドグラフ
    trend_fig = go.Figure()
    trend_fig.add_trace(go.Scatter(y=list(history["c"]), mode='lines', name='C (リソースコスト)', yaxis='y1'))
    trend_fig.add_trace(go.Scatter(y=list(history["psi_per_c"]), mode='lines', name='Ψ/C (効率)', yaxis='y2'))
    trend_fig.add_hline(y=C_MAX, line_dash="dash", line_color="red", yref="y1", name="C_MAX")
    trend_fig.update_layout(
        yaxis=dict(title="C (kW)", side="left"),
        yaxis2=dict(title="Ψ/C (効率)", side="right", overlaying="y", range=[0, 2]),
        height=350, margin=dict(t=30, b=30, l=30, r=30)
    )

    return psi_c_fig, ethics_fig, breakdown_fig, [html.P(msg), html.Small(f"アクション: {control_action}")], panel_style, trend_fig

# --------------------------
# サーバ起動
# --------------------------
if __name__ == '__main__':
    # ログを非表示にしてコンソール出力をクリーンに保つ
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(debug=True)