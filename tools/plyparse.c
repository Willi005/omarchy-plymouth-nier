#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

/* script_parse_file returns a script_op_t* (NULL on parse failure).
   Parse errors are printed to stderr by the library itself. */
int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s <script>\n", argv[0]); return 2; }
    void *h = dlopen("/usr/lib/plymouth/script.so", RTLD_NOW | RTLD_LOCAL);
    if (!h) { fprintf(stderr, "dlopen: %s\n", dlerror()); return 2; }
    void *(*parse)(const char *) = dlsym(h, "script_parse_file");
    if (!parse) { fprintf(stderr, "dlsym: %s\n", dlerror()); return 2; }
    void *op = parse(argv[1]);
    if (!op) { printf("PARSE FAILED\n"); return 1; }
    printf("PARSE OK\n");
    return 0;
}
