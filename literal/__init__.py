"""Python code generation tool."""
from __future__ import absolute_import

VERSION = (1, 0, 0)
__version__ = ".".join(map(str, VERSION[0:3])) + "".join(VERSION[3:])
__author__ = "Ask Solem"
__contact__ = "ask@celeryproject.org"
__homepage__ = "http://github.com/ask/literal.py/"
__docformat__ = "restructuredtext en"

# -eof meta-

from inspect import getargspec
from itertools import imap

#: map of infix operators
infices = [
    ('+', "__add__", "add"),
    ('-', "__sub__", "sub"),
    ('*', "__mul__", "mul"),
    ('/', "__div__", "div"),
    ('%', "__mod__", "mod"),
    ('&', "__and__", "band"),
    ('^', "__xor__", "xor"),
    ('|', "__or__", "bor"),
    ('<', None, "lt"),
    ('>', None, "gt"),
    ('<=', None, "le"),
    ('>=', None, "ge"),
    ('==', None, "eq"),
    ('!=', None, "ne"),
    ('//', "__floordiv", "floordiv"),
    ('**', "__pow__", "pow"),
    ('<<', "__lshift__", "lshift"),
    ('>>', "__rshift__", "rshift"),
    ('and', None, "and_"),
    ('or', None, "or_"),
]

#: map of inplace infix operators.
infices_inplace = [
    ('=', "__ilshift__", "assign"),
    ('+=', "__iadd__", "inplace_add"),
    ('-=', "__isub__", "inplace_sub"),
    ('*=', "__imul__", "inplace_mul"),
    ('/=', "__idiv__", "inplace_div"),
    ('%=', "__imod__", "inplace_mod"),
    ('&=', "__iand__", "inplace_and"),
    ('^=', "__ixor__", "inplace_xor"),
    ('|=', "__ior__", "inplace_or"),
    ('**=', "__ipow__", "inplace_pow"),
    ('<<=', None, "inplace_lshift"),
    ('>>=', "__irshift__", "inplace_rshift"),
]


def textindent(s, n=4):
    """Indents text."""
    return '\n'.join(' ' * n + line for line in s.split('\n'))


def reprkwargs(kwargs, sep=', ', fmt="{0!s}={1!r}"):
    """Display kwargs."""
    return sep.join(fmt.format(k, v) for k, v in kwargs.iteritems())


def reprargs(args, sep=', ', filter=repr):
    return sep.join((map(filter, args)))


def reprcall(name, args=(), kwargs=(), keywords='', sep=', ',
        argfilter=repr):
    """Format a function call for display."""
    if keywords:
        keywords = ((', ' if (args or kwargs) else '') +
                    '**' + keywords)
    argfilter = argfilter or repr
    return "{name}({args}{sep}{kwargs}{keywords})".format(
            name=name, args=reprargs(args, filter=argfilter),
            sep=(args and kwargs) and sep or "",
            kwargs=reprkwargs(kwargs, sep), keywords=keywords or '')


def reprsig(fun, name=None, method=False):
    """Format a methods signature for display."""
    args, varargs, keywords, defs, kwargs = [], [], None, [], {}
    argspec = fun
    if callable(fun):
        name = fun.__name__ if name is None else name
        argspec = getargspec(fun)
    try:
        args = argspec[0]
        varargs = argspec[1]
        keywords = argspec[2]
        defs = argspec[3]
    except IndexError:
        pass
    if defs:
        args, kwkeys = args[:-len(defs)], args[-len(defs):]
        kwargs = dict(zip(kwkeys, defs))
    if varargs:
        args.append('*' + varargs)
    if method:
        args.insert(0, 'self')
    return reprcall(name, map(str, args), kwargs, keywords,
                    argfilter=str)


class _node(object):
    """base class for root + node."""

    def _new_node(self, *s, **kwargs):
        return self.leaf(*s, **dict(kwargs, root=self.root))

    def node(self, *s):
        return self.root.add(self._new_node(*s))

    def __unicode__(self):
        return self.s

    def __str__(self):
        return str(unicode(self))

    def __repr__(self):
        return str(self)


class _ops(type):
    """metaclass for :class:`node` with infix operators."""

    def __new__(cls, name, bases, attrs):

        def create_infix_op(op, name, inplace=False):

            def _infixop(self, other):
                return (self.infix_inplace if inplace
                                           else self.infix)(op, other)
            _infixop.__name__ = name
            return _infixop

        for op, override, alias in infices:
            attrs[override] = attrs[alias] = \
                    create_infix_op(op, override or alias)
        for op, override, alias in infices_inplace:
            attrs[override] = attrs[alias] = \
                    create_infix_op(op, override or alias, inplace=True)
        return super(_ops, cls).__new__(cls, name, bases, attrs)


class node(_node):
    __metaclass__ = _ops

    def __init__(self, *s, **kwargs):
        self.root = kwargs.get("root", self)
        self.s = '\n'.join(s)
        self.leaf = node

    def symbol(self, k):
        return self.root.symbol(k)
    var = sym = call = symbol

    def literal(self, k):
        return self.root.literal(k)
    lit = literal

    def prefix(self, fmt, node):
        return self.maybe_replace(self._new_node(
                    fmt.format(get_value(node))), replace_vars=True)

    def suffix(self, suffix):
        x = self._new_node(get_value(self) + suffix)
        return self.maybe_replace(x)

    def infix(self, op, rhs):
        n = self._new_node(
                ' '.join(map(unicode, [self.value, op, get_value(rhs)])))
        self.remove(self)
        self.maybe_replace(n, rhs)
        return n

    def infix_inplace(self, op, rhs):
        self.infix(op, rhs)
        return self

    def returns(self, sym):
        return self.prefix('return {0!s}', sym)

    def _eval_list(self, l):
        return map(get_value, l)

    def _eval_dict(self, d):
        return {k: get_value(v) for k, v in d.iteritems()}

    def __call__(self, *args, **kwargs):
        _args = list(args)
        _values = list(kwargs.values())
        n = self.maybe_replace(
                self._new_node(reprcall(self.value, args,
                                        self._eval_dict(kwargs))))
        map(self.remove, _args + _values)
        return n

    def wrap(self, prefix=None, suffix=None):
        return self.maybe_replace(
                self._new_node((prefix or '')
                             + get_value(self)
                             + (suffix or '')))

    def group(self):
        return self.wrap('(', ')')

    def _maybe_format_slice(self, key):
        if isinstance(key, slice):
            return "{}:{}".format(get_value(self.remove(key.start) or ''),
                                  get_value(self.remove(key.stop) or ''))
        return repr(key)

    def __getitem__(self, k):
        return self.suffix('[{}]'.format(self._maybe_format_slice(k), ))

    def __getattr__(self, k):
        return self.suffix('.{}'.format(k))

    def maybe_replace(self, n, prev=None, replace_vars=False):
        prev = self if prev is None else prev
        if not replace_vars and isinstance(prev, symbol):
            return self.root.add(n)
        return self.root.maybe_replace(prev, n)

    def remove(self, n):
        return self.root.remove(n)

    @property
    def value(self):
        return unicode(self)

    @value.setter            # noqa
    def value(self, value):
        self.s = value


class _v(object):
    """``root.v.foo`` == ``root.var('foo')``"""

    def __init__(self, root):
        self.root = root

    def __getattr__(self, name):
        return self.root.var(name)


class root(_node):

    def __init__(self):
        self.root = self
        self.leaf = node
        self.next = []
        self.v = _v(self)

    def add(self, n):
        if n != self and not isinstance(n, symbol):
            self.next.append(n)
        return n

    def indent(self, n=4):
        return textindent(unicode(self), n)

    def tuple(self, *values):
        return self.symbol(', '.join(map(get_value, values)))

    def as_fun(self, fun, name=None, indent=0, decorators=None):
        decorators = ['@{0!s}'.format(get_value(dec))
                        for dec in decorators or []]
        return '\n'.join(decorators +
            [textindent('def {}:'.format(reprsig(fun, name)), indent),
             self.indent(indent + 4)])

    def symbol(self, name):
        return self.add(symbol(name, root=self))
    var = sym = call = symbol

    def literal(self, k):
        return self.add(literal(k, root=self))
    lit = literal

    def vars(self, *names):
        return list(map(self.symbol, names))

    def __unicode__(self):
        return '\n'.join(filter(None, imap(unicode, self)))

    def __iter__(self):
        for node in self.next:
            yield node

    def remove(self, unwanted):
        if isinstance(unwanted, node):
            try:
                self.next.remove(unwanted)
            except ValueError:
                pass
        return unwanted

    def dump(self, desc=None):
        if desc:
            print(desc)

        for node in self.next:
            if not isinstance(node, symbol):
                print("NODE: {}".format(node.s))
            else:
                print("<symbol: {!r}>".format(node.value))

    def replace(self, a, b):
        try:
            idx = self.next.index(a)
            prev, self.next[idx] = self.next[idx], b
        except ValueError:
            self.add(b)  # no node to replace, so add it.
        return b

    def maybe_replace(self, prev, n, replace_vars=False):
        if not replace_vars and isinstance(n, symbol):
            self.add(n)
        else:
            self.replace(prev, n)
        return n

    def detach(self):
        return self.__class__()

    def fun(self, f):
        sub = self.detach()
        spec = getargspec(f)[0]
        args = sub.vars(*spec)
        if spec and spec[0] == 'p':
            args[0] = sub

        ret = f(*args)
        if isinstance(ret, node):
            ret.returns(ret)

        return lambda: sub

    def _format_attrs(self, attrs):
        return reprkwargs(attrs, sep='\n', fmt="{!s} = {!r}")

    def type(self, name, bases=None, attrs=None, methods=None):
        bases = bases or (self.var("object"), )
        if not attrs or not methods:
            methods = ['pass']
        return ("class {!s}({!s}):\n".format(name, reprargs(bases))
              + textindent(self._format_attrs(attrs))
              + "\n\n" + textindent('\n\n'.join(methods or [])))

    def format(self, *args, **kwargs):
        return unicode(self).format(*args, **kwargs)


class symbol(node):
    """A symbol is a node that doesn't have any contant,
    but it does have a name that is used in the context of other nodes."""

    def __init__(self, name, root=None):
        self.name = name
        self.leaf = node
        super(symbol, self).__init__('', root=root)

    def __repr__(self):
        return self.name

    def __unicode__(self):
        return ''

    @property
    def value(self):
        return self.name

    @value.setter            # noqa
    def value(self, value):
        self.name = value


class literal(symbol):

    def __repr__(self):
        return repr(self.name)

    @property
    def value(self):
        return repr(self)


class _py(object):

    def __call__(self, obj=None):
        if obj:
            if callable(obj):
                return root().fun(obj)
        return root()

    def __getattr__(self, name):
        return getattr(root(), name)
py = ly = _py()


def get_value(n):
    if isinstance(n, symbol):
        return n.value
    if isinstance(n, node):
        return unicode(n)
    return n


if __name__ == "__main__":

    @ly
    def play(x, payload, offset, unpack_from):
        x <<= offset[0 + 10:30]
        payload <<= x[x + 10:]
        x.frobulate.the().query.machine(30, a=10)

    x = ly()
    print(x.type('foo', attrs={'x': 30}, methods=[
            play().as_fun(lambda self, payload, offset: 1, 'encode')],
    ))

    @ly
    def b(bool, mandatory, immediate):
        bool(mandatory) | bool(immediate)
