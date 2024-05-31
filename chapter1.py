"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 1 (Downloading Web Pages),
without exercises.
"""
import time  # For caching the expiration time of cached pages
import socket  # For connecting to the web
import ssl  # For HTTPS

# A cache of downloaded pages
# The key is the URL, and the value is a tuple of the headers and body and the
# time it expired
# So for example,
# {
#     "http://example.org": ({...}, "Hello, world!", 1234567890),
#     "http://example.org/about": ({...}, "About us", 1234567890),
# }
CACHE = {}

BOOKMARKS = []


# Caching: Typically the same images, styles, and scripts are used on multiple
# pages; downloading them repeatedly is a waste. It’s generally valid to cache
# any HTTP response, as long as it was requested with GET and received a 200
# response.
# Implement a cache in your browser and test it by requesting the same file
# multiple times. Servers control caches using the Cache-Control header.
# Add support for this header, specifically for no-store and max-age values.
# If the Cache-Control header contains any other value than these two, it’s best
# not to cache the response.
def cache(url, headers, body):
    # If there's no cache-control header, don't cache the response
    if "cache-control" not in headers:
        return

    cache_control = headers["cache-control"].lower()
    # If the Cache-Control header contains no-store, don't cache the response
    if "no-store" in cache_control:
        return

    # If the Cache-Control header contains max-age, cache the response
    if "max-age" in cache_control:
        # Get the max-age value
        max_age = int(cache_control.split("max-age=")[1])
        # If the value is a number, cache the response
        if max_age:
            expiration_time = time.time() + max_age
            # Cache the response by adding it to the cache dictionary
            CACHE[url] = (headers, body, expiration_time)
            return


# Make HTTP/HTTPS requests
# Returns a tuple of (headers, body) where headers is a dictionary and body is a
# string
def request(url, headers=None):
    if url == "about:bookmarks":
        body = "<!doctype html>\n"
        for bookmark in BOOKMARKS:
            body += '<a href="{}">{}</a><br>\n'.format(bookmark, bookmark)
        return None, body

    # Check the cache for the URL
    if url in CACHE:
        headers, body, expiration_time = CACHE[url]
        # If the URL hasn't expired in the cache, return the cached response
        # That is, if the current time is less than the expiration time
        if time.time() < expiration_time:
            return headers, body

        # The URL has expired, remove it from the cache
        del CACHE[url]

    full_url = url

    # Split the URL into scheme and URL parts based on the presence of `://`
    # So for example, "http://example.org:8080/index.html" becomes "http" and
    # "example.org:8080/index.html"
    scheme, url = url.split("://", 1)
    # Check that the scheme is either "http" or "https".
    # If not, raise an exception.
    assert scheme in ["http", "https", "file"], f"Unknown scheme: {scheme}"

    # If the scheme is "file", we're looking at a local file, so open it and
    # return the contents
    if scheme == "file":
        with open(url) as f:
            return {}, f.read()

    # Split the URL into host and path parts based on the presence of `/`
    # So for example, "example.org:8080/index.html" becomes "example.org:8080"
    # and "/index.html".
    if "/" in url:
        host, path = url.split("/", 1)
        path = "/" + path
    # If there is no `/`, then the path is just `/`.
    else:
        host = url
        path = "/"

    # Set the port number to 80 for "http" URLs and 443 for "https" URLs
    port = 80 if scheme == "http" else 443

    # If the host includes a port number, split it into host and port parts
    # So for example, "example.org:8080" becomes "example.org" and 8080
    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    # Create a new socket object and connect it to the host on the specified port
    s = socket.socket(
        # A socket has an address family, which tells you how to find the other
        # computer. Address families have names that begin with AF. We want
        # AF_INET, but for example AF_BLUETOOTH is another.
        family=socket.AF_INET,
        # A socket has a type, which describes the sort of conversation that’s
        # going to happen. Types have names that begin with SOCK. We want
        # SOCK_STREAM, which means each computer can send arbitrary amounts of
        # data over, but there’s also SOCK_DGRAM, in which case they send each
        # other packets of some fixed size.
        type=socket.SOCK_STREAM,
        # A socket has a protocol, which describes the steps by which the two
        # computers will establish a connection. Protocols have names that
        # depend on the address family, but we want IPPROTO_TCP.
        proto=socket.IPPROTO_TCP,
    )
    s.connect((host, port))

    # The difference between http and https is that https is more secure—but
    # let’s be a little more specific. The https scheme, or more formally HTTP
    # over TLS, is identical to the normal http scheme, except that all
    # communication between the browser and the host is encrypted.

    # If the scheme is "https", wrap the socket in an SSL context
    if scheme == "https":
        # Making an encrypted connection with ssl is pretty easy. Suppose you’ve
        # already created a socket, s, and connected it to example.org. To
        # encrypt the connection, you use ssl.create_default_context to create
        # a context ctx and use that context to wrap the socket s.
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)

        # When you wrap s, you pass a server_hostname argument, and it should
        # match the argument you passed to s.connect. Note that I save the new
        # socket back into the s variable. That’s because you don’t want to send
        # over the original socket; it would be unencrypted and also confusing.

    # Send an HTTP GET request to the server for the specified path
    # Default headers to send
    request_headers = {
        "host": host,
        "connection": "close",
        "user-agent": "abosh",
    }

    # If the `headers` argument includes headers that are sent by default, like `User-Agent`,
    # the `headers` argument should overwrite their value.
    # In other words, the request should only contain one occurrence of each header.
    if headers:
        # Can probably use request_headers.update(headers) here, but
        # I want to do a case-insenstive lookup
        for key, value in headers.items():
            request_headers[key.lower()] = value

    # Convert the headers into a string. Don't forget we need the blank line at the end!
    header_str = (
        "".join(f"{key}: {value}\r\n" for key, value in request_headers.items())
        + "\r\n"
    )

    request_str = f"GET {path} HTTP/1.1\r\n{header_str}\r\n".encode("utf8")
    s.send(request_str)

    # Read the server's response
    response = s.makefile("r", encoding="utf8", newline="\r\n")

    # Parse the status line and check that the status code is 200 OK
    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)

    # Note that I do not check that the server’s version of HTTP is the same as
    # mine; this might sound like a good idea, but there are a lot of
    # misconfigured servers out there that respond in HTTP 1.1 even when you
    # talk to them in HTTP 1.0.
    assert status == "200" or status.startswith(
        "3"
    ), (  # 3xx is a redirect
        f"Status code was not 200, instead received {status}: {explanation}"
    )

    # Parse the headers and fill a map of header names to header values,
    # stripping whitespace from the values
    headers = {}
    while True:
        line = response.readline()
        if line == "\r\n":
            break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()

    # Redirects: Error codes in the 300 range request a redirect.
    # When your browser encounters one, it should make a new request to the URL
    # given in the Location header. Sometimes the Location header is a full URL,
    # but sometimes it skips the host and scheme and just starts with a /
    # (meaning the same host and scheme as the original request). The new URL
    # might itself be a redirect, so make sure to handle that case. You don’t,
    # however, want to get stuck in a redirect loop, so make sure limit how many
    # redirects your browser can follow in a row. You can test this with with
    # the URL http://browser.engineering/redirect, which redirects back to this
    # page.
    if status.startswith("3"):
        location = headers["location"]
        if location.startswith("/"):
            location = f"{scheme}://{host}{location}"

        return request(location, headers)

    # Headers can describe all sorts of information, but a couple of headers are
    # especially important because they tell us that the data we’re trying to
    # access is being sent in an unusual way. Let’s make sure none of those are
    # present.
    assert "transfer-encoding" not in headers, "Transfer encoding not supported"
    assert "content-encoding" not in headers, "Content encoding not supported"

    # Read the body of the response and close the socket
    body = response.read()
    s.close()

    # Cache the response if the response is 200
    if status == "200":
        cache(full_url, headers, body)

    # Return the headers and body of the response
    return headers, body


# Remove HTML tags from a string and print the result
def show(body):
    # Represents if we are currently inside an HTML tag
    in_angle = False
    for c in body:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
        elif not in_angle:
            print(c, end="")


# Load and display the contents of a web page given its URL
def load(url):
    headers, body = request(url)
    show(body)


# Load the web page specified by the first command-line argument
if __name__ == "__main__":
    import sys

    load(sys.argv[1])
