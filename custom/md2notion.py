import itertools
import re
from md2notion.NotionPyRenderer import NotionPyRenderer
from mistletoe import span_token, core_tokens
from notion.block import field_map, BasicBlock
from mistletoe.block_token import BlockToken, Document, tokenize
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.span_token import RawText
from mistletoe.core_tokens import Delimiter, find_link_image, whitespace, unicode_whitespace, punctuation, code_pattern, _code_matches

def find_core_tokens(string, root):
    delimiters = []
    matches = []
    escaped = False
    in_delimiter_run = None
    in_image = False
    start = 0
    i = 0
    code_match = code_pattern.search(string)
    while i < len(string):
        if code_match is not None and i == code_match.start():
            _code_matches.append(code_match)
            i = code_match.end()
            code_match = code_pattern.search(string, i)
            continue
        c = string[i]
        if c == '\\' and not escaped:
            escaped = True
            i += 1
            continue
        if in_delimiter_run is not None and (c != in_delimiter_run or escaped):
            delimiters.append(Delimiter(start, i if not escaped else i-1, string))
            in_delimiter_run = None
        if in_delimiter_run is None and (c == '*' or c == '_') and not escaped:
            in_delimiter_run = c
            start = i
        if not escaped:
            if c == '[':
                if not in_image:
                    delimiters.append(Delimiter(i, i+1, string))
                else:
                    delimiters.append(Delimiter(i-1, i+1, string))
                    in_image = False
            elif c == '!':
                in_image = True
            elif c == ']':
                i = find_link_image(string, i, delimiters, matches, root)
                code_match = code_pattern.search(string, i)
            elif in_image:
                in_image = False
        else:
            escaped = False
        i += 1
    if in_delimiter_run:
        delimiters.append(Delimiter(start, i, string))
    return matches

core_tokens.find_core_tokens = find_core_tokens


class CustomEquationBlock(BasicBlock):

    latex = field_map(
        ["properties", "title"],
        python_to_api=lambda x: [[x]],
        api_to_python=lambda x: x[0][0],
    )

    _type = "equation"


class CustomNotionPyRenderer(NotionPyRenderer):
    
    def render_block_equation(self, token):
        def blockFunc(blockStr):
            return {
                'type': CustomEquationBlock,
                'title_plaintext': blockStr.strip() #.replace('\\', '\\\\')
            }
        return self.renderMultipleToStringAndCombine(token.children, blockFunc)
    
    def render_inline_equation(self, token):
        return self.renderMultipleToStringAndCombine(token.children, lambda s: f"$${s}$$")


class Document(BlockToken):
    """
    Document token.
    """
    def __init__(self, lines):
        if isinstance(lines, str):
            lines = lines.splitlines(keepends=True)
        lines = [line if line.endswith('\n') else '{}\n'.format(line) for line in lines]

        # add new line above and below '$$\n'
        new_lines = []
        for (i, line) in enumerate(lines):
            new_line = [None, line, None]
            if i > 0 and i < len(lines) - 2:
                if line == '$$\n' and lines[i-1][0] != '\n':
                    new_line[0] = '\n'
                if line == '$$\n' and lines[i+1][0] != '\n':
                    new_line[2] = '\n'
            new_lines.append(new_line)
        new_lines = list(itertools.chain(*new_lines))
        new_lines = list(filter(lambda x: x is not None, new_lines))
        new_lines = ''.join(new_lines)
        lines = new_lines.splitlines(keepends=True)
        lines = [line if line.endswith('\n') else '{}\n'.format(line) for line in lines]

        self.footnotes = {}
        global _root_node
        _root_node = self
        span_token._root_node = self
        self.children = tokenize(lines)
        span_token._root_node = None
        _root_node = None

def markdown(iterable, renderer=HTMLRenderer):
    """
    Output HTML with default settings.
    Enables inline and block-level HTML tags.
    """
    with renderer() as renderer:
        return renderer.render(Document(iterable))


def convert(mdFile, notionPyRendererCls=NotionPyRenderer):
    """
    Converts a mdFile into an array of NotionBlock descriptors
    @param {file|string} mdFile The file handle to a markdown file, or a markdown string
    @param {NotionPyRenderer} notionPyRendererCls Class inheritting from the renderer
    incase you want to render the Markdown => Notion.so differently
    """
    return markdown(mdFile, notionPyRendererCls)