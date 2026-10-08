/* Byte boundary selection only. Input serialization and node verification
 * remain Python's existing exact contracts. No input or result survives. */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>

static uint64_t mix(uint64_t value) {
  value += UINT64_C(0x9e3779b97f4a7c15);
  value = (value ^ (value >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
  value = (value ^ (value >> 27)) * UINT64_C(0x94d049bb133111eb);
  return value ^ (value >> 31);
}

static int append_offset(PyObject *result, Py_ssize_t end) {
  PyObject *offset = PyLong_FromSsize_t(end);
  if (!offset)
    return 0;
  int ok = PyList_Append(result, offset) == 0;
  Py_DECREF(offset);
  return ok;
}

static int split_range(PyObject *result, const unsigned char *data,
                       Py_ssize_t begin, Py_ssize_t end, uint64_t *table) {
  uint64_t hash = 0;
  Py_ssize_t start = begin;
  for (Py_ssize_t i = begin; i < end; i++) {
    hash = (hash << 1) + table[data[i]];
    Py_ssize_t length = i + 1 - start;
    if ((length >= 1024 && !(hash & UINT64_C(4095))) || length == 65536) {
      if (!append_offset(result, i + 1))
        return 0;
      start = i + 1;
    }
  }
  return start == end || append_offset(result, end);
}

static PyObject *boundaries(PyObject *self, PyObject *raw) {
  (void)self;
  if (!PyBytes_CheckExact(raw)) {
    PyErr_SetString(PyExc_TypeError, "Exact byte input required");
    return NULL;
  }
  const unsigned char *data = (const unsigned char *)PyBytes_AS_STRING(raw);
  Py_ssize_t size = PyBytes_GET_SIZE(raw), start = 0;
  uint64_t hash = 0, table[256];
  for (int i = 0; i < 256; i++)
    table[i] = mix((uint64_t)i);
  PyObject *result = PyList_New(0);
  if (!result)
    return NULL;
  for (Py_ssize_t i = 0; i < size;) {
    Py_ssize_t end = i + 1;
    if (data[i] == '"') {
      // Input comes only from the existing canonical encoder. String token
      // ranges isolate unchanged long fields from earlier length changes.
      while (end < size) {
        unsigned char c = data[end++];
        if (c == '\\' && end < size)
          end++;
        else if (c == '"')
          break;
      }
      if (end - i >= 1024) {
        if ((start != i && !append_offset(result, i)) ||
            !split_range(result, data, i, end, table))
          goto fail;
        start = end;
        hash = 0;
        i = end;
        continue;
      }
    }
    // The short token path still checks maximum literal length every byte.
    for (; i < end; i++) {
      hash = (hash << 1) + table[data[i]];
      Py_ssize_t length = i + 1 - start;
      if (length == 65536 || (length >= 1024 && !(hash & UINT64_C(4095))) ||
          (end == i + 1 && length >= 512 &&
           (data[i] == '}' || data[i] == ']'))) {
        if (!append_offset(result, i + 1))
          goto fail;
        start = i + 1;
        hash = 0;
      }
    }
  }
  if (start != size) {
    if (!append_offset(result, size))
      goto fail;
  }
  return result;
fail:
  Py_DECREF(result);
  return NULL;
}

static PyMethodDef methods[] = {{"boundaries", boundaries, METH_O,
                                 "Return deterministic bounded byte offsets."},
                                {NULL, NULL, 0, NULL}};
static struct PyModuleDef module = {PyModuleDef_HEAD_INIT,
                                    "_canonical_fragmenter_native",
                                    NULL,
                                    -1,
                                    methods,
                                    NULL,
                                    NULL,
                                    NULL,
                                    NULL};
PyMODINIT_FUNC PyInit__canonical_fragmenter_native(void) {
  return PyModule_Create(&module);
}
