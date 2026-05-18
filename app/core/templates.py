import weasyprint
from jinja2 import Environment, BaseLoader, select_autoescape

# Configuración de Jinja2 con cargador desde cadenas
template_env = Environment(
    loader=BaseLoader(),  # Las plantillas se pasarán como string
    autoescape=select_autoescape(['html', 'xml'])
)

async def generate_pdf_from_template_string(html_content: str, data: dict) -> bytes:
    """
    Renderiza el HTML dado con los datos y devuelve el PDF como bytes.
    """
    template = template_env.from_string(html_content)
    rendered_html = template.render(data)
    pdf_bytes = weasyprint.HTML(string=rendered_html).write_pdf()
    return pdf_bytes