"""Email template renderer using Jinja2."""

import os

from jinja2 import Environment, FileSystemLoader


class EmailTemplateRenderer:
    """Renders email templates with Jinja2."""

    def __init__(self):
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "templates", "emails"
        )
        self._env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
        )

    def render(self, template_name: str, context: dict) -> str:
        """Render an email template.

        Args:
            template_name: Name of template without .html extension
            context: Variables to pass to template

        Returns:
            Rendered HTML string
        """
        template = self._env.get_template(f"{template_name}.html")
        return template.render(**context)
