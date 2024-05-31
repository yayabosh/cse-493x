import sys  # For parsing command-line arguments
import tkinter  # For the GUI
import tkinter.font
from chapter1 import request  # For getting the web page


# Remove HTML tags from a string. Return the resulting string.
def lex(body):
    text = ""
    # Represents if we are currently inside an HTML tag
    in_angle = False
    for c in body:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
        elif not in_angle:
            text += c

    return text


# Fixed width and height for the browser window
WIDTH, HEIGHT = 800, 600
# Fixed width for how many x- and y-pixels we should move between characters and
# lines, respectively
HSTEP, VSTEP = 13, 18
# How many pixels to scroll when the user presses the down arrow key
SCROLL_STEP = 100


# Given a string of text, return a list of tuples, where each tuple
# contains the x- and y-coordinates of the character, as well as the
# character itself. The list is in the order that the characters should
# be drawn on the screen.
def layout(text: str) -> list[tuple[int, int, str]]:
    display_list = []
    # Point to where the next character will go, as if we were typing the
    # text within a word processor.
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        if c == "\n":
            # If the character is a newline character, increment y by
            # more than VSTEP to give the illusion of paragraphs
            cursor_y += 2 * VSTEP
            cursor_x = HSTEP
            continue

        # Add the character to the display list with its x- and y-coordinates
        display_list.append((cursor_x, cursor_y, c))

        # Move the cursor to the right in the line
        cursor_x += HSTEP

        # Line breaks. Think of WIDTH - MARGIN as the margin on the right
        # side of the window. If the cursor is at the margin, then adding
        # the next character would go past the right edge of the window.
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP  # Move down to the next line
            cursor_x = HSTEP  # Move to the left edge of the window

    return display_list


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
        self.text = lex(body)
        # Top left corner is (x0, y0) (first two args), bottom right is (x1, y1)
        # self.canvas.create_rectangle(10, 20, 400, 300)

        # Compute the display list for the text of the page
        self.display_list = layout(self.text)
        # Draw the text on the canvas
        self.draw()

    # Draws the text of the page on the canvas
    def draw(self):
        # Clear the canvas, since we don't want to draw on top of the old text
        self.canvas.delete("all")
        for x, y, c in self.display_list:
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

            # Only draw the character if it's in the visible part of the window
            # self.scroll represents the padding above the window to be drawn
            # So y - self.scroll represents the y-coordinate of the character
            # relative to the top of the window, since we are subtracting
            # this padding from y. Thus, we can draw the character at this
            # y-coordinate relative to the top of the window, regardless
            # of the actual y-coordinate of the character on the page
            self.canvas.create_text(
                x, y - self.scroll, text=c, font=tkinter.font.Font(size=self.fontsize)
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
        self.display_list = layout(self.text)

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
        self.display_list = layout(self.text)

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
        self.display_list = layout(self.text)

        # Redraw the text on the canvas
        self.draw()


# Load the web page specified by the first command-line argument
if __name__ == "__main__":
    # Construct a browser, then load the web page with the given URL
    Browser().load(url=sys.argv[1])
    tkinter.mainloop()
