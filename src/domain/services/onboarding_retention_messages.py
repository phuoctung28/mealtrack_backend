# D1-D3 onboarding retention campaign message catalog.
# Keyed by language → gender → notification_type.
#
# All 7 campaign notification types:
#   d1_night_anchor, d2_morning_steps_sync, d2_lunch_refuel,
#   d2_hydration_slump, d2_daily_summary, d3_churn_preemption,
#   d3_premium_asset_lock
#
# d2_daily_summary branches (zero_logs, on_target, under_goal, slightly_over, way_over)
# use body_template placeholders: {percentage}, {deficit}, {excess}.
# All other types have a plain body field.
#
# Tone rules:
# - D3 lock copy uses "locked" / "unavailable" — never "deleted"
# - EN: male="bro", female="mate"
# - VI: male="bro", female="bạn ơi"

_CATALOG: dict = {
    "en": {
        "male": {
            "d1_night_anchor": {
                "title": "Nutree",
                "body": "What's your commute tomorrow, bro?\nTap to set your steps goal and keep your streak building 🚶",
            },
            "d2_morning_steps_sync": {
                "title": "Nutree",
                "body": "Morning, bro! Sync your steps from yesterday\nYour streak is building — don't let it slip 🔥",
            },
            "d2_lunch_refuel": {
                "title": "Nutree",
                "body": "Quick lunch log, bro → stay on target\n1-tap and you're back on track 🥗",
            },
            "d2_hydration_slump": {
                "title": "Nutree",
                "body": "Halfway through Day 2, bro — how's your water intake?\nDrink a glass now to beat the afternoon slump 💧",
            },
            "d2_daily_summary": {
                "zero_logs": {
                    "body_template": "Day 2 check-in, bro! No logs yet today — no stress\nQuick 1-tap entry keeps your health streak alive 📝",
                },
                "on_target": {
                    "body_template": "Day 2 check-in, bro! You're at {percentage}% — keep it up!\nYou're on a roll with your new routine 🎉",
                },
                "under_goal": {
                    "body_template": "Day 2 check-in, bro! You're {deficit} kcal under — time to refuel\nA clean snack closes the gap perfectly 💪",
                },
                "slightly_over": {
                    "body_template": "Day 2 check-in, bro! Only {excess} kcal over — totally fine\nYour body adapts. Keep the momentum going 😎",
                },
                "way_over": {
                    "body_template": "Day 2 check-in, bro! Enjoyed a cheat by {excess} kcal\nNo setbacks — tomorrow we reset together 🤙",
                },
            },
            "d3_churn_preemption": {
                "title": "Nutree",
                "body": "Your 3-day progress is at risk of being lost, bro\nLog in now to protect everything you've built 💪",
            },
            "d3_premium_asset_lock": {
                "title": "Nutree",
                "body": "Your trial features become unavailable soon, bro\nUpgrade now to keep your personalised health toolkit 🔒",
            },
        },
        "female": {
            "d1_night_anchor": {
                "title": "Nutree",
                "body": "What's your commute tomorrow, mate?\nTap to set your steps goal and keep your streak building 🚶",
            },
            "d2_morning_steps_sync": {
                "title": "Nutree",
                "body": "Morning, mate! Sync your steps from yesterday\nYour streak is building — don't let it slip 🔥",
            },
            "d2_lunch_refuel": {
                "title": "Nutree",
                "body": "Quick lunch log, mate → stay on target\n1-tap and you're back on track 🥗",
            },
            "d2_hydration_slump": {
                "title": "Nutree",
                "body": "Halfway through Day 2, mate — how's your water intake?\nDrink a glass now to beat the afternoon slump 💧",
            },
            "d2_daily_summary": {
                "zero_logs": {
                    "body_template": "Day 2 check-in, mate! No logs yet today — no stress\nQuick 1-tap entry keeps your health streak alive 📝",
                },
                "on_target": {
                    "body_template": "Day 2 check-in, mate! You're at {percentage}% — keep it up!\nYou're on a roll with your new routine 🎉",
                },
                "under_goal": {
                    "body_template": "Day 2 check-in, mate! You're {deficit} kcal under — time to refuel\nA clean snack closes the gap perfectly 💪",
                },
                "slightly_over": {
                    "body_template": "Day 2 check-in, mate! Only {excess} kcal over — totally fine\nYour body adapts. Keep the momentum going 😎",
                },
                "way_over": {
                    "body_template": "Day 2 check-in, mate! Enjoyed a cheat by {excess} kcal\nNo setbacks — tomorrow we reset together 🤙",
                },
            },
            "d3_churn_preemption": {
                "title": "Nutree",
                "body": "Your 3-day progress is at risk of being lost, mate\nLog in now to protect everything you've built 💪",
            },
            "d3_premium_asset_lock": {
                "title": "Nutree",
                "body": "Your trial features become unavailable soon, mate\nUpgrade now to keep your personalised health toolkit 🔒",
            },
        },
    },
    "vi": {
        "male": {
            "d1_night_anchor": {
                "title": "Nutree",
                "body": "Ngày mai bro di chuyển thế nào?\nTap để đặt mục tiêu bước chân và giữ chuỗi ngày liên tiếp 🚶",
            },
            "d2_morning_steps_sync": {
                "title": "Nutree",
                "body": "Sáng rồi bro! Sync bước chân từ hôm qua đi nào\nChuỗi streak đang tăng — đừng để đứt mạch 🔥",
            },
            "d2_lunch_refuel": {
                "title": "Nutree",
                "body": "Ghi nhanh bữa trưa đi bro → giữ đúng mục tiêu\n1-chạm là xong, không mất nhiều thời gian đâu 🥗",
            },
            "d2_hydration_slump": {
                "title": "Nutree",
                "body": "Đã qua nửa Ngày 2 rồi bro — uống nước chưa?\nUống một ly ngay để đập tan cơn uể oải buổi chiều 💧",
            },
            "d2_daily_summary": {
                "zero_logs": {
                    "body_template": "Check-in Ngày 2 đây bro! Chưa có log nào hôm nay — không sao\n1-chạm ghi nhanh để bảo toàn chuỗi ngày sống khỏe 📝",
                },
                "on_target": {
                    "body_template": "Check-in Ngày 2 đây bro! Đạt {percentage}% rồi — tiếp tục thôi!\nBro đang tạo được thói quen tuyệt vời rồi đó 🎉",
                },
                "under_goal": {
                    "body_template": "Check-in Ngày 2 đây bro! Còn thiếu {deficit} kcal — nạp thêm chút nào\nMột món ăn nhẹ là lấp đầy khoảng trống hoàn hảo 💪",
                },
                "slightly_over": {
                    "body_template": "Check-in Ngày 2 đây bro! Vượt nhẹ {excess} kcal — hoàn toàn ổn\nCơ thể thích ứng tốt. Cứ giữ vững nhịp điệu nhé 😎",
                },
                "way_over": {
                    "body_template": "Check-in Ngày 2 đây bro! Nuông chiều bản thân {excess} kcal hôm nay\nKhông lùi bước — ngày mai chúng ta cùng reset lại 🤙",
                },
            },
            "d3_churn_preemption": {
                "title": "Nutree",
                "body": "Tiến trình 3 ngày của bro đang có nguy cơ mất đi\nMở app ngay để bảo vệ thành quả đã xây dựng 💪",
            },
            "d3_premium_asset_lock": {
                "title": "Nutree",
                "body": "Tính năng dùng thử sắp bị khóa rồi bro\nNâng cấp ngay để giữ lại bộ công cụ sức khỏe cá nhân 🔒",
            },
        },
        "female": {
            "d1_night_anchor": {
                "title": "Nutree",
                "body": "Ngày mai bạn ơi di chuyển thế nào?\nTap để đặt mục tiêu bước chân và giữ chuỗi ngày liên tiếp 🚶",
            },
            "d2_morning_steps_sync": {
                "title": "Nutree",
                "body": "Sáng rồi bạn ơi! Sync bước chân từ hôm qua đi nào\nChuỗi streak đang tăng — đừng để đứt mạch 🔥",
            },
            "d2_lunch_refuel": {
                "title": "Nutree",
                "body": "Ghi nhanh bữa trưa đi bạn ơi → giữ đúng mục tiêu\n1-chạm là xong, không mất nhiều thời gian đâu 🥗",
            },
            "d2_hydration_slump": {
                "title": "Nutree",
                "body": "Đã qua nửa Ngày 2 rồi bạn ơi — uống nước chưa?\nUống một ly ngay để đập tan cơn uể oải buổi chiều 💧",
            },
            "d2_daily_summary": {
                "zero_logs": {
                    "body_template": "Check-in Ngày 2 đây bạn ơi! Chưa có log nào hôm nay — không sao\n1-chạm ghi nhanh để bảo toàn chuỗi ngày sống khỏe 📝",
                },
                "on_target": {
                    "body_template": "Check-in Ngày 2 đây bạn ơi! Đạt {percentage}% rồi — tiếp tục thôi!\nBạn đang tạo được thói quen tuyệt vời rồi đó 🎉",
                },
                "under_goal": {
                    "body_template": "Check-in Ngày 2 đây bạn ơi! Còn thiếu {deficit} kcal — nạp thêm chút nào\nMột món ăn nhẹ là lấp đầy khoảng trống hoàn hảo 💪",
                },
                "slightly_over": {
                    "body_template": "Check-in Ngày 2 đây bạn ơi! Vượt nhẹ {excess} kcal — hoàn toàn ổn\nCơ thể thích ứng tốt. Cứ giữ vững nhịp điệu nhé 😎",
                },
                "way_over": {
                    "body_template": "Check-in Ngày 2 đây bạn ơi! Nuông chiều bản thân {excess} kcal hôm nay\nKhông lùi bước — ngày mai chúng ta cùng reset lại 🤙",
                },
            },
            "d3_churn_preemption": {
                "title": "Nutree",
                "body": "Tiến trình 3 ngày của bạn ơi đang có nguy cơ mất đi\nMở app ngay để bảo vệ thành quả đã xây dựng 💪",
            },
            "d3_premium_asset_lock": {
                "title": "Nutree",
                "body": "Tính năng dùng thử sắp bị khóa rồi bạn ơi\nNâng cấp ngay để giữ lại bộ công cụ sức khỏe cá nhân 🔒",
            },
        },
    },
}


def _resolve_d2_summary(entry: dict, context: dict) -> dict:
    """Render d2_daily_summary slot from context into a plain title/body dict."""
    slot = context.get("summary_slot", "on_target")
    if slot not in entry:
        slot = "on_target"
    branch = entry[slot]
    template: str = branch["body_template"]
    percentage = context.get("percentage", 100)
    deficit = context.get("deficit", 0)
    excess = context.get("excess", 0)
    body = template.format(percentage=percentage, deficit=deficit, excess=excess)
    return {"title": "Nutree", "body": body}


def get_retention_messages(
    language: str,
    gender: str,
    context: dict | None = None,
) -> dict:
    """Return resolved message catalog for the given language + gender.

    Falls back to en/male if the language or gender is not in the catalog.
    For d2_daily_summary, the returned entry has a plain ``body`` field
    (not a body_template) rendered from ``context`` (default: on_target/100%).
    """
    ctx = context or {}
    locale = _CATALOG.get(language, _CATALOG["en"])
    msgs_raw = locale.get(gender, locale["male"])

    # Build a resolved copy — d2_daily_summary needs template rendering.
    resolved: dict = {}
    for ntype, entry in msgs_raw.items():
        if ntype == "d2_daily_summary":
            resolved[ntype] = _resolve_d2_summary(entry, ctx)
        else:
            resolved[ntype] = entry
    return resolved
