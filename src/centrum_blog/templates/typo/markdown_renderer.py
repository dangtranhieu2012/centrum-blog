import mistune

from flask import url_for
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import html


class MarkdownRenderer(mistune.HTMLRenderer):
    _article_id: str


    def __init__(self, article_id: str = "", escape: bool = True):
        super().__init__(escape=escape)
        self._article_id = article_id


    def heading(self, text, level, **attrs):
        return f'<h{level} class="mt-5">{text}</h{level}>'


    def block_code(self, code, info=None):
        lang = info.strip() if info else "text"

        try:
            lexer = get_lexer_by_name(lang, stripall=True)
        except:
            lexer = TextLexer()

        formatter = html.HtmlFormatter()
        return highlight(code, lexer, formatter)


    def image(self, text, url, title=None):
        if self._article_id == "":
            src = url_for("static", filename=f"content/images/{url}")
        else:
            src = url_for("static", filename=f"content/posts/{self._article_id}/{url}")

        s = f'<figure><img src="{src}" alt="{text}"'
        if title:
            s += f' title="{title}"'
        return s + f' /><figcaption>{text}</figcaption></figure>'
