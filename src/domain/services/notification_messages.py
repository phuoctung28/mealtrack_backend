"""
Notification message templates keyed by language and gender.

Gender-aware buddy terms:
- EN: male="bro", female="mate"
- VI: male="bro", female="bạn ơi"

Meal reminders (lunch/dinner) use {remaining} placeholder for remaining calories.
Daily summary uses {percentage}, {deficit}, {excess} placeholders.
"""

NOTIFICATION_MESSAGES = {
    "en": {
        "male": {
            "meal_reminder": {
                "breakfast": {
                    "title": "☕ Morning, bro!",
                    "body": "Grab a bite or coffee — log it!",
                },
                "lunch": {
                    "title": "🥗 Lunch o'clock, bro!",
                    "body_template": "{remaining} cal left — what's on the plate?",
                },
                "dinner": {
                    "title": "🍽️ Dinner time, bro!",
                    "body_template": "{remaining} cal left — make it count!",
                },
            },
            "daily_summary": {
                "zero_logs": {
                    "title": "📝 Busy day, bro?",
                    "body": "Drop a quick meal log when you can!",
                },
                "on_target": {
                    "title": "🎉 Crushed it, bro!",
                    "body_template": "{percentage}% of your goal!",
                },
                "under_goal": {
                    "title": "💪 Almost there, bro!",
                    "body_template": "{deficit} cal left — grab a snack!",
                },
                "slightly_over": {
                    "title": "😎 No stress, bro!",
                    "body_template": "{excess} cal over — keep going!",
                },
                "way_over": {
                    "title": "🤙 All good, bro!",
                    "body_template": "{excess} cal over — tomorrow's a fresh start!",
                },
            },
        },
        "female": {
            "meal_reminder": {
                "breakfast": {
                    "title": "☕ Morning, mate!",
                    "body": "Grab a bite or coffee — log it!",
                },
                "lunch": {
                    "title": "🥗 Lunch o'clock, mate!",
                    "body_template": "{remaining} cal left — what's on the plate?",
                },
                "dinner": {
                    "title": "🍽️ Dinner time, mate!",
                    "body_template": "{remaining} cal left — make it count!",
                },
            },
            "daily_summary": {
                "zero_logs": {
                    "title": "📝 Busy day, mate?",
                    "body": "Drop a quick meal log when you can!",
                },
                "on_target": {
                    "title": "🎉 Crushed it, mate!",
                    "body_template": "{percentage}% of your goal!",
                },
                "under_goal": {
                    "title": "💪 Almost there, mate!",
                    "body_template": "{deficit} cal left — grab a snack!",
                },
                "slightly_over": {
                    "title": "😎 No stress, mate!",
                    "body_template": "{excess} cal over — keep going!",
                },
                "way_over": {
                    "title": "🤙 All good, mate!",
                    "body_template": "{excess} cal over — tomorrow's a fresh start!",
                },
            },
        },
    },
    "vi": {
        "male": {
            "meal_reminder": {
                "breakfast": {
                    "title": "☕ Sáng rồi bro!",
                    "body": "Ăn nhẹ hay cà phê đi — ghi lại nha!",
                },
                "lunch": {
                    "title": "🥗 Trưa rồi bro!",
                    "body_template": "Còn {remaining} cal — ăn gì chưa?",
                },
                "dinner": {
                    "title": "🍽️ Tối rồi bro!",
                    "body_template": "Còn {remaining} cal — ăn gì đi hả?",
                },
            },
            "daily_summary": {
                "zero_logs": {
                    "title": "📝 Bận cả ngày hả bro?",
                    "body": "Tranh thủ ghi lại bữa nào đó nha!",
                },
                "on_target": {
                    "title": "🎉 Đỉnh nóc bro!",
                    "body_template": "{percentage}% mục tiêu!",
                },
                "under_goal": {
                    "title": "💪 Gần tới rồi bro!",
                    "body_template": "Còn {deficit} cal — ăn nhẹ gì đi!",
                },
                "slightly_over": {
                    "title": "😎 Thoải mái bro!",
                    "body_template": "Vượt một ít {excess} cal — tiếp tục nha!",
                },
                "way_over": {
                    "title": "🤙 Không sao bro!",
                    "body_template": "Vượt {excess} cal — mai là ngày mới!",
                },
            },
        },
        "female": {
            "meal_reminder": {
                "breakfast": {
                    "title": "☕ Sáng rồi bạn ơi!",
                    "body": "Ăn nhẹ hay cà phê đi — ghi lại nha!",
                },
                "lunch": {
                    "title": "🥗 Trưa rồi bạn ơi!",
                    "body_template": "Còn {remaining} cal — ăn gì chưa?",
                },
                "dinner": {
                    "title": "🍽️ Tối rồi bạn ơi!",
                    "body_template": "Còn {remaining} cal — ăn gì đi hả?",
                },
            },
            "daily_summary": {
                "zero_logs": {
                    "title": "📝 Bận cả ngày hả bạn ơi?",
                    "body": "Tranh thủ ghi lại bữa nào đó nha!",
                },
                "on_target": {
                    "title": "🎉 Đỉnh nóc bạn ơi!",
                    "body_template": "{percentage}% mục tiêu!",
                },
                "under_goal": {
                    "title": "💪 Gần tới rồi bạn ơi!",
                    "body_template": "Còn {deficit} cal — ăn nhẹ gì đi!",
                },
                "slightly_over": {
                    "title": "😎 Thoải mái bạn ơi!",
                    "body_template": "Vượt một ít {excess} cal — tiếp tục nha!",
                },
                "way_over": {
                    "title": "🤙 Không sao bạn ơi!",
                    "body_template": "Vượt {excess} cal — mai là ngày mới!",
                },
            },
        },
    },
}


def get_messages(language: str, gender: str) -> dict:
    """Get notification messages for language + gender.

    Falls back to: EN male if language/gender combo not found.
    """
    locale = NOTIFICATION_MESSAGES.get(language, NOTIFICATION_MESSAGES["en"])
    return locale.get(gender, locale["male"])
