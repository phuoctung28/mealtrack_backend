"""
Notification message templates keyed by language and gender.

Time Sensitive notifications: title is empty (iOS shows app name).
All content in body field with emoji at end.

Gender-aware buddy terms:
- EN: male="bro", female="mate"
- VI: male="bro", female="bạn ơi"

Placeholders:
- Meal reminders (lunch/dinner): {remaining} for remaining calories
- Daily summary: {percentage}, {deficit}, {excess}
"""

NOTIFICATION_MESSAGES = {
    "en": {
        "male": {
            "meal_reminder": {
                "breakfast": {
                    "body": "Morning, bro! Grab a bite or coffee — log it! ☕",
                },
                "lunch": {
                    "body_template": "Lunch o'clock, bro! {remaining} cal left — what's on the plate? 🥗",
                },
                "dinner": {
                    "body_template": "Dinner time, bro! {remaining} cal left — make it count! 🍽️",
                },
            },
            "daily_summary": {
                "zero_logs": {
                    "body": "Busy day, bro? Drop a quick meal log when you can! 📝",
                },
                "on_target": {
                    "body_template": "Crushed it, bro! {percentage}% of your goal! 🎉",
                },
                "under_goal": {
                    "body_template": "Almost there, bro! {deficit} cal left — grab a snack! 💪",
                },
                "slightly_over": {
                    "body_template": "No stress, bro! {excess} cal over — keep going! 😎",
                },
                "way_over": {
                    "body_template": "All good, bro! {excess} cal over — tomorrow's a fresh start! 🤙",
                },
            },
            "trial_expiry": {
                "2d": {
                    "title": "Nutree",
                    "body": "Heads up, bro — your trial ends in 2 days. Lock in your streak! ⏳",
                },
                "1d": {
                    "title": "Nutree",
                    "body": "Last day, bro — trial ends tomorrow. Keep your progress going! 🔥",
                },
            },
        },
        "female": {
            "meal_reminder": {
                "breakfast": {
                    "body": "Morning, mate! Grab a bite or coffee — log it! ☕",
                },
                "lunch": {
                    "body_template": "Lunch o'clock, mate! {remaining} cal left — what's on the plate? 🥗",
                },
                "dinner": {
                    "body_template": "Dinner time, mate! {remaining} cal left — make it count! 🍽️",
                },
            },
            "daily_summary": {
                "zero_logs": {
                    "body": "Busy day, mate? Drop a quick meal log when you can! 📝",
                },
                "on_target": {
                    "body_template": "Crushed it, mate! {percentage}% of your goal! 🎉",
                },
                "under_goal": {
                    "body_template": "Almost there, mate! {deficit} cal left — grab a snack! 💪",
                },
                "slightly_over": {
                    "body_template": "No stress, mate! {excess} cal over — keep going! 😎",
                },
                "way_over": {
                    "body_template": "All good, mate! {excess} cal over — tomorrow's a fresh start! 🤙",
                },
            },
            "trial_expiry": {
                "2d": {
                    "title": "Nutree",
                    "body": "Heads up, mate — your trial ends in 2 days. Lock in your streak! ⏳",
                },
                "1d": {
                    "title": "Nutree",
                    "body": "Last day, mate — trial ends tomorrow. Keep your progress going! 🔥",
                },
            },
        },
    },
    "vi": {
        "male": {
            "meal_reminder": {
                "breakfast": {
                    "body": "Sáng rồi bro! Ăn nhẹ hay cà phê đi — ghi lại nha! ☕",
                },
                "lunch": {
                    "body_template": "Trưa rồi bro! Còn {remaining} cal — ăn gì chưa? 🥗",
                },
                "dinner": {
                    "body_template": "Tối rồi bro! Còn {remaining} cal — ăn gì đi hả? 🍽️",
                },
            },
            "daily_summary": {
                "zero_logs": {
                    "body": "Bận cả ngày hả bro? Tranh thủ ghi lại bữa nào đó nha! 📝",
                },
                "on_target": {
                    "body_template": "Đỉnh nóc bro! {percentage}% mục tiêu! 🎉",
                },
                "under_goal": {
                    "body_template": "Gần tới rồi bro! Còn {deficit} cal — ăn nhẹ gì đi! 💪",
                },
                "slightly_over": {
                    "body_template": "Thoải mái bro! Vượt một ít {excess} cal — tiếp tục nha! 😎",
                },
                "way_over": {
                    "body_template": "Không sao bro! Vượt {excess} cal — mai là ngày mới! 🤙",
                },
            },
            "trial_expiry": {
                "2d": {
                    "title": "Nutree",
                    "body": "Còn 2 ngày là trial hết hạn nha bro — giữ streak nào! ⏳",
                },
                "1d": {
                    "title": "Nutree",
                    "body": "Ngày cuối rồi bro — trial mai hết hạn. Tiếp tục nha! 🔥",
                },
            },
        },
        "female": {
            "meal_reminder": {
                "breakfast": {
                    "body": "Sáng rồi bạn ơi! Ăn nhẹ hay cà phê đi — ghi lại nha! ☕",
                },
                "lunch": {
                    "body_template": "Trưa rồi bạn ơi! Còn {remaining} cal — ăn gì chưa? 🥗",
                },
                "dinner": {
                    "body_template": "Tối rồi bạn ơi! Còn {remaining} cal — ăn gì đi hả? 🍽️",
                },
            },
            "daily_summary": {
                "zero_logs": {
                    "body": "Bận cả ngày hả bạn ơi? Tranh thủ ghi lại bữa nào đó nha! 📝",
                },
                "on_target": {
                    "body_template": "Đỉnh nóc bạn ơi! {percentage}% mục tiêu! 🎉",
                },
                "under_goal": {
                    "body_template": "Gần tới rồi bạn ơi! Còn {deficit} cal — ăn nhẹ gì đi! 💪",
                },
                "slightly_over": {
                    "body_template": "Thoải mái bạn ơi! Vượt một ít {excess} cal — tiếp tục nha! 😎",
                },
                "way_over": {
                    "body_template": "Không sao bạn ơi! Vượt {excess} cal — mai là ngày mới! 🤙",
                },
            },
            "trial_expiry": {
                "2d": {
                    "title": "Nutree",
                    "body": "Còn 2 ngày là trial hết hạn nha bạn ơi — giữ streak nào! ⏳",
                },
                "1d": {
                    "title": "Nutree",
                    "body": "Ngày cuối rồi bạn ơi — trial mai hết hạn. Tiếp tục nha! 🔥",
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
