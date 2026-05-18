"""APNs payload builder for Time Sensitive notifications.

Pure-function builder: produces messaging.APNSConfig with the
`interruption-level` key placed in the payload body (per Apple spec),
not in HTTP headers (where APNs silently drops it).
"""

from firebase_admin import messaging


def build_apns_config(title: str, body: str) -> messaging.APNSConfig:
    """Build APNs config with Time Sensitive interruption level in payload body.

    Empty title maps to None so firebase-admin omits the key entirely. APNs
    expects either a non-empty string or absent key — empty string is undefined
    behavior on iOS 15+ Time Sensitive and may suppress the banner.
    """
    alert_title = title if title else None
    return messaging.APNSConfig(
        headers={
            "apns-priority": "10",
            "apns-push-type": "alert",
        },
        payload=messaging.APNSPayload(
            aps=messaging.Aps(
                alert=messaging.ApsAlert(title=alert_title, body=body),
                sound="default",
                badge=1,
                mutable_content=True,
                custom_data={"interruption-level": "time-sensitive"},
            )
        ),
    )
