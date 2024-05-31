import sys  # For parsing command-line arguments
import tkinter as tk  # For the GUI

from typing import *
from chapter3 import Browser


# A class to represent a string of text
class Text:
    def __init__(self, text: str, parent):
        self.text = text
        self.children = (
            []
        )  # Text nodes have no children, but we’ll need this for consistency
        # to avoid calling isinstance calls throughout the code
        self.parent = parent

    def __repr__(self):
        return repr(self.text)


class Element:
    def __init__(self, tag: str, attributes: dict[str, str], parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

    def __repr__(self):
        result = "<" + self.tag
        for key, value in self.attributes.items():
            result += f' {key}="{value}"'
        result += ">"
        return result


Node = Union[Text, Element]


# Parsing is a little more complex than lex, so we’re going to want to break it
# into several functions, organized in a new HTMLParser class. That class can
# also store the source code it’s analyzing and the incomplete tree.
class HTMLParser:
    # The tags that you’re supposed to put into the <head> element
    HEAD_TAGS = [
        "base",
        "basefont",
        "bgsound",
        "noscript",
        "link",
        "meta",
        "title",
        "style",
        "script",
    ]

    # Elements like <meta> and <link> are what are called self-closing: these tags
    # don’t surround content, so you don’t ever write </meta> or </link>. Our parser
    # needs special support for them. In HTML, there’s a specific list of these
    # self-closing tags (the spec calls them “void” tags):
    SELF_CLOSING_TAGS = [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]

    def __init__(self, body: str):
        self.body = body
        # Parser reads tags left to right. Unfinished tags have always
        # been opened but not closed; they are always to the right of the
        # finished nodes, and they are always children of other unfinished tags.

        # This is an incomplete tree, which stores unfinished tags ordered with
        # parents before children. First node in the list is the root of the
        # HTML tree; the last node in the list is the most recent unfinished tag.
        self.unfinished = []

    # parse html
    def parse(self) -> Node:
        # Text buffer
        text = ""
        # If we are inside a tag
        in_tag = False
        in_comment = False
        in_single_quote = False
        in_double_quote = False
        # In a script tag
        in_script_tag = False
        current_tag = ""
        i = 0  # current index in body

        while i < len(self.body):
            # Update the HTML lexer to support comments. Comments in HTML begin
            # with <!-- and end with -->. However, comments aren’t the same as
            # tags: they can contain any text, including left and right angle
            # brackets. The lexer should skip comments, not generating any token
            # at all. Check: is <!--> a comment, or does it just start one?
            # Check for beginning of comment
            if not in_comment and self.body[i : i + 4] == "<!--":
                # Skip the opening of the comment
                i += 4
                in_comment = True
                continue
            # Check for end of comment
            elif in_comment and self.body[i : i + 3] == "-->":
                # Skip the ending of the comment
                i += 3
                in_comment = False
                # If we're not in a tag, add the text to the tree.
                if text and not in_tag:
                    self.add_text(text)
                    text = ""
                continue
            # If we're in a comment, skip the character. Don't generate
            # any token at all for comments.
            elif in_comment:
                i += 1
                continue

            c = self.body[i]
            # Quoted attributes can contain spaces and right angle brackets.
            # Fix the lexer so that this is supported properly.
            # Hint: the current lexer is a finite state machine, with two states
            # (determined by in_tag). You’ll need more states.
            if in_tag:
                if c == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif c == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote

            # JavaScript code embedded in a <script> tag uses the left angle
            # bracket to mean less-than. Modify your lexer so that the contents
            # of <script> tags are treated specially: no tags are allowed inside
            # <script>, except the </script> close tag.
            if c == "<":
                if in_script_tag:
                    # Check for end of script tag
                    if self.body[i : i + 9] == "</script>":
                        in_script_tag = False
                    # JavaScript code embedded in a <script> tag uses the left
                    # angle bracket to mean less-than, so we need to add it to
                    # the text, and not treat it as a tag.
                    else:
                        text += c
                        i += 1
                        continue
                # If we encounter a < and we're in a quote, add it to the text
                # because it's not a tag.
                elif in_tag and in_single_quote or in_double_quote:
                    text += c
                    i += 1
                    continue

                # We are not in a tag, so we are starting a new tag.
                in_tag = True
                # If we have text, add it to the tree. This is the case where
                # we have text before a tag.
                if text:
                    self.add_text(text)

                # Reset text
                text = ""

            # Otherwise, we encountered a right angle bracket, which means
            # we are ending a tag. We need to add the tag to the tree.
            elif c == ">":
                # If we're in a script tag, add the > to the text. This is because
                # JavaScript code embedded in a <script> tag uses the right angle
                # bracket to mean greater-than.
                if in_script_tag:
                    text += c
                    i += 1
                    continue
                # If we encounter a > and we're in a quote, add it to the text
                # as well because it's not a tag.
                elif in_tag and in_single_quote or in_double_quote:
                    text += c
                    i += 1
                    continue

                # Close the tag
                in_tag = False
                current_tag = self.add_tag(text)
                # if current_tag and current_tag.tag == "script":
                #     in_script_tag = True
                text = ""
            else:
                text += c

            i += 1

        if text and not in_tag:
            self.add_text(text)

        return self.finish()

    # To add a text node we add it as a child of the most recent unfinished tag.
    def add_text(self, text: str) -> None:
        # Ignore whitespace-only text nodes
        if text.isspace():
            return

        # The argument to implicit_tags is the tag name (or None for text nodes),
        # which we’ll compare to the list of unfinished tags to determine what’s
        # been omitted
        self.implicit_tags(None)
        # Get the most recent unfinished tag
        parent = self.unfinished[-1]
        # Create a new Text node
        node = Text(text, parent)
        # Add it as a child of the most recent unfinished tag
        parent.children.append(node)

    def add_tag(self, tag: str) -> Node:
        tag, attributes = self.get_attributes(tag)
        # Ignore most comments and doctypes
        if tag.startswith("!"):
            return

        self.implicit_tags(tag)
        # Closing tag starts with /
        if tag.startswith("/"):
            # Edge case: this is the very last tag. There's no unfinished node to add it to.
            if len(self.unfinished) == 1:
                return

            # A close tag removes an unfinished node, by finishing it, and add
            # it to the next unfinished node in the list.
            # Get the most recent unfinished tag
            node = self.unfinished.pop()
            # Get the parent of the most recent unfinished tag
            parent = self.unfinished[-1]
            # Add the finished node as a child of the parent
            parent.children.append(node)
        # Self-closing tags don't have a closing tag, so we want to auto-close them.
        elif tag in self.SELF_CLOSING_TAGS:
            # Get the most recent unfinished tag
            parent = self.unfinished[-1]
            # Create a new Element node
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            # An open tag instead adds an unfinished node to the end of the list
            # Get the most recent unfinished tag. The very first tag is an edge
            # case without a parent.
            parent = self.unfinished[-1] if self.unfinished else None

            # It’s not clear what it would mean for one paragraph to contain another.
            # Change the parser so that a document like <p>hello<p>world</p> results
            # in two sibling paragraphs instead of one paragraph inside another;
            # real browsers do this too.
            if tag == "p" and self.open_paragraph():
                # Close all unclosed tags in the paragraph. We need to do this
                # because we're going to close the paragraph tag, to start a
                # new paragraph, and we don't want to close the tags in the
                # middle of the paragraph. We'll re-open them after we start
                # the new paragraph.

                # "Any tags that are open when encountering the second paragraph
                #  should be closed with the first paragraph, but also reopened
                #  and applied to the second."
                unclosed = []
                for node in reversed(self.unfinished):
                    # Found the opening paragraph tag
                    if node.tag == "p":
                        break
                    # Else, add the tag to be closed to the list of unclosed tags
                    unclosed.append(node)

                unclosed = reversed(unclosed)

                # Close the paragraph tag
                self.add_tag("/p")
                # Open the new paragraph tag
                self.add_tag("p")

                # Re-open the unclosed tags
                for node in unclosed:
                    self.add_tag(node.tag)

                # Return the new paragraph tag
                return node

            # Create a new Element node
            node = Element(tag, attributes, parent)
            # Add it as a child of the most recent unfinished tag
            self.unfinished.append(node)

        return node

    def implicit_tags(self, tag: str) -> None:
        # More than one tag could have been omitted in a row; every iteration
        # around the loop will add just one. To determine which implicit tag to
        # add, if any, requires examining the open tags and the tag being inserted.
        while True:
            open_tags = [node.tag for node in self.unfinished]
            # Let’s start with the easiest case, the implicit <html> tag. An
            # implicit <html> tag is necessary if the first tag in the document
            # is something other than <html>.
            if open_tags == [] and tag != "html":
                self.add_tag("html")

            # Both <head> and <body> can also be omitted, but to figure out which
            # it is we need to look at which tag is being added
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")

            # Finally, the </head> tag can also be implicit, if the parser is
            # inside the <head> and sees an element that’s supposed to go in the
            # <body>
            elif (
                open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS
            ):
                self.add_tag("/head")

            # Technically, the </body> and </html> tags can also be implicit.
            # But since our finish function already closes any unfinished tags,
            # that doesn’t need any extra code. So all that’s left for
            # implicit_tags tags is to exit out of the loop
            else:
                break

    # Returns true if there is an open paragraph tag in the unfinished list.
    # This is useful in add_tag to determine if we need to close the paragraph
    # tag before opening a new sibling one.
    def open_paragraph(self) -> bool:
        for node in reversed(self.unfinished):
            if isinstance(node, Element) and node.tag == "p":
                return True
        return False

    # Once the parser is done, it turns our incomplete tree into a complete tree
    # by just finishing any unfinished nodes.
    def finish(self):
        # If there are no unfinished nodes, add an html node. This is the root
        # of the tree.
        if len(self.unfinished) == 0:
            self.add_tag("html")

        # Finish any unfinished nodes
        while len(self.unfinished) > 1:
            # Get the most recent unfinished tag
            node = self.unfinished.pop()
            # Get the parent of the most recent unfinished tag
            parent = self.unfinished[-1]
            # Add the finished node as a child of the parent
            parent.children.append(node)

        # Return the root of the tree
        return self.unfinished.pop()

    # Since we’re not handling whitespace in values, we can split on whitespace
    # to get the tag name and the attribute-value pairs.
    def get_attributes(self, text: str):
        if " " not in text:
            return text, {}

        tag, attrpairs = text.split(maxsplit=1)
        attributes = {}
        # Stores the current key and value being built
        current_key, current_value = "", ""
        # We need to keep track of whether we’re building a key or a value.
        building_key = True
        # If we're in an escape sequence
        in_escape = False
        # If we're in a single-quoted string
        in_single_quote = False
        # If we're in a double-quoted string
        in_double_quote = False

        for c in attrpairs:
            # If we hit a space, there's a bunch of weird cases
            if c == " ":
                # If we're building a key, we can just ignore it
                if building_key:
                    continue

                # If we're in a quoted string, we can just add it to the value
                # buffer
                if in_single_quote or in_double_quote:
                    current_value += c
                # If we're not in a quoted string, we need to check if we're
                else:
                    # Add the key-value pair to the attributes dictionary
                    attributes[current_key.lower()] = current_value
                    # Reset the key and value buffers
                    current_key = ""
                    current_value = ""
                    # Start building a new key
                    building_key = True

            # We're in the case where we found the = sign, which signifies the
            # end of the key and the start of the value. We need to handle the
            # case where the value is quoted, and the case where it's not.
            elif c == "=":
                if building_key:
                    # We do this for quoted attributes
                    if not current_key:
                        current_key += c
                    else:
                        building_key = False
                # If we're building a value, we need to check if we're in a
                # quoted string or not
                else:
                    current_value += c
            # Double quoted string
            elif c == '"':
                if in_escape:
                    current_value += c
                    in_escape = False
                elif in_single_quote:
                    current_value += c
                else:
                    if in_double_quote:
                        # Add the key-value pair to the attributes dictionary
                        attributes[current_key.lower()] = current_value
                        # Reset the key and value buffers
                        current_key = ""
                        current_value = ""
                        # Start building a new key
                        building_key = True

                    in_double_quote = not in_double_quote
            # Single quoted string
            elif c == "'":
                if in_escape:
                    current_value += c
                    in_escape = False
                elif in_double_quote:
                    current_value += c
                else:
                    if in_single_quote:
                        # Add the key-value pair to the attributes dictionary
                        attributes[current_key.lower()] = current_value
                        # Reset the key and value buffers
                        current_key = ""
                        current_value = ""
                        # Start building a new key
                        building_key = True

                    in_single_quote = not in_single_quote
            # Escape sequence
            elif c == "\\":
                if in_escape:
                    current_value += c

                in_escape = not in_escape
            # Normal character, but we're building a key
            elif building_key:
                current_key += c
            # Normal character, but we're building a value
            else:
                current_value += c

        # Add the last key-value pair to the attributes dictionary
        if current_key:
            attributes[current_key.lower()] = current_value

        return tag, attributes


# Recursive pretty printer.
def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


if __name__ == "__main__":
    Browser().load(sys.argv[1])
    tk.mainloop()
