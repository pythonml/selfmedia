import re
import json
import sys
import requests
from lxml import html, etree
from pygments import highlight
from pygments.lexers import PythonLexer, get_lexer_by_name
from pygments.formatters import HtmlFormatter

class Block(object):
    @staticmethod
    def escape_underscore(text):
        return re.sub(r'_', r'\_', text)

    @staticmethod
    def html2md(element):
        # figure
        if element.tag == "figure":
            imgs = element.xpath('.//img')
            if len(imgs) == 0:
                raise Exception("error getting image")
            img = imgs[0]
            img_url = ""
            if "data-original" in img.attrib:
                img_url = img.attrib["data-original"]
            else:
                img_url = img.attrib["src"]
            md = "![]({})".format(img_url)
            return md

        # code
        if element.tag == "div" and element.attrib["class"] == "highlight":
            code = element.text_content()
            lang_class = element.xpath('./pre/code')[0].attrib["class"]
            matched = re.match("language-(.*)$", lang_class)
            lang = matched.group(1)
            md = '```{}\n{}\n```'.format(lang, code)
            return md
        if element.tag == "code":
            code = element.text
            md = '`{}`'.format(code)
            return md

        # head
        if element.tag == "h2":
            text = Block.escape_underscore(element.text)
            md = "#### {}".format(text)
            return md

        # html
        if element.tag == "p":
            md = "" if element.text is None else Block.escape_underscore(element.text)
            for node in element:
                node_md = Block.html2md(node)
                md += node_md
                node_tail = "" if node.tail is None else Block.escape_underscore(node.tail)
                md += node_tail
            return md

        if element.tag == "ol":
            md = ""
            i = 1
            for node in element:
                node_md = Block.html2md(node)
                md += "{}. {}\n".format(i, node_md)
                i += 1
            return md

        if element.tag == "ul":
            md = ""
            for node in element:
                node_md = Block.html2md(node)
                md += "{}\n".format(node_md)
            return md

        if element.tag == "li":
            md = "+ {}".format(element.text)
            return md

        if element.tag == "hr":
            md = "---\n"
            return md

        if element.tag == "b":
            md = "" if element.text is None else Block.escape_underscore(element.text)
            for node in element:
                node_md = Block.html2md(node)
                md += node_md
                node_tail = "" if node.tail is None else Block.escape_underscore(node.tail)
                md += node_tail
            md = "**{}**".format(md)
            return md

        if element.tag == "i":
            md = "" if element.text is None else Block.escape_underscore(element.text)
            for node in element:
                node_md = Block.html2md(node)
                md += node_md
                node_tail = "" if node.tail is None else Block.escape_underscore(node.tail)
                md += node_tail
            md = "*{}*".format(md)
            return md

        if element.tag == "a":
            url = element.attrib["href"]
            name_md = ""
            if len(element) > 0:
                name_md = Block.html2md(element[0])
            else:
                name_md = Block.escape_underscore(element.text)
            md = "[{}]({})".format(name_md, url)
            return md

        if element.tag == "br":
            md = "\n"
            return md

        if element.tag == "blockquote":
            md = "" if element.text is None else Block.escape_underscore(element.text)
            for node in element:
                node_md = Block.html2md(node)
                md += node_md
                node_tail = "" if node.tail is None else Block.escape_underscore(node.tail)
                md += node_tail
            md = "> {}".format(md)
            return md

        raise Exception("unrecognized tag {}".format(element.tag))

    def __repr__(self):
        return '<Block type="%s" data="%s">' % (self.type, self.data)

class Article(object):
    def __init__(self, title="",
        title_image="",
        author_name="",
        content=""):
        self.title = title
        self.title_image = title_image
        self.author_name = author_name
        self.content = content
        self.markdown = ""

    def parse_title(self, element):
        data = json.loads(element.attrib["data-zop"])
        self.title = data["title"]
        self.author_name = data["authorName"]
        imgs = element.xpath(".//img[contains(@class, 'TitleImage')]")
        if len(imgs) == 0:
            self.title_image = ""
        else:
            self.title_image = imgs[0].attrib["src"]

    def to_markdown(self, element):
        result = ""
        for e in element:
            md = Block.html2md(e)
            result = result + md + "\n\n"
        self.markdown = result

    def __repr__(self):
        name = "<Article [title=\"%s\", title_image=\"%s\", author_name=\"%s\"]>" % (self.title.encode("utf-8"),
            self.title_image,
            self.author_name.encode("utf-8"),
        )
        return name

def get_zhihu_content(url):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.86 Safari/537.36"}
    r = requests.get(url, headers=headers)
    content = r.content.decode("utf-8")
    tree = html.fromstring(content)
    layout_main_divs = tree.xpath("//main[contains(@class, 'App-main')]")
    if len(layout_main_divs) < 1:
        raise Exception("error finding content")
    layout_main_div = layout_main_divs[0]

    article = Article()
    content_div = layout_main_div.xpath('.//div[contains(@class, "Post-content")]')[0]
    article.parse_title(content_div)

    article_div = content_div.xpath('.//div[contains(@class, "Post-RichText")]')[0]
    article.to_markdown(article_div)

    return article

if len(sys.argv) < 2:
    print("Usage: %s <url>" % sys.argv[0])
    sys.exit(1)


url = sys.argv[1]
#url = "https://zhuanlan.zhihu.com/p/41694635"
article = get_zhihu_content(url)
print(article.markdown)

