class TemplateEngine:
	"""A base class for template engines. BoundContext.render_template calls TemplateEngine.render_template with the template name and context."""
	def __init__(self,app):
		self.app = app
	def render_template(self,template,**context):
		raise NotImplementedError

from jinja2 import Environment, FunctionLoader, TemplateNotFound
import os.path

class Jinja2TemplateEngine(TemplateEngine):
	"""Default TemplateEngine subclass. Uses jinja2 templating."""
	def __init__(self,app):
		self.app = app
		self.env = Environment(loader=FunctionLoader(self.load_template),autoescape=self.app.config.get("autoescape",False))
	def render_template(self,template,**context):
		template_obj = self.env.get_template(template)
		rv = template_obj.render(context)
		return rv
	def load_template(self,name):
		name = self.__sanitize_template(name)
		if name is None: return
		searchpath = self.app.config.get("searchpath",["templates"])
		for dir in searchpath:
			path = os.path.join(dir,name)
			if os.path.exists(path):
				with open(path) as f:
					return f.read()
	def __sanitize_template(self,name):
		pieces = []
		for piece in name.split("/"):
			if (
				os.path.sep in piece
				or (os.path.altsep and os.path.altsep in piece)
				or piece == os.path.pardir
			):
				return None
			elif piece and piece != ".":
				pieces.append(piece)
		return os.path.join(*pieces)

