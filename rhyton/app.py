from jayhawk.dispatch import SpartanRequestDispatcher
from werkzeug.routing import Rule, Map, NotFound

class Rhyton:
	"""
	A rhyton is a kind of horn-shaped cup that was common in Persia (the name comes from the Greek word for it; the Persians called them takuk).

	To use Rhyton:

	>>> app = Rhyton("example.com")
	"""
	# Default configuration values
	DEFAULT_CONFIG = {}
	# Rule class
	RULE_CLASS = Rule
	# Map class
	MAP_CLASS = Map
	def __init__(self,host=None,**config):
		assert host, "Must provide host argument"
		config["host"]=host
		self.config = self.make_config(config)
		self.map = self.MAP_CLASS()
		self.view_functions = {}
	def make_config(self,config):
		ret = dict()
		# first apply defaults
		ret.update(self.DEFAULT_CONFIG)
		# then apply changes
		ret.update(config)
		return ret
	def route(self,rule,endpoint=None,**options):
		def __wrapper(func):
			self.add_rule(rule,func,endpoint,**options)
			return func
		return __wrapper
	def add_rule(self,rule,view_func,endpoint=None,**options):
		if endpoint is None:
			assert view_func is not None, "Must provide either view function or endpoint name!"
			endpoint = view_func.__name__
		options["endpoint"] = endpoint
		rule = self.RULE_CLASS(rule,**options)
		self.map.add(rule)
		if view_func is not None:
			assert (old_func:=self.view_functions.get(endpoint)) is None or old_func==view_func, f"View function mapping would overwrite an existing endpoint {endpoint}!"
			self.view_functions[endpoint]=view_func
	def build_adapter(self):
		map_adapter = self.map.bind(self.config["host"])
		adapter = type("_RhytonAdapter",(RhytonAdapter,),{"map_adapter":map_adapter,"rhyton":self})
		adapter.context = Context(adapter)
		return adapter

class Context:
	def __init__(self,adapter):
		self.adapter = adapter
	@property
	def rhyton(self):
		return self.adapter.rhyton
	def redirect(self,endpoint,**args):
		path = self.adapter.map_adapter.build(endpoint,args)
		return Response(b'',path,3)
	def bind(self,host,path,data=b''):
		return BoundContext(self.adapter,host,path,data)

class BoundContext(Context):
	def __init__(self,adapter,host,path,data=b''):
		super(BoundContext,self).__init__(adapter)
		self.host=host
		self.path=path
		self.data=data
		self._teardown_funcs = []
		self._torndown = False
	@property
	def has_data(self):
		return bool(self.data)
	def register_teardown(self,func):
		self._teardown_funcs.append(func)
	def teardown(self):
		for func in self._teardown_funcs: func(self)
		self._torndown = False
	def __del__(self):
		if not self._torndown: self.teardown()

class Response:
	def __init__(self,content=b'',meta="text/gemini",response_code=2):
		self.__dict__.update(locals())
		if type(self.content)==str: self.content = self.content.encode("utf-8")
	def handle(self,adapter):
		adapter.response_code(self.response_code,self.meta)
		if self.response_code==2:
			adapter.wfile.write(self.content)

DEFAULT_META = {
	4: "Client Error",
	5: "Server Error"
}
def abort(response_code,meta=None):
	try:
		meta = meta or DEFAULT_META[response_code]
		return Response(meta=meta,response_code=response_code)
	except KeyError:
		raise TypeError(f'No default meta for response code {response_code}') from None

class RhytonAdapter(SpartanRequestDispatcher):
	def handle_request(self, host, path, data=b''):
		if host!=self.rhyton.config["host"]:
			self.response_code(4,f"Your princess is in another castle! (This adapter is for {self.rhyton.config['host']})")
			return
		try:
			endpoint, args = self.map_adapter.match(path)
		except NotFound:
			self.response_code(4,"Not Found")
			return
		ctx = self.context.bind(host,path,data)
		rv = self.rhyton.view_functions[endpoint](ctx,**args)
		ctx.teardown()
		if not type(rv)==Response:
			if type(rv) in (str, bytes):
				rv = Response(rv)
			elif type(rv) in (list, tuple):
				rv = Response(*rv)
			else:
				raise TypeError(f"Cannot figure out how to handle view function return value {rv!r}")
		rv.handle(self)
