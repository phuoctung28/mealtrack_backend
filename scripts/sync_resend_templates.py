#!/usr/bin/env python3
"""
Sync email templates with Resend.

Usage:
    python scripts/sync_resend_templates.py push          # Push all templates to Resend
    python scripts/sync_resend_templates.py push welcome  # Push specific template
    python scripts/sync_resend_templates.py list          # List templates in Resend
    python scripts/sync_resend_templates.py preview       # Preview templates locally
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import resend
from src.infra.config.settings import get_settings
from src.infra.services.email_template_renderer import EmailTemplateRenderer

TEMPLATES = {
    "welcome": {
        "subject": "Your nutrition journey starts now, {{first_name}}! 🎉",
        "description": "Sent after onboarding",
    },
    "reengagement": {
        "subject": "We saved your progress, {{first_name}} 📊",
        "description": "Re-engage inactive users",
    },
    "trial_expiring": {
        "subject": "In {{days_left}} days, your macros go dark ⏰",
        "description": "Trial expiring reminder",
    },
    "trial_cancelled": {
        "subject": "Before you go — one quick question? 🤔",
        "description": "Cancellation feedback request",
    },
}

SAMPLE_DATA = {
    "subject": "Test",
    "first_name": "Alex",
    "tdee": 2100,
    "streak_days": 7,
    "days_left": 2,
    "meals_logged": 42,
    "user_id": "sample-user-123",
    "app_url": "https://app.nutree.app",
    "upgrade_url": "https://app.nutree.app/upgrade",
    "feedback_url": "https://app.nutree.app/feedback",
    "pause_url": "https://app.nutree.app/pause",
    "unsubscribe_url": "https://app.nutree.app/unsubscribe?user=sample",
}


def init_resend():
    settings = get_settings()
    if not settings.RESEND_API_KEY:
        print("❌ RESEND_API_KEY not configured")
        sys.exit(1)
    resend.api_key = settings.RESEND_API_KEY


def list_templates():
    """List all templates in Resend."""
    init_resend()

    print("\n📋 Templates in Resend:\n")
    result = resend.Templates.list()
    templates = result.get("data", [])

    if not templates:
        print("  (none)")
        return

    for t in templates:
        print(f"  • {t.get('name')} (ID: {t.get('id')})")
        print(f"    Created: {t.get('created_at')}")

    print(f"\n  Total: {len(templates)} templates")


def render_subject(subject: str, data: dict) -> str:
    """Render mustache-style variables in subject line."""
    result = subject
    for key, value in data.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def push_templates(template_name: str | None = None):
    """Push templates to Resend."""
    init_resend()
    renderer = EmailTemplateRenderer()

    # Get existing templates
    existing = resend.Templates.list()
    existing_map = {t.get("name"): t.get("id") for t in existing.get("data", [])}

    templates_to_push = {template_name: TEMPLATES[template_name]} if template_name else TEMPLATES

    print(f"\n🚀 Pushing {len(templates_to_push)} template(s) to Resend...\n")

    for name, config in templates_to_push.items():
        try:
            rendered_subject = render_subject(config["subject"], SAMPLE_DATA)
            data = {**SAMPLE_DATA, "subject": rendered_subject}
            html = renderer.render(name, data)

            if name in existing_map:
                resend.Templates.update({
                    "id": existing_map[name],
                    "html": html,
                    "subject": rendered_subject,
                })
                print(f"  ✅ Updated: {name} (ID: {existing_map[name]})")
            else:
                result = resend.Templates.create({
                    "name": name,
                    "html": html,
                    "subject": config["subject"],
                })
                print(f"  ✅ Created: {name} (ID: {result.get('id')})")

        except Exception as e:
            print(f"  ❌ Failed: {name} - {e}")

    print("\n✨ Done! View templates at https://resend.com/templates")


def preview_templates():
    """Preview templates locally by saving to HTML files."""
    renderer = EmailTemplateRenderer()
    output_dir = Path(__file__).parent / "template_previews"
    output_dir.mkdir(exist_ok=True)

    print(f"\n👀 Generating previews in {output_dir}...\n")

    for name, config in TEMPLATES.items():
        rendered_subject = render_subject(config["subject"], SAMPLE_DATA)
        data = {**SAMPLE_DATA, "subject": rendered_subject}
        html = renderer.render(name, data)

        output_file = output_dir / f"{name}.html"
        output_file.write_text(html)
        print(f"  ✅ {name}.html")

    print(f"\n✨ Open files in browser to preview")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "push":
        template_name = sys.argv[2] if len(sys.argv) > 2 else None
        if template_name and template_name not in TEMPLATES:
            print(f"❌ Unknown template: {template_name}")
            print(f"   Available: {', '.join(TEMPLATES.keys())}")
            sys.exit(1)
        push_templates(template_name)

    elif command == "list":
        list_templates()

    elif command == "preview":
        preview_templates()

    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
