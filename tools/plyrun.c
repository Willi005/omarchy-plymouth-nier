/* plyrun — actually EXECUTE a Plymouth theme script and read globals back.
 *
 * script.so exports the parser, the interpreter and the math/string libs, but
 * the image/sprite/window/plymouth libs need a real display. So this harness
 * registers only math+string and expects the script under test to define its
 * own stubs for the graphics calls. That is enough to exercise the parts that
 * actually broke in practice: loops, hash indexing, function scoping, and
 * whether sprites created inside a helper survive the call.
 *
 * Build: gcc -o plyrun plyrun.c -ldl
 * Run:   ./plyrun <script> [global_name ...]
 */
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

int main(int argc, char **argv)
{
        if (argc < 2) {
                fprintf(stderr, "usage: %s <script> [global ...]\n", argv[0]);
                return 2;
        }

        void *h = dlopen("/usr/lib/plymouth/script.so", RTLD_NOW | RTLD_LOCAL);
        if (!h) {
                fprintf(stderr, "dlopen: %s\n", dlerror());
                return 2;
        }

        void *(*state_new)(void *) = dlsym(h, "script_state_new");
        void *(*math_setup)(void *) = dlsym(h, "script_lib_math_setup");
        void *(*string_setup)(void *) = dlsym(h, "script_lib_string_setup");
        void *(*parse)(const char *) = dlsym(h, "script_parse_file");
        void *(*execute)(void *, void *) = dlsym(h, "script_execute");
        double (*hash_get_number)(void *, const char *) =
                dlsym(h, "script_obj_hash_get_number");

        if (!state_new || !math_setup || !string_setup || !parse || !execute ||
            !hash_get_number) {
                fprintf(stderr, "missing symbol\n");
                return 2;
        }

        void *state = state_new(NULL);
        math_setup(state);
        string_setup(state);

        void *op = parse(argv[1]);
        if (!op) {
                printf("PARSE FAILED\n");
                return 1;
        }

        execute(state, op);

        /* script_state_t is { user_data, global, local, this }: at top level
         * global and local are refs to the same hash, so global is at [1]. */
        void *global = ((void **) state)[1];

        for (int i = 2; i < argc; i++)
                printf("%s = %g\n", argv[i], hash_get_number(global, argv[i]));

        printf("EXECUTED\n");
        return 0;
}
