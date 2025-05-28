# config.py

# 赔率配置
PAYOUT_RATES = {
    1: 5,
    2: 5,
    3: 5,
    4: 5,
    5: 10,
    6: 15,
    7: 25,
    8: 45,
}

# 中奖结构
WINNING_STRUCTURES = [
    {"areas": [1], "weight": 1930},
    {"areas": [2], "weight": 1930},
    {"areas": [3], "weight": 1930},
    {"areas": [4], "weight": 1930},
    {"areas": [5], "weight": 965},
    {"areas": [6], "weight": 640},
    {"areas": [7], "weight": 390},
    {"areas": [8], "weight": 215},
    {"areas": [1, 2, 3, 4], "weight": 60},
    {"areas": [5, 6, 7, 8], "weight": 10},
]

# 游戏阶段时长（秒）
BETTING_DURATION = 3   # 下注阶段时长
WAITING_DURATION = 1    # 等待开奖阶段时长
ANIMATION_DURATION = 1  # 开奖动画时长
ROUND_TOTAL_DURATION = BETTING_DURATION + WAITING_DURATION + ANIMATION_DURATION # 一局总时长

# 策略相关控制参数
# 标准差
STD_THRESHOLD = 0.15   # 基础标准差
CONFIDENCE_LEVEL = 0.95 # 置信水平
MINIMUM_BET_THRESHOLD = 500    # 最小下注额
TARGET_RTP = 0.995  # 目标 RTP

# 盈利态势
MEMORY_WINDOW = 30  # N 局窗口长度
MEMORY_DECAY_ALPHA = 0.1   # 衰减函数参数，控制遗忘速度