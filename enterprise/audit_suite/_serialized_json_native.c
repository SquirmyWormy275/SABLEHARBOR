/* Optional CPython accelerator. A true result means byte-for-byte
 * Store.canonical JSON. Every other input uses the existing
 * json.loads/canonical path. No source objects or validation results survive
 * this function. */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>
#include <string.h>

typedef struct {
  const unsigned char *s;
  Py_ssize_t n, i;
  int limit;
  PyObject *requested, *projection;
} Parser;
typedef struct {
  const unsigned char *s;
  Py_ssize_t n;
  unsigned char *owned;
} Key;
static int value(Parser *p);
static int hex(unsigned char c) {
  return c >= '0' && c <= '9'   ? c - '0'
         : c >= 'a' && c <= 'f' ? c - 'a' + 10
                                : -1;
}
static int utf8(Parser *p, unsigned char a) {
  int count;
  unsigned char lo = 0x80, hi = 0xbf;
  if (a >= 0xc2 && a <= 0xdf)
    count = 1;
  else if (a >= 0xe0 && a <= 0xef) {
    count = 2;
    if (a == 0xe0)
      lo = 0xa0;
    if (a == 0xed)
      hi = 0x9f;
  } else if (a >= 0xf0 && a <= 0xf4) {
    count = 3;
    if (a == 0xf0)
      lo = 0x90;
    if (a == 0xf4)
      hi = 0x8f;
  } else
    return 0;
  if (p->n - p->i < count)
    return 0;
  if (p->s[p->i] < lo || p->s[p->i] > hi)
    return 0;
  p->i++;
  while (--count) {
    if (p->s[p->i] < 0x80 || p->s[p->i] > 0xbf)
      return 0;
    p->i++;
  }
  return 1;
}
static unsigned char simple(unsigned char c) {
  switch (c) {
  case '"':
    return '"';
  case '\\':
    return '\\';
  case 'b':
    return 8;
  case 'f':
    return 12;
  case 'n':
    return 10;
  case 'r':
    return 13;
  case 't':
    return 9;
  default:
    return 255;
  }
}
static int string(Parser *p, Key *key) {
  if (p->i >= p->n || p->s[p->i++] != '"')
    return 0;
  Py_ssize_t start = p->i;
  int escaped = 0;
  while (p->i < p->n) {
    unsigned char c = p->s[p->i++];
    if (c == '"') {
      if (key) {
        key->s = p->s + start;
        key->n = p->i - start - 1;
        key->owned = NULL;
        if (escaped) {
          unsigned char *out = PyMem_Malloc((size_t)key->n + 1);
          if (!out) {
            PyErr_NoMemory();
            return 0;
          }
          Py_ssize_t z = 0;
          for (Py_ssize_t k = start; k < p->i - 1; k++) {
            unsigned char a = p->s[k];
            if (a == '\\') {
              a = p->s[++k];
              if (a == 'u') {
                a = (unsigned char)(hex(p->s[k + 3]) * 16 + hex(p->s[k + 4]));
                k += 4;
              } else
                a = simple(a);
            }
            out[z++] = a;
          }
          key->s = key->owned = out;
          key->n = z;
        }
      }
      return 1;
    }
    if (c < 0x20)
      return 0;
    if (c == '\\') {
      escaped = 1;
      if (p->i >= p->n)
        return 0;
      c = p->s[p->i++];
      if (c == 'u') {
        if (p->n - p->i < 4 || p->s[p->i] != '0' || p->s[p->i + 1] != '0')
          return 0;
        int a = hex(p->s[p->i + 2]), b = hex(p->s[p->i + 3]);
        if (a < 0 || b < 0)
          return 0;
        int v = a * 16 + b;
        if (v >= 0x20 || v == 8 || v == 9 || v == 10 || v == 12 || v == 13)
          return 0;
        p->i += 4;
      } else if (simple(c) == 255)
        return 0;
    } else if (c >= 0x80 && !utf8(p, c))
      return 0;
  }
  return 0;
}
static int number(Parser *p) {
  Py_ssize_t start = p->i, digits;
  int minus = 0, floating = 0;
  if (p->s[p->i] == '-') {
    minus = 1;
    p->i++;
    if (p->i == p->n)
      return 0;
  }
  digits = p->i;
  if (p->s[p->i] == '0') {
    p->i++;
    if (p->i < p->n && p->s[p->i] >= '0' && p->s[p->i] <= '9')
      return 0;
  } else {
    if (p->s[p->i] < '1' || p->s[p->i] > '9')
      return 0;
    do {
      p->i++;
    } while (p->i < p->n && p->s[p->i] >= '0' && p->s[p->i] <= '9');
  }
  Py_ssize_t ndigits = p->i - digits;
  if (p->i < p->n && p->s[p->i] == '.') {
    floating = 1;
    p->i++;
    Py_ssize_t d = p->i;
    while (p->i < p->n && p->s[p->i] >= '0' && p->s[p->i] <= '9')
      p->i++;
    if (d == p->i)
      return 0;
  }
  if (p->i < p->n && (p->s[p->i] == 'e' || p->s[p->i] == 'E')) {
    floating = 1;
    p->i++;
    if (p->i < p->n && (p->s[p->i] == '+' || p->s[p->i] == '-'))
      p->i++;
    Py_ssize_t d = p->i;
    while (p->i < p->n && p->s[p->i] >= '0' && p->s[p->i] <= '9')
      p->i++;
    if (d == p->i)
      return 0;
  }
  if (!floating)
    return !(minus && ndigits == 1 && p->s[digits] == '0') &&
           (!p->limit || ndigits <= p->limit);
  PyObject *text =
      PyUnicode_FromStringAndSize((const char *)p->s + start, p->i - start);
  if (!text)
    return 0;
  PyObject *v = PyFloat_FromString(text);
  Py_DECREF(text);
  if (!v)
    return 0;
  if (!isfinite(PyFloat_AS_DOUBLE(v))) {
    Py_DECREF(v);
    return 0;
  }
  PyObject *repr = PyObject_Repr(v);
  Py_DECREF(v);
  if (!repr)
    return 0;
  Py_ssize_t n;
  const char *s = PyUnicode_AsUTF8AndSize(repr, &n);
  int ok = s && n == p->i - start && !memcmp(s, p->s + start, (size_t)n);
  Py_DECREF(repr);
  return ok;
}
static int object(Parser *p) {
  int project_root = p->i == 0 && p->projection != NULL;
  p->i++;
  Key previous = {NULL, 0, NULL};
  int ok = 0;
  if (p->i < p->n && p->s[p->i] == '}') {
    p->i++;
    return 1;
  }
  for (;;) {
    Key current = {NULL, 0, NULL};
    if (!string(p, &current))
      goto finish;
    if (previous.s) {
      Py_ssize_t n = current.n < previous.n ? current.n : previous.n;
      int c = memcmp(previous.s, current.s, (size_t)n);
      if (c > 0 || (c == 0 && previous.n >= current.n)) {
        PyMem_Free(current.owned);
        goto finish;
      }
    }
    PyMem_Free(previous.owned);
    previous = current;
    if (p->i >= p->n || p->s[p->i++] != ':')
      goto finish;
    Py_ssize_t start = p->i;
    if (!value(p))
      goto finish;
    if (project_root) {
      PyObject *name = PyUnicode_DecodeUTF8((const char *)previous.s,
                                          previous.n, "strict");
      if (!name)
        goto finish;
      int requested = PySet_Contains(p->requested, name);
      if (requested < 0) {
        Py_DECREF(name);
        goto finish;
      }
      if (requested) {
        PyObject *raw = PyBytes_FromStringAndSize((const char *)p->s + start,
                                                p->i - start);
        if (!raw || PyDict_SetItem(p->projection, name, raw) < 0) {
          Py_XDECREF(raw);
          Py_DECREF(name);
          goto finish;
        }
        Py_DECREF(raw);
      }
      Py_DECREF(name);
    }
    if (p->i >= p->n)
      goto finish;
    unsigned char c = p->s[p->i++];
    if (c == '}') {
      ok = 1;
      goto finish;
    }
    if (c != ',')
      goto finish;
  }
finish:
  PyMem_Free(previous.owned);
  return ok;
}
static int array(Parser *p) {
  p->i++;
  if (p->i < p->n && p->s[p->i] == ']') {
    p->i++;
    return 1;
  }
  for (;;) {
    if (!value(p) || p->i >= p->n)
      return 0;
    unsigned char c = p->s[p->i++];
    if (c == ']')
      return 1;
    if (c != ',')
      return 0;
  }
}
static int value(Parser *p) {
  if (p->i >= p->n)
    return 0;
  unsigned char c = p->s[p->i];
  if (c == '{' || c == '[') {
    if (Py_EnterRecursiveCall(" while validating canonical JSON"))
      return 0;
    int ok = c == '{' ? object(p) : array(p);
    Py_LeaveRecursiveCall();
    return ok;
  }
  if (c == '"')
    return string(p, NULL);
  if (c == '-' || (c >= '0' && c <= '9'))
    return number(p);
  const char *word = c == 't'   ? "true"
                     : c == 'f' ? "false"
                     : c == 'n' ? "null"
                                : NULL;
  if (!word)
    return 0;
  Py_ssize_t n = (Py_ssize_t)strlen(word);
  if (p->n - p->i < n || memcmp(p->s + p->i, word, (size_t)n))
    return 0;
  p->i += n;
  return 1;
}
static PyObject *validate(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *raw;
  int limit = 4300;
  if (!PyArg_ParseTuple(args, "O|i", &raw, &limit))
    return NULL;
  if (!PyBytes_CheckExact(raw) || limit < 0) {
    PyErr_SetString(PyExc_TypeError,
                    "Exact bytes and nonnegative integer digit limit required");
    return NULL;
  }
  Parser p = {(const unsigned char *)PyBytes_AS_STRING(raw),
              PyBytes_GET_SIZE(raw), 0, limit, NULL, NULL};
  int ok = value(&p) && p.i == p.n;
  if (PyErr_Occurred()) {
    if (PyErr_ExceptionMatches(PyExc_MemoryError))
      return NULL;
    PyErr_Clear();
    ok = 0;
  }
  return PyBool_FromLong(ok);
}
static PyObject *project(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *raw, *fields;
  int limit = 4300;
  if (!PyArg_ParseTuple(args, "OO|i", &raw, &fields, &limit))
    return NULL;
  if (!PyBytes_CheckExact(raw) || !PyTuple_CheckExact(fields) || limit < 0) {
    PyErr_SetString(PyExc_TypeError,
                    "Exact bytes, field tuple and nonnegative digit limit required");
    return NULL;
  }
  for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(fields); i++) {
    if (!PyUnicode_CheckExact(PyTuple_GET_ITEM(fields, i))) {
      PyErr_SetString(PyExc_TypeError, "Exact unique string field names required");
      return NULL;
    }
  }
  PyObject *requested = PySet_New(fields);
  if (!requested)
    return NULL;
  if (PySet_GET_SIZE(requested) != PyTuple_GET_SIZE(fields)) {
    Py_DECREF(requested);
    PyErr_SetString(PyExc_TypeError, "Exact unique string field names required");
    return NULL;
  }
  PyObject *projection = PyDict_New();
  if (!projection) {
    Py_DECREF(requested);
    return NULL;
  }
  Parser p = {(const unsigned char *)PyBytes_AS_STRING(raw),
              PyBytes_GET_SIZE(raw), 0, limit, requested, projection};
  int root_object = p.n > 0 && p.s[0] == '{';
  int ok = value(&p) && p.i == p.n && root_object;
  Py_DECREF(requested);
  if (PyErr_Occurred()) {
    if (PyErr_ExceptionMatches(PyExc_MemoryError)) {
      Py_DECREF(projection);
      return NULL;
    }
    PyErr_Clear();
    ok = 0;
  }
  if (!ok) {
    Py_DECREF(projection);
    Py_RETURN_NONE;
  }
  return projection;
}
static PyMethodDef methods[] = {
    {"validate", validate, METH_VARARGS,
     "Strictly validate Store canonical serialized UTF-8 JSON."},
    {"project", project, METH_VARARGS,
     "Validate the entire canonical object, returning exact requested root value bytes."},
    {NULL, NULL, 0, NULL}};
static struct PyModuleDef module = {PyModuleDef_HEAD_INIT,
                                    "_serialized_json_native",
                                    NULL,
                                    -1,
                                    methods,
                                    NULL,
                                    NULL,
                                    NULL,
                                    NULL};
PyMODINIT_FUNC PyInit__serialized_json_native(void) {
  return PyModule_Create(&module);
}
