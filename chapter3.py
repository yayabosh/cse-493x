import sys  # For parsing command-line arguments
import tkinter  # For the GUI
import tkinter.font as tkfont

from typing import *
from chapter1 import request
from chapter2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP


# A class to represent a string of text
class Text:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return "Text('{}')".format(self.text)


# A class to represent an HTML tag
class Tag:
    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "Tag('{}')".format(self.tag)


Token = Union[Text, Tag]


# Remove HTML tags from a string. Return the resulting string.
def lex(body: str) -> list[Token]:
    # The list of tokens to return
    out = []
    # Represents the text between HTML tags
    text = ""
    # Represents if we are currently inside an HTML tag
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if text:
                # Replace HTML entities with their corresponding characters
                text = (
                    text.replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("&amp;", "&")
                    .replace("&quot;", '"')
                )

                out.append(Text(text))
                text = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(text))
            text = ""
        else:
            text += c

    if not in_tag and text:
        out.append(Text(text))

    return out


# We’ll need our own cache, so that we can reuse Font objects and have our text
# measurements cached. We’ll store our cache in a global FONTS dictionary.
FONTS = {}


# Return a tkinter font object for the given size, weight, and slant
def get_font(size: int, weight: str, slant: str, family: str) -> tkfont.Font:
    # The keys to this dictionary will be size/weight/style triples, and the
    # values will be Font objects.
    key = (size, weight, slant, family)
    if key not in FONTS:
        font = tkfont.Font(size=size, weight=weight, slant=slant, family=family)
        FONTS[key] = font
    return FONTS[key]


# A class to represent a word on a line of text
class LineItem:
    def __init__(
        self, cursor_x: float, text: str, font: tkfont.Font, superscript: bool
    ):
        # The x-coordinate of the cursor when the line was created
        self.cursor_x = cursor_x
        # The text of the line
        self.text = text
        # The font of the line
        self.font = font
        # Superscript
        self.superscript = superscript


# A class to represent a formatted block of text. Each Layout has a list of
# tokens, and a list of (x, y, text, font) tuples to display. For example,
# if the tokens are [Text('Hello'), Tag('b'), Text('world'), Tag('/b')], then
# the display list might be [(0, 0, 'Hello', Font(...)), (0, 16, 'world',
# Font(...))], representing the words "Hello" and "world" on the first and
# second lines, respectively, with the word "world" in bold.
class Layout:
    def __init__(self, tokens: list[Token]):
        # The list of tokens to format
        self.tokens = tokens
        # The list of (x, y, text, font) tuples to display
        self.display_list = []

        # Fixed width for how many x- and y-pixels we should move between
        # characters and lines, respectively
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP

        # The current font weight, style, and size
        self.weight = "normal"
        self.style = "roman"
        self.size = 16

        # Centered text
        self.centered = False

        # Small caps
        self.abbr = False

        # Superscripts
        self.superscript = False

        # Preformatted text
        self.pre = False

        # The current line of text
        self.line = []
        for tok in tokens:
            self.token(tok)

        self.flush()

    def token(self, tok: Token) -> None:
        if isinstance(tok, Text):
            self.text(tok)
            return

        # Otherwise, it's a tag (but still check)
        assert isinstance(tok, Tag)
        if tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        # <br> tag ends the current line and starts a new one (self-closing tag)
        elif tok.tag == "br":
            self.flush()
        # Paragraphs are defined by the <p> and </p> tags, so </p> also ends
        # the current line.
        elif tok.tag == "/p":
            self.flush()
            # I add a bit extra to cursor_y here to create a little gap between
            # paragraphs.
            self.cursor_y += VSTEP
        # The <h1> tag starts a new line, but it also centers the text.
        elif tok.tag.startswith("h1"):
            self.flush()
            # self.cursor_y += VSTEP
            self.centered = True
        # The </h1> tag ends the current line and turns off centering.
        elif tok.tag.startswith("/h1"):
            self.flush()
            self.centered = False
        elif tok.tag == "sup":
            self.superscript = True
        elif tok.tag == "/sup":
            self.superscript = False
        elif tok.tag == "abbr":
            self.abbr = True
        elif tok.tag == "/abbr":
            self.abbr = False
        elif tok.tag == "pre":
            self.pre = True
        elif tok.tag == "/pre":
            self.pre = False

    # Add a string of text to the current line. This method is similar to the
    # text method, but it doesn't need to worry about HTML tags. It just needs
    # to add the text to the current line and move the cursor to the right.
    # The append_space parameter indicates whether a space should be appended
    # after the text. This is useful for abbreviations, where we don't want a
    # space after the last word.
    def append_line_item(
        self,
        cursor_x: float,
        text: str,
        font: tkfont.Font,
        superscript: bool = False,
        append_space: bool = True,
    ) -> None:
        width = font.measure(text)
        if self.cursor_x + width > WIDTH - HSTEP:
            self.flush()

        # Add the word to the line item list and move the cursor to the right
        self.line.append(
            LineItem(cursor_x=cursor_x, text=text, font=font, superscript=superscript)
        )

        # Move the cursor to the right by the width of the word
        self.cursor_x += width
        # Add a space to the end of the word
        if append_space:
            self.cursor_x += font.measure(" ")

    # Return a font object for the current font weight, style, and size.
    # For example, if the current font weight is bold, style is italic, and size
    # is 16, then this method will return a Font object with those attributes.
    # We need this method to be a method of the Layout class because we need to
    # access the current font weight, style, and size, which are stored as
    # instance variables. We then call the general get_font function, passing in
    # the current size, weight, and style.
    def get_font(
        self,
        size: int = None,
        scale: float = None,
        bold: bool = False,
        italic: bool = False,
    ) -> tkfont.Font:
        # If the size is None, use the current size
        font_size = size if size else self.size
        # If scale is not None, scale the font size by that amount. For example,
        # for superscripts, we want the font size to be half the normal size,
        # so we pass scale=0.5.
        if scale:
            font_size = int(font_size * scale)

        return get_font(
            font_size,
            "bold" if bold else self.weight,
            "italic" if italic else self.style,
        )

    def process_abbr(self, font: tkfont.Font, word: str) -> str:
        line_abbr = ""
        # Whether the previous "chunk" of characters was lowercase
        is_lowercase = word[0].islower()
        for c in word:
            # Case 1: The current character is not lowercase but the previous
            # chunk of characters was lowercase. This means we need to draw the
            # previous chunk of characters in small caps and clear the chunk.
            if not c.islower() and is_lowercase:
                self.append_line_item(
                    cursor_x=self.cursor_x,
                    text=line_abbr.upper(),  # caps
                    font=self.get_font(scale=0.5, bold=True),  # small caps
                    superscript=self.superscript,
                    append_space=False,
                )

                line_abbr = ""
                is_lowercase = not is_lowercase

            # Case 2: The current character is lowercase but the previous chunk
            # of characters was not lowercase. This means we need to draw the
            # previous chunk of characters in the normal font and clear the
            # chunk.
            elif c.islower() and not is_lowercase:
                self.append_line_item(
                    cursor_x=self.cursor_x,
                    text=line_abbr,
                    font=font,  # normal font
                    superscript=self.superscript,
                    append_space=False,
                )

                line_abbr = ""
                is_lowercase = not is_lowercase

            # All cases: Add the current character to the chunk, since the
            # chunk is either still all lowercase/uppercase or now empty.
            line_abbr += c

        # If there are any characters left over in the chunk, draw them in the
        # appropriate font.
        if line_abbr:
            # Case 1: The last chunk of characters was lowercase.
            # Draw them in small caps.
            if is_lowercase:
                self.append_line_item(
                    cursor_x=self.cursor_x,
                    text=line_abbr.upper(),  # caps
                    font=self.get_font(scale=0.5, bold=True),  # small caps
                    superscript=self.superscript,
                    append_space=False,
                )
            # Case 2: The last chunk of characters was not lowercase.
            # Draw them in the normal font.
            else:
                self.append_line_item(
                    cursor_x=self.cursor_x,
                    text=line_abbr,
                    font=font,  # normal font
                    superscript=self.superscript,
                    append_space=False,
                )

        # Add a space to the end of the word.
        self.cursor_x += font.measure(" ")

    # Add a string of text to the current line
    def text(self, tok: Token) -> None:
        font = None
        if self.pre:
            # Use Courier New as the font for preformatted text
            font = tkinter.font.Font(family="Courier New", size=self.size)
        elif self.superscript:
            font = self.get_font(scale=0.5)
        else:
            font = self.get_font()

        # Split the string into words
        for word in tok.text.split():
            if self.pre:
                # If the text is preformatted, then we don't need to worry
                # about splitting the text into words. We can just add the
                # entire string to the line.
                self.append_line_item(
                    cursor_x=self.cursor_x,
                    text=word,
                    font=font,
                    superscript=self.superscript,
                )
                continue

            # Make the <abbr> element render text in small caps.
            # Inside an <abbr> tag, lower-case letters should be small,
            # capitalized, and bold, while all other characters (upper case,
            # numbers, etc) should be drawn in the normal font.
            if self.abbr:
                self.process_abbr(font, word)
                continue

            # Split the word on soft hyphens. This is useful for words that are
            # too long to fit on a single line. For example, if the word is
            # "supercalifragilisticexpialidocious", then we want to split it
            # into "su", "per", "cal", "ifrag", etc. This way, we can fit the
            # word on multiple lines.
            line_prefix = ""
            for h_word in word.split("\N{soft hyphen}"):
                # Measure the width of the word, including the hyphen. This
                # will be the width of the word if it is split on a hyphen.
                width = font.measure(line_prefix + h_word + "-")

                # If adding the word to the line prefix would make the line too
                # long, then flush the line and start a new one.
                if self.cursor_x + width > WIDTH - HSTEP:
                    if line_prefix != "":
                        self.append_line_item(
                            cursor_x=self.cursor_x,
                            text=line_prefix + "-",
                            font=font,
                            superscript=self.superscript,
                        )

                    # Flush the line and start a new one
                    self.flush()
                    # Clear the line prefix
                    line_prefix = ""

                # Add the word to the line prefix. At this point, either the
                # line prefix is empty or the line prefix plus the word plus a
                # hyphen will fit on the current line.
                line_prefix += h_word

            # If there are any characters left over in the line prefix, draw
            # them in the appropriate font.
            if line_prefix != "":
                word = line_prefix

            # Add the word to the line
            self.append_line_item(
                cursor_x=self.cursor_x,
                text=word,
                font=font,
                superscript=self.superscript,
            )

    # Flush the current line of text to the display list. Flushing means
    # adding the line to the display list and resetting the cursor to the
    # beginning of the next line.
    # This new flush function has three responsibilities:
    # It must align the words along the line;
    # It must add all those words to the display list; and
    # It must update the cursor_x and cursor_y fields
    def flush(self) -> None:
        # If the line is empty, do nothing
        if not self.line:
            return

        # Get the maximum ascent and descent for the line
        metrics = [line_item.font.metrics() for line_item in self.line]
        # Locate the tallest word
        max_ascent = max([metric["ascent"] for metric in metrics])
        # The line is then max_ascent below self.y—or actually a little more to
        # account for the leading
        baseline = self.cursor_y + 1.25 * max_ascent

        # If the text is centered, then we need to shift the line to the right.
        # The amount we shift is the difference between the width of the line
        # and the width of the canvas, divided by two. This centers the line.
        shift = 0
        if self.centered:
            # The width of the line is where the cursor is on the line minus
            # the horizontal step. This is because the HSTEP is the left margin
            # of the window, so we subtract this padding from the width of the
            # line.
            line_len = self.cursor_x - HSTEP
            # Calculate the shift. This is the difference between the width of
            # the line and the width of the canvas, divided by two (essentially
            # the whitespace on either side of the line).

            # The 8 is a hack to make the text centered. I don't know why it
            # works, but it does.
            shift = (WIDTH - line_len) / 2 - HSTEP + 8  # no idea why this works

        # Now that we know where the line is, we can place each word relative to
        # that line and add it to the display list
        for line_item in self.line:
            if line_item.superscript:
                # The top of a superscript lines up with the top of a normal letter.
                cursor_y = baseline - max_ascent
            else:
                # Note how y starts at the baseline, and moves UP by just enough
                # to accomodate that word’s ascender.
                cursor_y = baseline - line_item.font.metrics("ascent")

            # Add the word to the display list
            self.display_list.append(
                (line_item.cursor_x + shift, cursor_y, line_item.text, line_item.font)
            )

        # Reset the cursor to the beginning of the next line
        self.cursor_x = HSTEP
        # Reset the line
        self.line = []

        # The cursor_y field should be set to the baseline of the next line.
        max_descent = max([metric["descent"] for metric in metrics])
        # y must be far enough below baseline to account for the deepest
        # descender
        self.cursor_y = baseline + 1.25 * max_descent


class Browser:
    # Constructor
    def __init__(self) -> None:
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        # Pack the canvas into the window. We want to make it resizable, so
        # we use the fill and expand arguments to make it fill the entire
        # window. Read more: https://www.tutorialspoint.com/python/tk_pack.htm
        self.canvas.pack(fill="both", expand=True)

        # Create a font object to use for drawing text on the canvas
        self.fontsize = 16

        # How many pixels has the user scrolled down
        self.scroll = 0

        # Bind the down arrow key to the scrolldown method
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Button-5>", self.scrolldown)  # Linux

        # Bind the up arrow key to the scrollup method
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<Button-4>", self.scrollup)  # Linux

        # Bind the MouseWheel event which triggers when you scroll the mouse
        # wheel or touchpad
        self.window.bind("<MouseWheel>", self.mousewheel)

        # Bind the resize event which triggers when the window is resized
        self.window.bind("<Configure>", self.resize)

        # Bind the plus and minus keys to zooming in and out, respectively
        self.window.bind("+", self.zoomin)
        self.window.bind("-", self.zoomout)

    # Load and display the contents of a web page given its URL
    def load(self, url):
        headers, body = request(url)
        self.tokens = lex(body)

        # Compute the display list for the text of the page
        self.display_list = Layout(self.tokens).display_list
        # Draw the text on the canvas
        self.draw()

    # Draws the text of the page on the canvas
    def draw(self):
        # Clear the canvas, since we don't want to draw on top of the old text
        self.canvas.delete("all")
        for x, y, word, font in self.display_list:
            if y > self.scroll + HEIGHT:
                # In this case, think of self.scroll as the padding above the
                # window on the page. So for example, if self.scroll was 100,
                # then the top of the window would be 100 pixels below the top
                # Then the plus HEIGHT is the bottom of the window, so if the
                # HEIGHT is 600, then the bottom of the window would be 700
                # If the y is greater than 700, then the character is below the
                # bottom of the window, so we can skip drawing it
                continue

            if y + VSTEP < self.scroll:
                # In this case, VSTEP represents the height of the character
                # So y + VSTEP represents the bottom edge of the character to be
                # drawn. Since self.scroll represents the padding above the
                # window to be drawn, if the bottom edge of the character is
                # above the top of the window, then we can skip drawing it
                continue

            if y + font.metrics("linespace") < self.scroll:
                # In this case, font.metrics("linespace") represents the
                # height of the line that the character is on. So y +
                # font.metrics("linespace") represents the bottom edge of the
                # line that the character is on. Since self.scroll represents
                # the padding above the window to be drawn, if the bottom edge
                # of the line is above the top of the window, then we can skip
                # drawing it
                continue

            # Only draw the character if it's in the visible part of the window
            # self.scroll represents the padding above the window to be drawn
            # So y - self.scroll represents the y-coordinate of the character
            # relative to the top of the window, since we are subtracting
            # this padding from y. Thus, we can draw the character at this
            # y-coordinate relative to the top of the window, regardless
            # of the actual y-coordinate of the character on the page
            self.canvas.create_text(
                x, y - self.scroll, text=word, font=font, anchor="nw"
            )

    # Scroll down when the down arrow key is pressed
    def scrolldown(self, event: object) -> None:
        # Add the scroll step to the scroll variable
        self.scroll += SCROLL_STEP
        # Redraw the text on the canvas
        self.draw()

    # Scroll up when the up arrow key is pressed. Make sure that the user
    # cannot scroll up past the top of the page.
    def scrollup(self, event: object) -> None:
        # Subtract the scroll step from the scroll variable
        self.scroll -= SCROLL_STEP

        # If the user has scrolled up past the top of the page, then
        # self.scroll will be negative. In this case, we want to set
        # self.scroll to 0, since we don't want to scroll up past the top
        # of the page.
        if self.scroll < 0:
            self.scroll = 0

        # Redraw the text on the canvas
        self.draw()

    # Scroll up or down when the mouse wheel is scrolled. Make sure that the
    # user cannot scroll up past the top of the page.
    def mousewheel(self, event: object) -> None:
        # The delta attribute of the event object represents how much the
        # user scrolled. If the user scrolled up, then delta will be
        # positive, and if the user scrolled down, then delta will be negative

        # This is why we subtract the delta from the scroll variable. For
        # example, if scroll was 100, and delta was 10, then we would set
        # scroll to 90, which would scroll the page up by 10 pixels
        self.scroll -= event.delta

        # If the user has scrolled up past the top of the page, then
        # self.scroll will be negative. In this case, we want to set
        # self.scroll to 0, since we don't want to scroll up past the top
        # of the page.
        if self.scroll < 0:
            self.scroll = 0

        # Redraw the text on the canvas
        self.draw()

    # Resize the canvas when the window is resized. This method is bound to
    # the <Configure> event, which fires when the window is resized
    def resize(self, event: object) -> None:
        # Update the WIDTH and HEIGHT variables to the new width and height
        # The new width and height can be found in the width and height
        # fields of the event object, since we bound this method to the
        # <Configure> event, which fires when the window is resized
        global WIDTH, HEIGHT
        WIDTH = event.width
        HEIGHT = event.height

        # Compute the display list for the text of the page again, since
        # the width of the window has changed and the text needs to be
        # re-laid out
        self.display_list = Layout(self.tokens).display_list

        # Redraw the text on the canvas
        self.draw()

    # Zoom in when the + key is pressed.
    def zoomin(self, event: object) -> None:
        # Double the font size, because the user pressed the + key
        self.fontsize *= 2

        # Also double the vertical and horizontal step size, since the
        # characters are now twice as big. This is necessary because the
        # layout function uses the VSTEP and HSTEP variables to determine
        # where to place the characters on the page
        global VSTEP, HSTEP
        VSTEP *= 2
        HSTEP *= 2

        # Compute the display list for the text of the page again, since
        # the font size has changed and the text needs to be re-laid out
        self.display_list = Layout(self.tokens).display_list

        # Redraw the text on the canvas
        self.draw()

    # Zoom out when the - key is pressed.
    def zoomout(self, event: object) -> None:
        # Half the font size, because the user pressed the - key
        self.fontsize //= 2  # We want an integer, so we use the // operator

        # Also half the vertical and horizontal step size, since the
        # characters are now half as big. This is necessary because the
        # layout function uses the VSTEP and HSTEP variables to determine
        # where to place the characters on the page
        global VSTEP, HSTEP
        VSTEP //= 2
        HSTEP //= 2

        # Compute the display list for the text of the page again, since
        # the font size has changed and the text needs to be re-laid out
        self.display_list = Layout(self.tokens).display_list

        # Redraw the text on the canvas
        self.draw()


# Load the web page specified by the first command-line argument
if __name__ == "__main__":
    # Construct a browser, then load the web page with the given URL
    Browser().load(url=sys.argv[1])
    tkinter.mainloop()
