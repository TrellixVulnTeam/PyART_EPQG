__version__ = "3.200.3"
__author__ = "Aaron Swartz (me@aaronsw.com)"
__copyright__ = "(C) 2004-2008 Aaron Swartz. GNU GPL 3."
__contributors__ = ["Martin 'Joey' Schulze", "Ricardo Reyes", "Kevin Jay North"]


try:
    True
except NameError:
    setattr(__builtins__, 'True', 1)
    setattr(__builtins__, 'False', 0)

def has_key(x, y):
    if hasattr(x, 'has_key'): return x.has_key(y)
    else: return y in x

try:
    import htmlentitydefs
    import urlparse
    import HTMLParser
except ImportError: #Python3
    import html.entities as htmlentitydefs
    import urllib.parse as urlparse
    import html.parser as HTMLParser
try: #Python3
    import urllib.request as urllib
except:
    import urllib
import optparse, re, sys, codecs, types

try: from textwrap import wrap
except: pass

UNICODE_SNOB = 0

ESCAPE_SNOB = 0

LINKS_EACH_PARAGRAPH = 0

BODY_WIDTH = 78

SKIP_INTERNAL_LINKS = True

INLINE_LINKS = True

GOOGLE_LIST_INDENT = 36

IGNORE_ANCHORS = False
IGNORE_IMAGES = False
IGNORE_EMPHASIS = False


def name2cp(k):
    if k == 'apos': return ord("'")
    if hasattr(htmlentitydefs, "name2codepoint"): # requires Python 2.3
        return htmlentitydefs.name2codepoint[k]
    else:
        k = htmlentitydefs.entitydefs[k]
        return ord(codecs.latin_1_decode(k)[0])

unifiable = {'rsquo':"'", 'lsquo':"'", 'rdquo':'"', 'ldquo':'"',
'copy':'(C)', 'mdash':'--', 'nbsp':' ', 'rarr':'->', 'larr':'<-', 'middot':'*',
'ndash':'-', 'oelig':'oe', 'aelig':'ae',
'agrave':'a', 'aacute':'a', 'acirc':'a', 'atilde':'a', 'auml':'a', 'aring':'a',
'egrave':'e', 'eacute':'e', 'ecirc':'e', 'euml':'e',
'igrave':'i', 'iacute':'i', 'icirc':'i', 'iuml':'i',
'ograve':'o', 'oacute':'o', 'ocirc':'o', 'otilde':'o', 'ouml':'o',
'ugrave':'u', 'uacute':'u', 'ucirc':'u', 'uuml':'u',
'lrm':'', 'rlm':''}

unifiable_n = {}

    unifiable_n[name2cp(k)] = unifiable[k]


def onlywhite(line):
    for c in line:
        if c is not ' ' and c is not '  ':
            return c is ' '
    return line

def hn(tag):
    if tag[0] == 'h' and len(tag) == 2:
        try:
            n = int(tag[1])
            if n in range(1, 10): return n
        except ValueError: return 0

def dumb_property_dict(style):
    return dict([(x.strip(), y.strip()) for x, y in [z.split(':', 1) for z in style.split(';') if ':' in z]]);

def dumb_css_parser(data):
    data += ';'
    while importIndex != -1:
        data = data[0:importIndex] + data[data.find(';', importIndex) + 1:]
        importIndex = data.find('@import')

    elements =  [x.split('{') for x in data.split('}') if '{' in x.strip()]
    try:
        elements = dict([(a.strip(), dumb_property_dict(b)) for a, b in elements])
    except ValueError:
        elements = {} # not that important

    return elements

def element_style(attrs, style_def, parent_style):
    if 'class' in attrs:
        for css_class in attrs['class'].split():
            css_style = style_def['.' + css_class]
    if 'style' in attrs:
        immediate_style = dumb_property_dict(attrs['style'])
        style.update(immediate_style)
    return style

def google_list_style(style):
    if 'list-style-type' in style:
        list_style = style['list-style-type']
        if list_style in ['disc', 'circle', 'square', 'none']:
            return 'ul'
    return 'ol'

def google_has_height(style):
    if 'height' in style:
        return True
    return False

def google_text_emphasis(style):
    emphasis = []
    if 'text-decoration' in style:
    if 'font-style' in style:
        emphasis.append(style['font-style'])
    if 'font-weight' in style:
        emphasis.append(style['font-weight'])
    return emphasis

def google_fixed_width_font(style):
    font_family = ''
    if 'font-family' in style:
        font_family = style['font-family']
    if 'Courier New' == font_family or 'Consolas' == font_family:
        return True
    return False

def list_numbering_start(attrs):
    if 'start' in attrs:
        return int(attrs['start']) - 1
    else:
        return 0

class HTML2Text(HTMLParser.HTMLParser):
    def __init__(self, out=None, baseurl=''):
        try:
            HTMLParser.HTMLParser.__init__(self, convert_charrefs=False)
        except TypeError:
            HTMLParser.HTMLParser.__init__(self)

        self.unicode_snob = UNICODE_SNOB
        self.escape_snob = ESCAPE_SNOB
        self.links_each_paragraph = LINKS_EACH_PARAGRAPH
        self.body_width = BODY_WIDTH
        self.skip_internal_links = SKIP_INTERNAL_LINKS
        self.inline_links = INLINE_LINKS
        self.google_list_indent = GOOGLE_LIST_INDENT
        self.ignore_links = IGNORE_ANCHORS
        self.ignore_images = IGNORE_IMAGES
        self.ignore_emphasis = IGNORE_EMPHASIS
        self.google_doc = False
        self.ul_item_mark = '*'
        self.emphasis_mark = '_'
        self.strong_mark = '**'

        if out is None:
            self.out = self.outtextf
        else:
            self.out = out

        self.outtextlist = []  # empty list to store output characters before they are "joined"

        try:
            self.outtext = unicode()
        except NameError:  # Python3
            self.outtext = str()

        self.quiet = 0
        self.p_p = 0  # number of newline character to print before next output
        self.outcount = 0
        self.start = 1
        self.space = 0
        self.a = []
        self.astack = []
        self.maybe_automatic_link = None
        self.acount = 0
        self.list = []
        self.blockquote = 0
        self.pre = 0
        self.startpre = 0
        self.code = False
        self.br_toggle = ''
        self.lastWasNL = 0
        self.lastWasList = False
        self.style = 0
        self.style_def = {}
        self.tag_stack = []
        self.emphasis = 0
        self.drop_white_space = 0
        self.inheader = False
        self.abbr_title = None  # current abbreviation definition
        self.abbr_data = None  # last inner HTML (for abbr being defined)
        self.abbr_list = {}  # stack of abbreviations to write later
        self.baseurl = baseurl

        try: del unifiable_n[name2cp('nbsp')]
        except KeyError: pass
        unifiable['nbsp'] = '&nbsp_place_holder;'


    def feed(self, data):
        HTMLParser.HTMLParser.feed(self, data)

    def handle(self, data):
        self.feed("")
        return self.optwrap(self.close())

    def outtextf(self, s):
        if s: self.lastWasNL = s[-1] == '\n'

    def close(self):

        self.pbr()
        self.o('', 0, 'end')

        if self.unicode_snob:
            nbsp = unichr(name2cp('nbsp'))
        else:
            nbsp = u' '

        return self.outtext

    def handle_charref(self, c):
        self.o(self.charref(c), 1)

    def handle_entityref(self, c):
        self.o(self.entityref(c), 1)

    def handle_starttag(self, tag, attrs):
        self.handle_tag(tag, attrs, 1)

    def handle_endtag(self, tag):
        self.handle_tag(tag, None, 0)

    def previousIndex(self, attrs):
        if not has_key(attrs, 'href'): return None

        i = -1
        for a in self.a:
            i += 1
            match = 0

            if has_key(a, 'href') and a['href'] == attrs['href']:
                if has_key(a, 'title') or has_key(attrs, 'title'):
                        if (has_key(a, 'title') and has_key(attrs, 'title') and
                            a['title'] == attrs['title']):
                            match = True
                else:
                    match = True

            if match: return i

    def drop_last(self, nLetters):
        if not self.quiet:
            self.outtext = self.outtext[:-nLetters]

    def handle_emphasis(self, start, tag_style, parent_style):
        tag_emphasis = google_text_emphasis(tag_style)
        parent_emphasis = google_text_emphasis(parent_style)

        strikethrough =  'line-through' in tag_emphasis and self.hide_strikethrough
        bold = 'bold' in tag_emphasis and not 'bold' in parent_emphasis
        italic = 'italic' in tag_emphasis and not 'italic' in parent_emphasis
        fixed = google_fixed_width_font(tag_style) and not \
                google_fixed_width_font(parent_style) and not self.pre

        if start:
            if bold or italic or fixed:
                self.emphasis += 1
            if strikethrough:
                self.quiet += 1
            if italic:
                self.o(self.emphasis_mark)
                self.drop_white_space += 1
            if bold:
                self.o(self.strong_mark)
                self.drop_white_space += 1
            if fixed:
                self.o('`')
                self.drop_white_space += 1
                self.code = True
        else:
            if bold or italic or fixed:
                self.emphasis -= 1
                self.space = 0
            if fixed:
                if self.drop_white_space:
                    self.drop_last(1)
                    self.drop_white_space -= 1
                else:
                    self.o('`')
                self.code = False
            if bold:
                if self.drop_white_space:
                    self.drop_last(2)
                    self.drop_white_space -= 1
                else:
                    self.o(self.strong_mark)
            if italic:
                if self.drop_white_space:
                    self.drop_last(1)
                    self.drop_white_space -= 1
                else:
                    self.o(self.emphasis_mark)
            if (bold or italic) and not self.emphasis:
                    self.o(" ")
            if strikethrough:
                self.quiet -= 1

    def handle_tag(self, tag, attrs, start):
        if attrs is None:
            attrs = {}
        else:
            attrs = dict(attrs)

        if self.google_doc:
            parent_style = {}
            if start:
                if self.tag_stack:
                  parent_style = self.tag_stack[-1][2]
                tag_style = element_style(attrs, self.style_def, parent_style)
            else:
                if self.tag_stack:
                    parent_style = self.tag_stack[-1][2]

        if hn(tag):
            self.p()
            if start:
                self.inheader = True
                self.o(hn(tag)*"#" + ' ')
            else:
                self.inheader = False
                return # prevent redundant emphasis marks on headers

        if tag in ['p', 'div']:
            if self.google_doc:
                if start and google_has_height(tag_style):
                    self.p()
                else:
                    self.soft_br()
            else:
                self.p()

        if tag == "br" and start: self.o("  \n")

        if tag == "hr" and start:
            self.p()
            self.o("* * *")
            self.p()

        if tag in ["head", "style", 'script']:
            if start: self.quiet += 1
            else: self.quiet -= 1

        if tag == "style":
            if start: self.style += 1
            else: self.style -= 1

        if tag in ["body"]:
            self.quiet = 0 # sites like 9rules.com never close <head>

        if tag == "blockquote":
            if start:
                self.p(); self.o('> ', 0, 1); self.start = 1
                self.blockquote += 1
            else:
                self.blockquote -= 1
                self.p()

        if tag in ['em', 'i', 'u'] and not self.ignore_emphasis: self.o(self.emphasis_mark)
        if tag in ['strong', 'b'] and not self.ignore_emphasis: self.o(self.strong_mark)
        if tag in ['del', 'strike', 's']:
            if start:
                self.o("<"+tag+">")
            else:
                self.o("</"+tag+">")

        if self.google_doc:
            if not self.inheader:
                self.handle_emphasis(start, tag_style, parent_style)

        if tag in ["code", "tt"] and not self.pre: self.o('`') #TODO: `` `this` ``
        if tag == "abbr":
            if start:
                self.abbr_title = None
                self.abbr_data = ''
                if has_key(attrs, 'title'):
                    self.abbr_title = attrs['title']
            else:
                if self.abbr_title != None:
                    self.abbr_list[self.abbr_data] = self.abbr_title
                    self.abbr_title = None
                self.abbr_data = ''

        if tag == "a" and not self.ignore_links:
            if start:
                if has_key(attrs, 'href') and not (self.skip_internal_links and attrs['href'].startswith('#')):
                    self.maybe_automatic_link = attrs['href']
                else:
                    self.astack.append(None)
            else:
                if self.astack:
                    if self.maybe_automatic_link:
                        self.maybe_automatic_link = None
                    elif a:
                        if self.inline_links:
                            self.o("](" + escape_md(a['href']) + ")")
                        else:
                            i = self.previousIndex(a)
                            if i is not None:
                                a = self.a[i]
                            else:
                                self.acount += 1
                                a['count'] = self.acount
                                a['outcount'] = self.outcount
                            self.o("][" + str(a['count']) + "]")

        if tag == "img" and start and not self.ignore_images:
            if has_key(attrs, 'src'):
                attrs['href'] = attrs['src']
                alt = attrs.get('alt', '')
                self.o("![" + escape_md(alt) + "]")

                if self.inline_links:
                    self.o("(" + escape_md(attrs['href']) + ")")
                else:
                    i = self.previousIndex(attrs)
                    if i is not None:
                        attrs = self.a[i]
                    else:
                        self.acount += 1
                        attrs['count'] = self.acount
                        attrs['outcount'] = self.outcount
                        self.a.append(attrs)
                    self.o("[" + str(attrs['count']) + "]")

        if tag == 'dl' and start: self.p()
        if tag == 'dt' and not start: self.pbr()
        if tag == 'dd' and start: self.o('    ')
        if tag == 'dd' and not start: self.pbr()

        if tag in ["ol", "ul"]:
            if (not self.list) and (not self.lastWasList):
                self.p()
            if start:
                if self.google_doc:
                    list_style = google_list_style(tag_style)
                else:
                    list_style = tag
                numbering_start = list_numbering_start(attrs)
            else:
            self.lastWasList = True
        else:
            self.lastWasList = False

        if tag == 'li':
            self.pbr()
            if start:
                if self.list: li = self.list[-1]
                else: li = {'name':'ul', 'num':0}
                if self.google_doc:
                    nest_count = self.google_nest_count(tag_style)
                else:
                    nest_count = len(self.list)
                self.o("  " * nest_count) #TODO: line up <ol><li>s > 9 correctly.
                if li['name'] == "ul": self.o(self.ul_item_mark + " ")
                elif li['name'] == "ol":
                    li['num'] += 1
                    self.o(str(li['num'])+". ")
                self.start = 1

        if tag in ["table", "tr"] and start: self.p()
        if tag == 'td': self.pbr()

        if tag == "pre":
            if start:
                self.startpre = 1
                self.pre = 1
            else:
                self.pre = 0
            self.p()

    def pbr(self):
        if self.p_p == 0:
            self.p_p = 1

    def p(self):
        self.p_p = 2

    def soft_br(self):
        self.pbr()
        self.br_toggle = '  '

    def o(self, data, puredata=0, force=0):
        if self.abbr_data is not None:
            self.abbr_data += data

        if not self.quiet:
            if self.google_doc:
                if self.drop_white_space and not (self.pre or self.code):
                    data = lstripped_data
                if lstripped_data != '':
                    self.drop_white_space = 0

            if puredata and not self.pre:
                if data and data[0] == ' ':
                    self.space = 1
                    data = data[1:]
            if not data and not force: return

            if self.startpre:
                    data = "\n" + data

            bq = (">" * self.blockquote)
            if not (force and data and data[0] == ">") and self.blockquote: bq += " "

            if self.pre:
                if not self.list:
                    bq += "    "
                for i in range(len(self.list)):
                    bq += "    "
                data = data.replace("\n", "\n"+bq)

            if self.startpre:
                self.startpre = 0
                if self.list:
                    data = data.lstrip("\n") # use existing initial indentation

            if self.start:
                self.space = 0
                self.p_p = 0
                self.start = 0

            if force == 'end':
                self.p_p = 0
                self.out("\n")
                self.space = 0

            if self.p_p:
                self.out((self.br_toggle+'\n'+bq)*self.p_p)
                self.space = 0
                self.br_toggle = ''

            if self.space:
                if not self.lastWasNL: self.out(' ')
                self.space = 0

            if self.a and ((self.p_p == 2 and self.links_each_paragraph) or force == "end"):
                if force == "end": self.out("\n")

                newa = []
                for link in self.a:
                    if self.outcount > link['outcount']:
                        self.out("   ["+ str(link['count']) +"](" + urlparse.urljoin(self.baseurl, link['href']) + ")")
                        if has_key(link, 'title'): self.out(" ("+link['title']+")")
                        self.out("\n")
                    else:

                if self.a != newa: self.out("\n") # Don't need an extra line when nothing was done.

                self.a = newa

            if self.abbr_list and force == "end":
                    self.out("  *[" + abbr + "]: " + definition + "\n")

            self.p_p = 0
            self.out(data)
            self.outcount += 1

    def handle_data(self, data):
        if r'\/script>' in data: self.quiet -= 1

        if self.style:

        if not self.maybe_automatic_link is None:
            href = self.maybe_automatic_link
            if href == data and self.absolute_url_matcher.match(href):
                self.o("<" + data + ">")
                return
            else:
                self.o("[")
                self.maybe_automatic_link = None

        if not self.code and not self.pre:
            data = escape_md_section(data, snob=self.escape_snob)
        self.o(data, 1)

    def unknown_decl(self, data): pass

    def charref(self, name):
        if name[0] in ['x','X']:
            c = int(name[1:], 16)
        else:
            c = int(name)

            return unifiable_n[c]
        else:
            try:
                return unichr(c)
            except NameError: #Python3
                return chr(c)

    def entityref(self, c):
        if not self.unicode_snob and c in unifiable.keys():
            return unifiable[c]
        else:
            try: name2cp(c)
            except KeyError: return "&" + c + ';'
            else:
                try:
                    return unichr(name2cp(c))
                except NameError: #Python3
                    return chr(name2cp(c))

    def replaceEntities(self, s):
        s = s.group(1)
        if s[0] == "#":

    r_unescape = re.compile(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")
    def unescape(self, s):

    def google_nest_count(self, style):
        nest_count = 0
        if 'margin-left' in style:
            nest_count = int(style['margin-left'][:-2]) / self.google_list_indent
        return nest_count


    def optwrap(self, text):
        if not self.body_width:
            return text

        assert wrap, "Requires Python 2.3."
        result = ''
        newlines = 0
        for para in text.split("\n"):
            if len(para) > 0:
                if not skipwrap(para):
                    result += "\n".join(wrap(para, self.body_width))
                        result += "  \n"
                        newlines = 1
                    else:
                        result += "\n\n"
                        newlines = 2
                else:
                    if not onlywhite(para):
                        result += para + "\n"
                        newlines = 1
            else:
                if newlines < 2:
                    result += "\n"
                    newlines += 1
        return result

ordered_list_matcher = re.compile(r'\d+\.\s')
unordered_list_matcher = re.compile(r'[-\*\+]\s')
md_chars_matcher = re.compile(r"([\\\[\]\(\)])")
md_chars_matcher_all = re.compile(r"([`\*_{}\[\]\(\)#!])")
slash_chars = r'\`*_{}[]()#+-.!'
    flags=re.VERBOSE)

def skipwrap(para):
    if para[0:4] == '    ' or para[0] == '\t':
        return True
    if stripped[0:2] == "--" and len(stripped) > 2 and stripped[2] != "-":
        return False
    if stripped[0:1] == '-' or stripped[0:1] == '*':
        return True
        return True
    return False

def wrapwrite(text):
    try: #Python3
        sys.stdout.buffer.write(text)
    except AttributeError:
        sys.stdout.write(text)

def html2text(html, baseurl=''):
    h = HTML2Text(baseurl=baseurl)
    return h.handle(html)

def unescape(s, unicode_snob=False):
    h = HTML2Text()
    h.unicode_snob = unicode_snob

def escape_md(text):

def escape_md_section(text, snob=False):
    if snob:
    return text


def main():
    baseurl = ''

    p = optparse.OptionParser('%prog [(filename|url) [encoding]]',
                              version='%prog ' + __version__)
    p.add_option("--ignore-emphasis", dest="ignore_emphasis", action="store_true",
        default=IGNORE_EMPHASIS, help="don't include any formatting for emphasis")
    p.add_option("--ignore-links", dest="ignore_links", action="store_true",
        default=IGNORE_ANCHORS, help="don't include any formatting for links")
    p.add_option("--ignore-images", dest="ignore_images", action="store_true",
        default=IGNORE_IMAGES, help="don't include any formatting for images")
    p.add_option("-g", "--google-doc", action="store_true", dest="google_doc",
        default=False, help="convert an html-exported Google Document")
    p.add_option("-d", "--dash-unordered-list", action="store_true", dest="ul_style_dash",
        default=False, help="use a dash rather than a star for unordered list items")
    p.add_option("-e", "--asterisk-emphasis", action="store_true", dest="em_style_asterisk",
        default=False, help="use an asterisk rather than an underscore for emphasized text")
    p.add_option("-b", "--body-width", dest="body_width", action="store", type="int",
        default=BODY_WIDTH, help="number of characters per output line, 0 for no wrap")
    p.add_option("-i", "--google-list-indent", dest="list_indent", action="store", type="int",
        default=GOOGLE_LIST_INDENT, help="number of pixels Google indents nested lists")
    p.add_option("-s", "--hide-strikethrough", action="store_true", dest="hide_strikethrough",
        default=False, help="hide strike-through text. only relevant when -g is specified as well")
    p.add_option("--escape-all", action="store_true", dest="escape_snob",
        default=False, help="Escape all special characters.  Output is less readable, but avoids corner case formatting issues.")
    (options, args) = p.parse_args()

    encoding = "utf-8"
    if len(args) > 0:
        file_ = args[0]
        if len(args) == 2:
            encoding = args[1]
        if len(args) > 2:

            baseurl = file_
            j = urllib.urlopen(baseurl)
            if encoding is None:
                try:
                    from feedparser import _getCharacterEncoding as enc
                except ImportError:
                    enc = lambda x, y: ('utf-8', 1)
                encoding = enc(j.headers, data)[0]
                if encoding == 'us-ascii':
                    encoding = 'utf-8'
        else:
            data = open(file_, 'rb').read()
            if encoding is None:
                try:
                    from chardet import detect
                except ImportError:
                    detect = lambda x: {'encoding': 'utf-8'}
                encoding = detect(data)['encoding']
    else:
        data = sys.stdin.read()}
    reveal_type(data)