console = {
  log: function (x) {
    call_python("log", x);
  },
};

document = {
  querySelectorAll: function (s) {
    return handlesToNodes(call_python("querySelectorAll", s));
  },
  createElement: function (tag) {
    var handle = call_python("create_element", tag);
    return new Node(handle);
  },
};

Object.defineProperty(Node.prototype, "children", {
  get: function () {
    return handlesToNodes(call_python("get_children", this.handle));
  },
});

// Helper function to take an array of handles and map it to Nodes
function handlesToNodes(handles) {
  return handles.map(function (h) {
    return new Node(h);
  });
}

function Node(handle) {
  this.handle = handle;
}

Node.prototype.getAttribute = function (attr) {
  return call_python("getAttribute", this.handle, attr);
};

LISTENERS = {};

function Event(type) {
  this.type = type;
  this.do_default = true;
  this.stop_propagation = false;
}

Event.prototype.stopPropagation = function () {
  this.stop_propagation = true;
};

Event.prototype.preventDefault = function () {
  this.do_default = false;
};

Node.prototype.addEventListener = function (type, listener) {
  if (!LISTENERS[this.handle]) LISTENERS[this.handle] = {};
  var dict = LISTENERS[this.handle];
  if (!dict[type]) dict[type] = [];
  var list = dict[type];
  list.push(listener);
};

Object.defineProperty(Node.prototype, "innerHTML", {
  set: function (s) {
    call_python("innerHTML_set", this.handle, s.toString());
  },
});

Node.prototype.dispatchEvent = function (evt) {
  var type = evt.type;
  var handle = this.handle;
  var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
  for (var i = 0; i < list.length; i++) {
    list[i].call(this, evt);
  }
  return {
    do_default: evt.do_default,
    stop_propagation: evt.stop_propagation,
  };
};

Node.prototype.appendChild = function (child) {
  call_python("append_child", this.handle, child.handle);
  return child;
};

Node.prototype.insertBefore = function (newNode, referenceNode) {
  if (!referenceNode) {
    return this.appendChild(newNode);
  }
  call_python(
    "insert_before",
    this.handle,
    newNode.handle,
    referenceNode.handle
  );
  return newNode;
};
