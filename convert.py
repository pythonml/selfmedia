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
    def convert_anchor(html):
        patt = re.compile(r'<a href="([^"]+)"[^>]*>(.*?)</a>')
        matched = patt.search(html)
        if matched:
            url = matched.group(1)
            name = matched.group(2)
            markdown = "[%s](%s)" % (name, url)
            new_html = patt.sub(markdown, html)
            return Block.convert_anchor(new_html)
        return html

    @staticmethod
    def convert_bold(html):
        patt = re.compile(r'<b>(.*?)</b>', re.M|re.S)
        matched = patt.search(html)
        if matched:
            text = matched.group(1)
            markdown = '**%s**' % text
            return markdown
        return html

    @staticmethod
    def parse_figure(element):
        for e in element:
            if e.tag == "img" and e.attrib["class"] == "origin_image zh-lightbox-thumb lazy":
                return e.attrib["data-original"]

    @staticmethod
    def parse_code(element):
        return element.text_content()

    @staticmethod
    def parse_paragraph(element):
        raw_html = etree.tostring(element).decode("utf-8")
        md_html = Block.convert_anchor(raw_html)
        md_html = Block.escape_underscore(md_html)
        node = html.fromstring(md_html)
        return node.text_content()

    def parse_ol(element):
        result = []
        for child in element:
            result.append(child.text)
        return result

    def parse_ul(element):
        result = []
        for child in element:
            result.append(child.text)
        return result

    def parse_blockquote(element):
        raw_html = etree.tostring(element).decode("utf-8")
        md_html = Block.convert_bold(raw_html)
        node = html.fromstring(md_html)
        return node.text_content()

    @staticmethod
    def parse_head(element):
        return element.text

    def __init__(self, element):
        self.element = element
        # figure
        if element.tag == "figure":
            self.type = "figure"
            self.data = Block.parse_figure(element)
        # code
        elif element.tag == "div" and element.attrib["class"] == "highlight":
            self.type = "code"
            self.data = Block.parse_code(element)
        # head
        elif element.tag == "h2":
            self.type = "head"
            self.data = Block.parse_head(element)
        # html
        elif element.tag == "p":
            self.type = "paragraph"
            self.data = Block.parse_paragraph(element)
        elif element.tag == "ol":
            self.type = "ol"
            self.data = Block.parse_ol(element)
        elif element.tag == "ul":
            self.type = "ul"
            self.data = Block.parse_ul(element)
        elif element.tag == "blockquote":
            self.type = "blockquote"
            self.data = Block.parse_blockquote(element)

    def to_markdown(self):
        if self.type == "paragraph":
            return self.data
        elif self.type == "head":
            html = "#### %s" % self.data
            return html
        elif self.type == "code":
            html = "```python\n%s\n```\n" % self.data
            return html
        elif self.type == "figure":
            html = "![](%s)" % self.data
            return html
        elif self.type == "ol":
            html = ""
            for i in range(len(self.data)):
                html += "%d. %s\n" % (i, self.data[i])
            return html
        elif self.type == "ul":
            html = ""
            for i in range(len(self.data)):
                html += "* %s\n" % (self.data[i])
            return html
        elif self.type == "blockquote":
            html = "> %s\n" % self.data
            return html

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

    def parse_title(self, element):
        data = json.loads(element.attrib["data-zop"])
        self.title = data["title"]
        self.author_name = data["authorName"]
        imgs = element.xpath(".//img[contains(@class, 'TitleImage')]")
        if len(imgs) == 0:
            self.title_image = ""
        else:
            self.title_image = imgs[0].attrib["src"]

    def parse_content(self, element):
        result = []
        for e in element:
            block = Block(e)
            result.append(block)
        self.content = result

    def to_markdown(self):
        blocks = self.content
        content_html = ""
        for block in blocks:
            content_html += block.to_markdown()
            content_html += "\n"
        html = content_html
        return html

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
    title_div = layout_main_div.xpath('.//div[contains(@class, "Post-content")]')[0]
    article.parse_title(title_div)

    article_div = title_div.xpath('.//div[contains(@class, "RichText Post-RichText")]')[0]
    article.parse_content(article_div)

    return article

if len(sys.argv) < 2:
    print("Usage: %s <url>" % sys.argv[0])
    sys.exit(1)


url = sys.argv[1]
#url = "https://zhuanlan.zhihu.com/p/32961280"
article = get_zhihu_content(url)
print(article.to_markdown())

