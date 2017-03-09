	TAGS	UNSORTED
Command	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	808	class Command(BaseCommand):
note	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	1645	    def note(self, msg):
log	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	1737	    def log(self, msg):
do_cmd	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	1870	    def do_cmd(self, cmd, *args):
svn_admin_cmd	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	2484	    def svn_admin_cmd(self, *args):
create_svn	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	2583	    def create_svn(self, svn):
remove_demo_components	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	3097	    def remove_demo_components(self, group, env):
remove_demo_milestones	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	3286	    def remove_demo_milestones(self, group, env):
symlink_to_master_assets	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	3475	    def symlink_to_master_assets(self, group, env):
add_wg_draft_states	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	3854	    def add_wg_draft_states(self, group, env):
add_wiki_page	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	4112	    def add_wiki_page(self, env, name, text):
add_default_wiki_pages	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	4404	    def add_default_wiki_pages(self, group, env):
add_custom_wiki_pages	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	5023	    def add_custom_wiki_pages(self, group, env):
sync_default_repository	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	5331	    def sync_default_repository(self, group, env):
create_trac	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	5630	    def create_trac(self, group):
update_trac_permissions	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	7769	    def update_trac_permissions(self, group, env):
update_trac_components	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	9467	    def update_trac_components(self, group, env):
maybe_add_group_url	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	10949	    def maybe_add_group_url(self, group, name, url):
add_custom_pages	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	11271	    def add_custom_pages(self, group, env):
add_custom_group_states	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	11398	    def add_custom_group_states(self, group, env):
handle	/a/www/ietf-datatracker/web/ietf/utils/management/commands/create_group_wikis.py	11603	    def handle(self, *filenames, **options):
filetext	service.py	980	def filetext(file):
read_whitelist	service.py	1498	def read_whitelist(files):
read_regexes	service.py	1983	def read_regexes(files):
read_blacklist	service.py	2900	def read_blacklist(files):
recent_count	service.py	3386	def recent_count(pending_list):
read_pending_file	service.py	3716	def read_pending_file(path, cutoff):
write_pending_file	service.py	4346	def write_pending_file(path, pending_conf_list):
read_pending_dir	service.py	4638	def read_pending_dir(dir):
read_data	service.py	5207	def read_data():
sighup_handler	service.py	6025	def sighup_handler(signum, frame):
setup	service.py	6191	def setup(configuration, files):
sendmail	service.py	6512	def sendmail(sender, recipient, subject, text, conf={"smtp_host":"localhost",}, headers={}):
cache_mail	service.py	7164	def cache_mail():
hash	service.py	7673	def hash(bytes):
make_hash	service.py	7870	def make_hash(sender, recipient, filename):
pad	service.py	8060	def pad(bytes):
request_confirmation	service.py	8265	def request_confirmation(sender, recipient, cachefn, headers, text):
verify_confirmation	service.py	11757	def verify_confirmation(sender, recipient, msg):
valid_hash	service.py	13234	def valid_hash(sender, recipient, filename, hash):
forward_whitelisted_post	service.py	13937	def forward_whitelisted_post(sender, recipient, cachefn, msg, all):
strip_batv	service.py	14657	def strip_batv(sender):
handler	service.py	15053	def handler():
Methods	fdpass.c	464	static PyMethodDef Methods[] = {
initfdpass	fdpass.c	886	void initfdpass(void)
send_fd	fdpass.c	971	static PyObject* send_fd(PyObject *self, PyObject *args)
recv_fd	fdpass.c	2017	static PyObject* recv_fd(PyObject *self, PyObject *args)
PROGNAME	postconfirmc.c	350	#define PROGNAME "postconfirm"
DEBUG	postconfirmc.c	381	#define DEBUG    0
DO_SEND_ARGS	postconfirmc.c	401	#define DO_SEND_ARGS     1
DO_SEND_ENV	postconfirmc.c	428	#define DO_SEND_ENV      1
DO_SEND_FD_NAMES	postconfirmc.c	455	#define DO_SEND_FD_NAMES 1
debug	postconfirmc.c	483	#define debug fprintf
SOCK_PATH	postconfirmc.c	505	#define SOCK_PATH	"/var/run/postconfirm/socket"
SOCK_BUF_LEN	postconfirmc.c	553	#define SOCK_BUF_LEN	256
MY_ARGC	postconfirmc.c	578	#define MY_ARGC 1
debugf	postconfirmc.c	1338	FILE *debugf;
do_debug	postconfirmc.c	1351	int  do_debug;
main	postconfirmc.c	1366	int main(int argc, char **argv)
myflush	postconfirmc.c	2739	void myflush(FILE *stream)
myclose	postconfirmc.c	2823	void myclose(FILE *stream)
myconnect	postconfirmc.c	2906	int myconnect(const char *path)
send_args	postconfirmc.c	3289	void send_args(FILE *stream, int argc, char **argv)
send_named_fd	postconfirmc.c	3545	void send_named_fd(FILE *stream, const char *name, int fd)
send_env	postconfirmc.c	3799	void send_env(FILE *stream)
count_env	postconfirmc.c	4126	int count_env()
read_exit_code	postconfirmc.c	4243	int read_exit_code(FILE *stream)
write_netstring_nulled	postconfirmc.c	4422	void write_netstring_nulled(FILE *stream, const char *ptr)
write_netstring	postconfirmc.c	4638	void write_netstring(FILE *stream, const void *ptr, unsigned len)
write_netint	postconfirmc.c	4995	void write_netint(FILE *stream, int l)
read_netint	postconfirmc.c	5156	int read_netint(FILE *stream)
read_netstring	postconfirmc.c	5615	char* read_netstring(FILE *stream, unsigned *len_ptr)
verify_expected	postconfirmc.c	6610	void verify_expected(FILE *stream, const char *expected)
usage	postconfirmc.c	6968	void usage(void)
error	postconfirmc.c	7073	void error(const char *msg)
proto_error	postconfirmc.c	7144	void proto_error(const char *msg)
send_fd	postconfirmc.c	7271	void send_fd(int s, int fd)
InterpolatorError	interpolate.py	3711	class InterpolatorError(ValueError):
__init__	interpolate.py	3750	    def __init__(self, text, pos):
__str__	interpolate.py	3833	    def __str__(self):
pymatchorfail	interpolate.py	3952	def pymatchorfail(text, pos):
shmatchorfail	interpolate.py	4117	def shmatchorfail(text, pos):
Interpolator	interpolate.py	4398	class Interpolator:
__init__	interpolate.py	4730	    def __init__(self, format, loc=None, glob=None):
__repr__	interpolate.py	8264	    def __repr__(self):
__str__	interpolate.py	8347	    def __str__(self):
interpolate	interpolate.py	9461	def interpolate(text, loc=None, glob=None): return str(Interpolator(text, loc, glob))
iprint	interpolate.py	9547	def iprint(text): print interpolate(text)
InterpolatorFile	interpolate.py	9592	class InterpolatorFile:
__init__	interpolate.py	9693	    def __init__(self, file): self.file = file
__repr__	interpolate.py	9740	    def __repr__(self): return "<interpolated " + repr(self.file) + ">"
__getattr__	interpolate.py	9812	    def __getattr__(self, attr): return getattr(self.file, attr)
write	interpolate.py	9877	    def write(self, text): self.file.write(str(Interpolator(text)))
filter	interpolate.py	9942	def filter(file=sys.stdout):
unfilter	interpolate.py	10262	def unfilter(ifile=None):
_test	interpolate.py	10576	def _test():
mkdir	postconfirmd.py	1965	def mkdir(path):
mkfile	postconfirmd.py	2123	def mkfile(file):
sendmail	sendmail.py	101	def sendmail(sender, recipient, subject, text, conf={"smtp_host":"localhost",}, headers={}):
ProtocolError	sockserver.py	3789	class ProtocolError(Exception):
TimeoutError	sockserver.py	3831	class TimeoutError(Exception):
Singleton	sockserver.py	3872	class Singleton(object):
__new__	sockserver.py	3899	    def __new__(cls, *args, **kwds):
Output	sockserver.py	4069	class Output(Singleton):
__init__	sockserver.py	4196	    def __init__(self, quiet=None, debug=None):
data	sockserver.py	4345	    def data(self, msg):
warn	sockserver.py	4388	    def warn(self, msg):
debug	sockserver.py	4468	    def debug(self, msg):
ReadyExecHandler	sockserver.py	4548	class ReadyExecHandler(SocketServer.StreamRequestHandler, object):
__init__	sockserver.py	5132	    def __init__(self, request, client_address, server):
handle	sockserver.py	5417	    def handle(self):
handle_conduit	sockserver.py	5940	    def handle_conduit(self):
handle_conduit_as_subchild	sockserver.py	6432	    def handle_conduit_as_subchild(self):
handle_stop	sockserver.py	7939	    def handle_stop(self):
stop_server	sockserver.py	7998	    def stop_server(self):
read_args	sockserver.py	8075	    def read_args(self):
read_fd	sockserver.py	8334	    def read_fd(self, stream_name):
read_environ	sockserver.py	8563	    def read_environ(self):
tell_exit	sockserver.py	8942	    def tell_exit(self, code):
send_string	sockserver.py	9036	    def send_string(self, msg):
send_long	sockserver.py	9173	    def send_long(self, msg):
read_string	sockserver.py	9302	    def read_string(self):
read_long	sockserver.py	9440	    def read_long(self):
verify_expected	sockserver.py	9571	    def verify_expected(self, expected):
ReadyExec	sockserver.py	9778	class ReadyExec(SocketServer.ForkingMixIn,
__init__	sockserver.py	9938	    def __init__(self, to_run, cs_path, quiet=0, debug=0):
handle_signal	sockserver.py	10480	    def handle_signal(self, sig, frame):
install_signal_handlers	sockserver.py	10588	    def install_signal_handlers(self):
reset_signal_handlers	sockserver.py	10787	    def reset_signal_handlers(self):
server_close	sockserver.py	10976	    def server_close(self):
handle_request	sockserver.py	11142	    def handle_request(self):
process_request	sockserver.py	11537	    def process_request(self, request, address):
finish_request	sockserver.py	12541	    def finish_request(self, request, address):
netint	sockserver.py	12918	def netint(i):
read_netint	sockserver.py	12988	def read_netint(f):
netstring	sockserver.py	13290	def netstring(str):
read_netstring	sockserver.py	13429	def read_netstring(f):
read_uint	sockserver.py	14033	def read_uint(f, maxdigits=4):
raise_TimeoutError	sockserver.py	14750	def raise_TimeoutError(signum, frame):
ConfigInputStream	config.py	3567	class ConfigInputStream(object):
__init__	config.py	3821	    def __init__(self, stream):
read	config.py	4950	    def read(self, size):
close	config.py	5217	    def close(self):
readline	config.py	5267	    def readline(self):
ConfigOutputStream	config.py	5551	class ConfigOutputStream(object):
__init__	config.py	5809	    def __init__(self, stream, encoding=None):
write	config.py	6764	    def write(self, data):
flush	config.py	6824	    def flush(self):
close	config.py	6874	    def close(self):
defaultStreamOpener	config.py	6920	def defaultStreamOpener(name):
ConfigError	config.py	7571	class ConfigError(Exception):
ConfigFormatError	config.py	7691	class ConfigFormatError(ConfigError):
ConfigResolutionError	config.py	7847	class ConfigResolutionError(ConfigError):
isWord	config.py	8007	def isWord(s):
makePath	config.py	8682	def makePath(prefix, suffix):
Container	config.py	9523	class Container(object):
__init__	config.py	9799	    def __init__(self, parent):
setPath	config.py	10056	    def setPath(self, path):
evaluate	config.py	10346	    def evaluate(self, item):
writeToStream	config.py	11061	    def writeToStream(self, stream, indent, container):
writeValue	config.py	11641	    def writeValue(self, value, stream, indent):
Mapping	config.py	12118	class Mapping(Container):
__init__	config.py	12236	    def __init__(self, parent=None):
__delitem__	config.py	12698	    def __delitem__(self, key):
__getitem__	config.py	13087	    def __getitem__(self, key):
__getattribute__	config.py	13326	    def __getattribute__(self, name):
iteritems	config.py	13849	    def iteritems(self):
__contains__	config.py	13969	    def __contains__(self, item):
addMapping	config.py	14088	    def addMapping(self, key, value, comment, setting=False):
__setattr__	config.py	15038	    def __setattr__(self, name, value):
keys	config.py	15159	    def keys(self):
get	config.py	15316	    def get(self, key, default=None):
__str__	config.py	15504	    def __str__(self):
__repr__	config.py	15586	    def __repr__(self):
__len__	config.py	15670	    def __len__(self):
__iter__	config.py	15753	    def __iter__(self):
iterkeys	config.py	15809	    def iterkeys(self):
writeToStream	config.py	15921	    def writeToStream(self, stream, indent, container):
save	config.py	16746	    def save(self, stream, indent=0):
Config	config.py	17801	class Config(Mapping):
Namespace	config.py	17976	    class Namespace(object):
__init__	config.py	18146	        def __init__(self):
__init__	config.py	18223	    def __init__(self, streamOrFile=None, parent=None):
load	config.py	19443	    def load(self, stream):
addNamespace	config.py	20167	    def addNamespace(self, ns, name=None):
removeNamespace	config.py	20835	    def removeNamespace(self, ns, name=None):
save	config.py	21303	    def save(self, stream, indent=0):
getByPath	config.py	21877	    def getByPath(self, path):
Sequence	config.py	22319	class Sequence(Container):
SeqIter	config.py	22446	    class SeqIter(object):
__init__	config.py	22578	        def __init__(self, seq):
__iter__	config.py	22733	        def __iter__(self):
next	config.py	22786	        def next(self):
__init__	config.py	22972	    def __init__(self, parent=None):
append	config.py	23318	    def append(self, item, comment):
__getitem__	config.py	23728	    def __getitem__(self, index):
__iter__	config.py	24288	    def __iter__(self):
__repr__	config.py	24351	    def __repr__(self):
__str__	config.py	24435	    def __str__(self):
__len__	config.py	24528	    def __len__(self):
writeToStream	config.py	24610	    def writeToStream(self, stream, indent, container):
save	config.py	25435	    def save(self, stream, indent):
Reference	config.py	26376	class Reference(object):
__init__	config.py	26501	    def __init__(self, config, type, ident):
addElement	config.py	26979	    def addElement(self, type, ident):
findConfig	config.py	27305	    def findConfig(self, container):
resolve	config.py	27798	    def resolve(self, container):
__str__	config.py	29309	    def __str__(self):
__repr__	config.py	29633	    def __repr__(self):
Expression	config.py	29686	class Expression(object):
__init__	config.py	29820	    def __init__(self, op, lhs, rhs):
__str__	config.py	30330	    def __str__(self):
__repr__	config.py	30412	    def __repr__(self):
evaluate	config.py	30467	    def evaluate(self, container):
ConfigReader	config.py	31631	class ConfigReader(object):
__init__	config.py	31742	    def __init__(self, config):
location	config.py	32301	    def location(self):
getChar	config.py	32657	    def getChar(self):
__repr__	config.py	33121	    def __repr__(self):
getToken	config.py	33223	    def getToken(self):
load	config.py	37135	    def load(self, stream, parent=None, suffix=None):
setStream	config.py	38404	    def setStream(self, stream):
match	config.py	38881	    def match(self, t):
parseMappingBody	config.py	39567	    def parseMappingBody(self, parent):
parseKeyValuePair	config.py	39916	    def parseKeyValuePair(self, parent):
parseValue	config.py	41372	    def parseValue(self, parent, suffix):
parseSequence	config.py	42248	    def parseSequence(self, parent, suffix):
parseMapping	config.py	43417	    def parseMapping(self, parent, suffix):
parseScalar	config.py	44269	    def parseScalar(self):
parseTerm	config.py	44809	    def parseTerm(self):
parseFactor	config.py	45301	    def parseFactor(self):
parseReference	config.py	46366	    def parseReference(self, type):
parseSuffix	config.py	46765	    def parseSuffix(self, ref):
defaultMergeResolve	config.py	47533	def defaultMergeResolve(map1, map2, key):
overwriteMergeResolve	config.py	48537	def overwriteMergeResolve(map1, map2, key):
ConfigMerger	config.py	49097	class ConfigMerger(object):
__init__	config.py	49464	    def __init__(self, resolver=defaultMergeResolve):
merge	config.py	50043	    def merge(self, merged, mergee):
mergeMapping	config.py	50464	    def mergeMapping(self, map1, map2):
mergeSequence	config.py	51614	    def mergeSequence(self, seq1, seq2):
handleMismatch	config.py	52343	    def handleMismatch(self, obj1, obj2):
ConfigList	config.py	52664	class ConfigList(list):
getByPath	config.py	52897	    def getByPath(self, path):
createDaemon	daemonize.py	1228	def createDaemon():
