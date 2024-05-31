"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 5 (Laying out Pages),
without exercises.
"""

import socket
import ssl
import tkinter
import tkinter.font
from chapter1 import request
from chapter2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from chapter3 import FONTS, get_font
from chapter4 import Text, Element, print_tree, HTMLParser

BLOCK_ELEMENTS = [
    "html",
    "body",
    "article",
    "section",
    "nav",
    "aside",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hgroup",
    "header",
    "footer",
    "address",
    "p",
    "hr",
    "pre",
    "blockquote",
    "ol",
    "ul",
    "menu",
    "li",
    "dl",
    "dt",
    "dd",
    "figure",
    "figcaption",
    "main",
    "div",
    "table",
    "form",
    "fieldset",
    "legend",
    "details",
    "summary",
]


def layout_mode(node):
    if isinstance(node, Text):
        return "inline"
    elif node.children:
        if any(
            [
                isinstance(child, Element) and child.tag in BLOCK_ELEMENTS
                for child in node.children
            ]
        ):
            return "block"
        else:
            return "inline"
    else:
        return "block"


class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        mode = layout_mode(self.node)
        if mode == "block":
            previous = None
            for child in self.node.children:
                if isinstance(child, Element) and child.tag == "head":
                    continue
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.display_list = []

            self.cursor_x = 0
            self.cursor_y = 0
            self.weight = "normal"
            self.style = "roman"
            self.size = 16
            self.line_height = 0

            self.line = []
            self.recurse(self.node)
            self.flush()

        for child in self.children:
            child.layout()

        if mode == "block":
            self.height = sum([child.height for child in self.children])
        else:
            self.height = self.cursor_y

    def recurse(self, node):
        if isinstance(node, Text):
            self.text(node)
        else:
            self.open_tag(node.tag)
            for child in node.children:
                self.recurse(child)
            self.close_tag(node.tag)

    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()
        elif tag == "li":
            self.x += 2 * HSTEP
            self.width -= 2 * HSTEP

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
        elif tag == "/li":
            pass

    def text(self, node):
        font = get_font(self.size, self.weight, self.style)
        for word in node.text.split():
            w = font.measure(word)
            if self.cursor_x + w > self.width:
                self.flush()
            self.line.append((self.cursor_x, word, font))
            self.cursor_x += w + font.measure(" ")

    def flush(self):
        if not self.line:
            return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        self.cursor_x = 0
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        if not self.line_height:
            self.line_height = self.cursor_y

    def paint(self, display_list):
        if (
            isinstance(self.node, Element)
            and self.node.tag == "nav"
            and "links" == self.node.attributes.get("class", None)
        ):
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "lightgray")
            display_list.append(rect)

        if isinstance(self.node, Element) and self.node.tag == "pre":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            display_list.append(rect)

        if isinstance(self.node, Element) and self.node.tag == "li":
            x = self.x - HSTEP - 2
            y = self.y + self.line_height / 2 - 2
            x2 = x + 4
            y2 = y + 4
            rect = DrawRect(x, y, x2, y2, "black")
            display_list.append(rect)

        if layout_mode(self.node) == "inline":
            for x, y, word, font in self.display_list:
                display_list.append(DrawText(x, y, word, font))

        for child in self.children:
            child.paint(display_list)

    def __repr__(self):
        mode = layout_mode(self.node)
        # Capitalize the first letter of the mode.
        mode = mode[0].upper() + mode[1:]
        return f"{mode}Layout(x={self.x}, y={self.y}, width={self.width}, height={self.height})"


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.previous = None
        self.children = []

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2 * HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height + 2 * VSTEP

    def paint(self, display_list):
        self.children[0].paint(display_list)

    def __repr__(self):
        return "DocumentLayout()"


class DrawText:
    def __init__(self, x1, y1, text, font):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font

        self.bottom = y1 + font.metrics("linespace")

    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left,
            self.top - scroll,
            text=self.text,
            font=self.font,
            anchor="nw",
        )

    def __repr__(self):
        return "DrawText(top={} left={} bottom={} text={} font={})".format(
            self.top, self.left, self.bottom, self.text, self.font
        )


class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left,
            self.top - scroll,
            self.right,
            self.bottom - scroll,
            width=0,
            fill=self.color,
        )

    def __repr__(self):
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            self.top, self.left, self.bottom, self.right, self.color
        )


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()

        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.display_list = []

    def load(self, url):
        headers, body = request(url)
        self.nodes = HTMLParser(body).parse()
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll, self.canvas)

        if self.document.height > HEIGHT:
            self.draw_scrollbar()

    def draw_scrollbar(self):
        sb_left = WIDTH - 8
        sb_right = WIDTH

        sb_height = HEIGHT * HEIGHT // self.document.height
        sb_top = HEIGHT * self.scroll // self.document.height
        sb_bot = sb_top + sb_height

        scrollbar = DrawRect(sb_left, sb_top, sb_right, sb_bot, "blue")
        scrollbar.execute(0, self.canvas)

    def scrolldown(self, e):
        max_y = self.document.height - HEIGHT
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.draw()


if __name__ == "__main__":
    import sys

    Browser().load(sys.argv[1])
    tkinter.mainloop()
