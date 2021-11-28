from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader(__name__.split(".", maxsplit=1)[0], "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)
help_template = env.get_template("help.j2")
