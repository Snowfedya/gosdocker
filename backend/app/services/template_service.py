from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from datetime import datetime, timezone

class TemplateService:
    def __init__(self, templates_dir: str = "templates"):
        base_dir = Path(__file__).parent.parent  # app/
        self.templates_path = base_dir / templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_path)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        # Add datetime to global context
        self.env.globals['now'] = lambda: datetime.utcnow()

    def render(self, template_path: str, context: dict) -> str:
        """Render Jinja2 template with context."""
        template = self.env.get_template(template_path)
        return template.render(**context)

    def render_single(self, component_slug: str, config: dict) -> str:
        """Render docker-compose for a single component."""
        template_path = f"single/{component_slug}/docker-compose.yml.j2"
        return self.render(template_path, {"config": config, "registry_url": config.get("registry_url", "")})

    def render_stack(self, stack_slug: str, components: list, configs: dict) -> str:
        """Render docker-compose for a stack (multiple components)."""
        template_path = f"stacks/{stack_slug}.yml.j2"
        return self.render(template_path, {
            "components": components,
            "configs": configs
        })